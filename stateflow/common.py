import asyncio
from abc import abstractmethod
from typing import Callable, Coroutine, Generic, TypeVar, Union

from stateflow.errors import NotAssignable


def ensure_coro_func(f):
    if asyncio.iscoroutinefunction(f):
        return f
    elif hasattr(f, '__call__'):
        async def async_f(*args, **kwargs):
            return f(*args, **kwargs)

        return async_f


CoroutineFunction = Callable[..., Coroutine]

MaybeAsyncFunction = Union[Callable, CoroutineFunction]
NotifyFunc = Union[Callable[[], None], Callable[[], Coroutine]]

T = TypeVar('T')


class Observable(Generic[T]):
    @property
    @abstractmethod
    def __notifier__(self) -> 'Notifier':
        """
        A notifier, that will notify whenever a reactive function that used this object should be called again.
        """
        pass

    @abstractmethod
    def __eval__(self) -> T:
        """
        Return the object that is wrapped.
        It's usually a raw non observable object, however inside "Proxy" it's used to hold a reference to any object (possibly other Proxy or other wrapper)
        It will be taken by the @reactive function and passed to the body of the function.
        """
        pass

    async def __aeval__(self) -> T:
        return self.__eval__()

    def __assign__(self, value: T):
        raise NotAssignable()


def ev_strict(v: Observable[T]) -> T:
    return v.__eval__()


async def aev_strict(v: Observable[T]) -> T:
    return await v.__aeval__()


def ev_exception(v):
    try:
        v.__eval__()
        return None
    except Exception as e:
        return e


def ev_def(v, val_on_exception=None):
    try:
        return v.__eval__()
    except Exception as e:
        return val_on_exception


def ev(v: Union[T, Observable[T]]) -> T:
    if is_observable(v):
        return ev_strict(v)
    else:
        return v


def assign(var: Observable[T], val: T):
    var.__assign__(val)


async def aev(v: Union[T, Observable[T]]) -> T:
    if is_observable(v):
        return await aev_strict(v)
    else:
        return v


def is_observable(v):
    """
    Check whether given object should be considered as "observable" i.e. the object that manages notifiers internally
    and returns observable objects from it's methods.
    """
    return hasattr(v, '__notifier__') and hasattr(v, '__eval__')


def is_wrapper(v):
    """
    deprecated
    """
    return is_observable(v)
