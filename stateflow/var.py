from abc import abstractmethod
from typing import Any, Union

from stateflow.common import Observable, T, is_observable
from stateflow.errors import NotInitializedError, raise_need_async_eval
from stateflow.notifier import DummyNotifier, Notifier


class Const(Observable[T]):
    """
    Simple implementation of `Observable` that holds the same value through the lifetime.
    """

    dummy_notifier = DummyNotifier(priority=0)

    def __init__(self, value: T):
        super().__init__()
        self._value = value

    @property
    def __notifier__(self):
        return self.dummy_notifier

    def __eval__(self) -> T:
        return self._value


class Proxy(Observable[T]):
    """
    Proxy calls of __eval__ and __assign__ to another `Observable`.
    """

    def __init__(self, inner: Observable[T]):
        super().__init__()
        self._inner = inner

    @property
    def __notifier__(self):
        return self._inner.__notifier__

    def __eval__(self) -> T:
        return self._inner.__eval__()

    async def __aeval__(self) -> T:
        return await self._inner.__aeval__()

    def __assign__(self, value: T):
        self._inner.__assign__(value)


class NotifiedProxy(Observable[T]):
    """
    Like `Proxy` but has own `Notifier` so it can be notified independently of the inner `Observable`.
    """

    def __init__(self, inner: Observable[T]):
        super().__init__()
        self._notifier = Notifier(self.notify)
        self._inner = inner  # type: Observable[T]
        self._inner.__notifier__.add_observer(self._notifier)

    @property
    def __notifier__(self):
        return self._notifier

    def __eval__(self) -> T:
        return self._inner.__eval__()

    async def __aeval__(self):
        return await self._inner.__aeval__()

    def __assign__(self, value: Union['Observable', Any]):
        self._inner.__assign__(value)

    def _notify(self):
        pass


class VarProxy(NotifiedProxy[T]):
    """
    Like `Proxy` but the target `Observable` can be changed (i.e. replaces with another `Observable`). Notifies whenever
    the inner `Observable` notifies or when another `Observable` is assigned.
    """

    def __init__(self, inner=Const(None)):
        super().__init__(inner)

    def set_inner(self, inner: Observable[T]):
        assert is_observable(inner)
        with self._notifier:
            self._unobserve_value()
            self._inner @= inner
            self._observe_value()

    def _unobserve_value(self):
        return self._inner.__notifier__.remove_observer(self._notifier)

    def _observe_value(self):
        return self._inner.__notifier__.add_observer(self._notifier)


class Var(Observable[T]):
    """
    A simple `Observable` that holds a raw value that can be changed.
    """

    class NotInitialized:
        pass

    NOT_INITIALIZED = NotInitialized()

    def __init__(self, value: T = NOT_INITIALIZED):
        super().__init__()
        self._value = value  # type: T
        self._notifier = Notifier()

    @property
    def __notifier__(self) -> Notifier:
        return self._notifier

    def __eval__(self) -> T:
        if self._value == self.NOT_INITIALIZED:
            raise NotInitializedError()
        return self._value

    def __assign__(self, value):
        with self._notifier:
            self._value = value


class CacheBase(Observable[T]):
    """
    See `Cache` for description.
    """

    def __init__(self, inner: Observable[T]):
        super().__init__()
        self._inner = inner  # type: Observable[T]
        self._cache_is_valid = False
        self._cached_value = None
        self._cached_exception = None
        self._notifier = Notifier(self._invalidate_cache)
        self._inner.__notifier__.add_observer(self._notifier)

    @property
    def __notifier__(self):
        return self._notifier

    def _invalidate_cache(self):
        if not self._cache_is_valid:
            # we don't forward the notification if new value was not requested (with eval) since last invalidate
            return False
        self._cache_is_valid = False
        return True

    @abstractmethod
    def __eval__(self) -> T:
        pass


class Cache(CacheBase[T]):
    """
    Avoids multiple calls of `__eval__` of the inner `Observable` if it didn't notify about change since last call.
    """

    def __eval__(self):
        self._update_cache()
        if self._cached_exception:
            raise self._cached_exception
        return self._cached_value

    def _update_cache(self):
        if not self._cache_is_valid:
            try:
                self._cached_value = self._inner.__eval__()
                self._cached_exception = None
            except Exception as e:
                self._cached_value = None
                self._cached_exception = e
            self._cache_is_valid = True


class AsyncCache(CacheBase[T]):
    async def __aeval__(self):
        await self._async_update_cache()
        if self._cached_exception:
            raise self._cached_exception
        return self._cached_value

    async def _async_update_cache(self):
        if not self._cache_is_valid:
            try:
                self._cached_value = await self._inner.__aeval__()
                self._cached_exception = None
            except Exception as e:
                self._cached_value = None
                self._cached_exception = e
            self._cache_is_valid = True

    def __eval__(self):
        raise_need_async_eval()


def as_observable(v):
    if is_observable(v):
        return v
    else:
        return Const(v)
