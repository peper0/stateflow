import asyncio
from abc import abstractmethod
from typing import Callable, Coroutine, Generic, TypeVar, Union

from stateflow.errors import ArgEvalError, BodyEvalError, EvError, NotAssignable


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
    repr_name = 'Observable'

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
        """
        pass

    async def __aeval__(self) -> T:
        return self.__eval__()

    def __assign__(self, value: T):
        raise NotAssignable()

    def __finalize__(self):
        pass

    def __repr__(self):
        try:
            val = ev_one(self)
        except Exception as e:
            return '{}(<{}: {}>)'.format(self.repr_name, type(e).__name__, str(e))
        else:
            return f'{self.repr_name}({repr(val)})'


def ev_one(v: Observable[T]) -> T:
    assert is_observable(v)
    try:
        return v.__eval__()
    except BodyEvalError as e:
        raise EvError() from e.with_traceback(None)
    except ArgEvalError as e:
        raise EvError() from e.with_traceback(None)


async def aev_strict(v: Observable[T]) -> T:
    return await v.__aeval__()


def ev_exception(v):
    try:
        v.__eval__()
        return None
    except EvError as e:
        return e


def ev_def(v, val_on_exception=None):
    try:
        return v.__eval__()
    except EvError as e:
        return val_on_exception


def ev(v: Union[T, Observable[T]]) -> T:
    while is_observable(v):
        v = ev_one(v)
    return v


def assign(var: Observable[T], val: T):
    var.__assign__(val)


def finalize(var: Observable[T], val: T):
    var._cleanup(val)

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
