from abc import abstractmethod
from typing import Any, Generic, Optional, Type, TypeVar, Union, cast

from stateflow.common import Observable, T, assign, is_observable
from stateflow.errors import FinalizedError, NotInitializedError
from stateflow.forwarders import ConstForwarders, MutatingForwarders
from stateflow.notifier import DummyNotifier, Notifier


class NotInitialized:
    pass


NOT_INITIALIZED: Any = type("NotInitialized", tuple(), {})
FINALIZED: Any = type("Finalized", tuple(), {})


class Const(Observable[T], ConstForwarders):
    """
    Simple implementation of `Observable` that holds the same value through the lifetime.
    """
    repr_name = 'Const'

    dummy_notifier: DummyNotifier = DummyNotifier(priority=0)

    def __init__(self, value: T) -> None:
        super().__init__()
        self._value: T = value

    def __notifier__(self) -> DummyNotifier:
        return self.dummy_notifier

    def __eval__(self) -> T:
        if self._value == FINALIZED:
            raise FinalizedError()
        return self._value

    def __finalize__(self) -> None:
        # it may be useful if we want to get rid of reference to the value, even in constant
        self._value = cast(T, FINALIZED)


class Proxy(Observable[T]):
    """
    Proxy calls of __eval__ and __assign__ to another `Observable`.
    """

    def __init__(self, inner: Observable[T]) -> None:
        super().__init__()
        assert is_observable(inner)
        self._inner: Observable[T] = inner

    def __notifier__(self) -> Notifier:
        return self._inner.__notifier__()

    def __eval__(self) -> T:
        return self._inner.__eval__()

    # async def __aeval__(self) -> T:
    #     return await self._inner.__aeval__()

    def __assign__(self, value: T) -> None:
        self._inner.__assign__(value)

    def __finalize__(self) -> None:
        self._inner.__finalize__()


class NotifiedProxy(Proxy[T]):
    """
    Like `Proxy` but has own `Notifier` so it can be notified independently of the inner `Observable`.
    """

    def __init__(self, inner: Observable[T]) -> None:
        super().__init__(inner)
        self._notifier: Notifier = Notifier(self._notify)
        self._inner.__notifier__().add_observer(self._notifier)

    def __notifier__(self) -> Notifier:
        return self._notifier

    def _notify(self) -> None:
        pass


V = TypeVar('V')

class VarProxy(NotifiedProxy[T]):
    """
    Like `Proxy` but the target `Observable` can be changed (i.e. replaced with another `Observable`). Notifies whenever
    the inner `Observable` notifies or when another `Observable` is assigned.
    """

    def __init__(self, inner: Observable[Any] = None) -> None:
        if inner is None:
            inner = Const(None)
        super().__init__(inner)

    def set_inner(self, inner: Observable[T]) -> None:
        assert is_observable(inner)
        with self._notifier:
            self._unobserve_value()
            assign(self._inner, inner)
            self._observe_value()

    def _unobserve_value(self) -> None:
        self._inner.__notifier__().remove_observer(self._notifier)

    def _observe_value(self) -> None:
        self._inner.__notifier__().add_observer(self._notifier)


class Var(Observable[T], ConstForwarders, MutatingForwarders):
    """
    A simple `Observable` that holds a raw value that can be changed.
    """

    repr_name = 'Var'
    NOT_INITIALIZED = NOT_INITIALIZED

    def __init__(self, value: Union[T, Any] = NOT_INITIALIZED) -> None:
        super().__init__()
        self._value: Union[T, Any] = value
        self._notifier: Notifier = Notifier()
        self._notifier.name = f'Var[{type(value).__name__}]'

    def __notifier__(self) -> Notifier:
        return self._notifier

    def __eval__(self) -> T:
        if self._value == NOT_INITIALIZED:
            raise NotInitializedError()
        elif self._value == FINALIZED:
            raise FinalizedError()
        return cast(T, self._value)

    def __assign__(self, value: T) -> None:
        self._value = value
        self._notifier.notify()

    def __finalize__(self) -> None:
        self._value = FINALIZED
        # no notification here since this value should not be used anymore


class CacheBase(Observable[T], ConstForwarders):
    """
    See `Cache` for description.
    """

    def __init__(self, inner: Observable[T]) -> None:
        super().__init__()
        self._inner: Observable[T] = inner
        self._cache_is_valid: bool = False
        self._cached_value: Optional[T] = None
        self._cached_exception: Optional[Exception] = None
        self._notifier: Notifier = Notifier(self._invalidate_cache)
        self._inner.__notifier__().add_observer(self._notifier)
        self._notifier.name = f'Cache'

    def __notifier__(self) -> Notifier:
        return self._notifier

    def _invalidate_cache(self) -> bool:
        if not self._cache_is_valid:
            # we don't forward the notification if new value was not requested (with eval) since last invalidate
            return False
        self._cache_is_valid = False
        return True

    @abstractmethod
    def __eval__(self) -> T:
        pass

    def __finalize__(self) -> None:
        self._inner.__finalize__()


class Cache(CacheBase[T]):
    """
    Avoids multiple calls of `__eval__` of the inner `Observable` if it didn't notify about change since last call.
    """

    def __eval__(self) -> T:
        self._update_cache()
        if self._cached_exception:
            raise self._cached_exception
        return cast(T, self._cached_value)

    def _update_cache(self) -> None:
        if not self._cache_is_valid:
            try:
                self._cached_value = self._inner.__eval__()
                self._cached_exception = None
            except Exception as e:
                self._cached_value = None
                self._cached_exception = e
            self._cache_is_valid = True


# class AsyncCache(CacheBase[T], ConstForwarders):
#     async def __aeval__(self):
#         await self._async_update_cache()
#         if self._cached_exception:
#             raise self._cached_exception
#         return self._cached_value
#
#     async def _async_update_cache(self):
#         if not self._cache_is_valid:
#             try:
#                 self._cached_value = await self._inner.__aeval__()
#                 self._cached_exception = None
#             except Exception as e:
#                 self._cached_value = None
#                 self._cached_exception = e
#             self._cache_is_valid = True
#
#     def __eval__(self):
#         raise_need_async_eval()


def as_observable(v: Union[T, Observable[T]]) -> Observable[T]:
    if is_observable(v):
        return cast(Observable[T], v)
    else:
        return Const(cast(T, v))
