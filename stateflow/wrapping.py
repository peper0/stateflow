from typing import Any, Callable, Iterable, Sequence, Tuple, Dict, List, Optional, cast, TypeVar, Union, Iterator, ContextManager

from stateflow import reactive
from stateflow.common import ev
from stateflow.notifier import Notifier


def get_subnotifier(self: Notifier, name: str) -> Notifier:
    if not name:
        return self.__notifier__
    if not hasattr(self, '_subnotifiers'):
        setattr(self, '_subnotifiers', dict())
    return self._subnotifiers.setdefault(name, Notifier(lambda: None, name="subnotifier " + name))


class many_notifiers:
    def __init__(self, *notifiers: Notifier) -> None:
        self.notifiers = notifiers

    def __enter__(self) -> None:
        for notifier in self.notifiers:
            notifier.__enter__()

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        for notifier in self.notifiers:
            notifier.__exit__(exc_type, exc_val, exc_tb)


def observable_method(unbound_method: Union[str, Callable], observed: Sequence[str], notified: Sequence[str]) -> Callable:
    # @reactive(other_deps=[get_subobservable observed)
    if isinstance(unbound_method, str):
        unbound_method = forward_by_name(unbound_method)

    @reactive(pass_args=[0], dep_only_args=['_additional_deps'])
    def wrapped(self: Any, *args: Any, **kwargs: Any) -> Any:
        with many_notifiers(*[get_subnotifier(self, observable) for observable in notified]):
            res = unbound_method(ev(self), *args, **kwargs)
        return res

    def wrapped2(self: Any, *args: Any, **kwargs: Any) -> Any:
        return wrapped(self, *args, **kwargs,
                       _additional_deps=[get_subnotifier(self, obs) for i, obs in enumerate(observed)])

    return wrapped2


def notifying_method(unbound_method: Union[str, Callable], notified: Sequence[str]) -> Callable:
    if isinstance(unbound_method, str):
        unbound_method = forward_by_name(unbound_method)

    def wrapped(self: Any, *args: Any, **kwargs: Any) -> Any:
        res = unbound_method(ev(self), *args, **kwargs)
        for observable in notified:
            get_subnotifier(self, observable)._notify_observers()
        return res

    return wrapped


def getter(unbound_method: Union[str, Callable], observed: Sequence[str]) -> Callable:
    return observable_method(unbound_method, observed=observed, notified=[])


def reactive_setter(unbound_method: Union[str, Callable], notified: Sequence[str]) -> Callable:
    return observable_method(unbound_method, observed=[], notified=notified)


def forward_by_name(name: str) -> Callable:
    def func(self: Any, *args: Any, **kwargs: Any) -> Any:
        return getattr(self, name)(*args, **kwargs)

    return func


def add_reactive_forwarders(cl: Any, functions: Iterable[Tuple[str, Callable]]) -> None:
    """
    For operators and methods that don't modify a state of an object (__neg_, etc.).
    """

    def add_one(cl: Any, name: str, func: Callable) -> None:
        def wrapped(self: Any, *args: Any) -> Any:
              # fixme: we should rather forward to the _target, not to __eval__
            reactive_f = reactive(func)

            prefix = ''
            if hasattr(self, '__notifier__'):
                prefix = self.__notifier__().name + '.'
            return reactive_f(self, *args)

        setattr(cl, name, wrapped)

    for name, func in functions:
        add_one(cl, name, func)


def add_assignop_forwarders(cl: Any, functions: Iterable[Tuple[str, Callable]]) -> None:
    """
    For operators like '+=' and one-arg functions like append, remove
    """

    def add_one(cl: Any, name: str, func: Callable) -> None:
        def wrapped(self: Any, arg1: Any) -> Any:
            target = self._target()
            self_unwrapped = target.__eval__()
            target.__assign__(func(self_unwrapped, arg1))
            return self

        setattr(cl, name, wrapped)

    for name, func in functions:
        add_one(cl, name, func)


def add_notifying_forwarders(cl: Any, functions: Iterable[Tuple[str, Callable]]) -> None:
    """
    For operators like '+=' and one-arg functions like append, remove
    """

    def add_one(cl: Any, name: str, func: Callable) -> None:
        def wrapped(self: Any, *args: Any) -> Any:
            target = self._target()
            self_unwrapped = target.__eval__()
            with target.__notifier__():
                res = func(self_unwrapped, *args)
            return res

        setattr(cl, name, wrapped)

    for name, func in functions:
        add_one(cl, name, func)
