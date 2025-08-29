import abc
import asyncio
from abc import abstractmethod
from typing import Any, Awaitable, Callable, Coroutine, Generic, Optional, ParamSpec, Protocol, TYPE_CHECKING, \
    TypeAlias, \
    TypeGuard, TypeVar, \
    Union, \
    cast, \
    runtime_checkable

from stateflow.errors import ArgEvalError, BodyEvalError, EvError, NotAssignable


FULL_TRACEBACKS = False
REPR_EVALUATES = False
deprecated_interactive_mode = False  # why deprecated? quite usable, e.g. to test if function does not raise an exception


R = TypeVar('R')
S = TypeVar('S')
T = TypeVar('T')
P = ParamSpec('P')

def ensure_coro_func(f: Callable[..., R]) -> Callable[..., Coroutine[Any, Any, R]]:
    if asyncio.iscoroutinefunction(f):
        return cast(Callable[..., Coroutine[Any, Any, R]], f)
    elif hasattr(f, '__call__'):
        async def async_f(*args: Any, **kwargs: Any) -> R:
            return f(*args, **kwargs)

        return async_f
    else:
        raise TypeError(f"Expected callable, got {type(f)}")


CoroutineFunction = Callable[P, Awaitable[R]]
MaybeAsyncFunction = Union[Callable[..., R], Callable[..., Coroutine[Any, Any, R]]]
NotifyFunc = Union[Callable[[], None], Callable[[], Coroutine[Any, Any, None]]]

#FIXME: INotificationNode? Or split into two interfaces?
class INotifier(abc.ABC):
    """
    A node in a graph where notifications (about changes) are propagated.

    A notifier observes other notifiers. It means, that if one of the observed notifiers is "notifier", the current one
    will also be notified soon (unless it is "inactive"). Physically, the notifications are called by `Refresher`.

    A notifier can be "active" or "inactive". Inactive notifiers are ignored by the refresher. Notifier is active if
    it has at least one active observer.

    A notifier has a priority, which is used to determine the order of notifications. The priority is an integer, where
    lower numbers are called first. The priority of the notifier is always greater than the priority of all its observers.
    """
    name: str = ""

    @abc.abstractmethod
    def notify(self) -> None:
        """
        Tell the notifier that the corresponding object state has possibly changed.

        Called by:
        - other notifiers
        - observable implementation
        """
        ...

    @abc.abstractmethod
    def propagate(self) -> None:
        """Call the update callback in the related object and notify active dependents. Called by refresher."""
        ...

    @property
    @abc.abstractmethod
    def priority(self) -> int:
        """
        When propagating notification, notifiers with lower priority number are called first. Should be greater than
        the priority of the observed notifiers.
        """
        ...

    @property
    @abc.abstractmethod
    def active(self) -> bool:
        """Whether the notification should be propagated. The notifier should be active if it has at least one active observer."""
        ...

    @abc.abstractmethod
    def add_observer(self, observer: 'INotifier') -> None:
        """Add an observer to this notifier. It will be notified when this notifier is called"""
        ...

    @abc.abstractmethod
    def remove_observer(self, observer: 'INotifier') -> None:
        """Remove an observer from this notifier. It will not be notified anymore."""
        ...

    @abc.abstractmethod
    def refresh(self) -> None:
        ...

class Observable(Generic[T]):
    repr_name = 'Observable'

    @abstractmethod
    def __notifier__(self) -> INotifier:
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
    def __assign__(self, value: T) -> None:
        raise NotAssignable()

    def __finalize__(self) -> None:
        """
        Declare that this observable will never be used again.
        :return:
        """
        pass

    def __repr__(self) -> str:
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


MaybeObservable: TypeAlias = Observable[T] | T
# async def aev_strict(v: Observable[T]) -> T:
#     return await v.__aeval__()
#

def ev(v: Union[T, Observable[T]]) -> T:
    while is_observable(v):
        v = cast(Observable[T], v)
        v = ev_one(v)
    return cast(T, v)


def ev_exception(v: Any) -> Optional[EvError]:
    try:
        _ = ev(v)
        return None
    except EvError as e:
        return e


def ev_def(v: Any, val_on_exception: Any = None) -> Any:
    try:
        return ev(v)
    except EvError as e:
        return val_on_exception


def assign(var: Observable[T], val: T) -> None:
    var.__assign__(val)


def finalize(var: Observable[T]) -> None:
    var.__finalize__()


def is_observable(v: Any) -> TypeGuard[Observable[T]]:
    """
    Check whether given object should be considered as "observable" i.e. the object that manages notifiers internally
    and returns observable objects from its methods.
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



