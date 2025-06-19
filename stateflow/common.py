import asyncio
from abc import abstractmethod
from typing import Callable, Coroutine, Generic, TypeVar, Union

from stateflow.errors import ArgEvalError, BodyEvalError, EvError, NotAssignable


FULL_TRACEBACKS = False
REPR_EVALUATES = False
deprecated_interactive_mode = False


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

    @abstractmethod
    def __notifier__(self) -> 'Notifier':
        """
        A notifier, that will notify whenever a reactive function that used this object should be called again.
        """
        pass

    @abstractmethod
    def __eval__(self) -> T:
        """
        Returns current value of the observable.

        Not a property since there is a mess with forwarding of getattr (via Forwarders) when getting property.
        """
        pass

    @abstractmethod
    def __assign__(self, value: T):
        raise NotAssignable()

    def __finalize__(self):
        """
        Declare that this observable will be never used again.
        :return:
        """
        pass

    def __repr__(self):
        try:
            if REPR_EVALUATES:
                self.__notifier__().refresh()
                val = self.__eval__()
            else:
                return f'{self.repr_name}(?)'
        except Exception as e:
            return '{}(<{}: {}>)'.format(self.repr_name, type(e).__name__, str(e))
        else:
            return f'{self.repr_name}({repr(val)})'



# async def aev_strict(v: Observable[T]) -> T:
#     return await v.__aeval__()
#

def ev(v: Union[T, Observable[T]]) -> T:
    while is_observable(v):
        v = ev_one(v)
    return v


def ev_exception(v):
    try:
        _ = ev(v)
        return None
    except EvError as e:
        return e


def ev_def(v, val_on_exception=None):
    try:
        return ev(v)
    except EvError as e:
        return val_on_exception


def assign(var: Observable[T], val: T):
    var.__assign__(val)


def finalize(var: Observable[T]):
    var.__finalize__()


def is_observable(v):
    """
    Check whether given object should be considered as "observable" i.e. the object that manages notifiers internally
    and returns observable objects from it's methods.
    """
    return hasattr(type(v), '__notifier__') and hasattr(type(v), '__eval__')


def ev_one(v: Observable[T]) -> T:
    assert is_observable(v)
    # BodyEvalError and ArgEvalError are handled in a special way to
    try:
        v.__notifier__().refresh()  # FIXME: why do we need this? shouldn't eval force to evaluate
        return v.__eval__()
    except BodyEvalError as e:
        # hide a part of stack from here to the place where BodyEvalError was raised
        raise EvError() from e.with_traceback(None)
    except ArgEvalError as e:
        raise EvError() from e.with_traceback(None)


