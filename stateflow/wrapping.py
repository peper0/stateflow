from typing import Any, Callable, Iterable, Sequence, Tuple

from stateflow import reactive
from stateflow.common import ev
from stateflow.notifier import Notifier, ScopedName, many_notifiers


def get_subnotifier(self: Notifier, name: str) -> Notifier:
    if name is None or name is '':
        return self.__notifier__
    if not hasattr(self, '_subnotifiers'):
        setattr(self, '_subnotifiers', dict())
    return self._subnotifiers.setdefault(name, Notifier("subnotifier " + name))


def observable_method(unbound_method, observed: Sequence[str], notified: Sequence[str]):
    # @reactive(other_deps=[get_subobservable observed)
    if isinstance(unbound_method, str):
        unbound_method = forward_by_name(unbound_method)

    @reactive(pass_args=[0], dep_only_args=['_additional_deps'])
    def wrapped(self, *args, **kwargs):
        with many_notifiers(*[get_subnotifier(self, observable) for observable in notified]):
            res = unbound_method(ev(self), *args, **kwargs)
        return res

    def wrapped2(self, *args, **kwargs):
        return wrapped(self, *args, **kwargs,
                       _additional_deps=[get_subnotifier(self, obs) for i, obs in enumerate(observed)])

    return wrapped2


def notifying_method(unbound_method, notified: Sequence[str]):
    if isinstance(unbound_method, str):
        unbound_method = forward_by_name(unbound_method)

    def wrapped(self, *args, **kwargs):
        res = unbound_method(ev(self), *args, **kwargs)
        for observable in notified:
            get_subnotifier(self, observable).notify_observers()
        return res

    return wrapped


def getter(unbound_method, observed):
    return observable_method(unbound_method, observed=observed, notified=[])


def reactive_setter(unbound_method, notified):
    return observable_method(unbound_method, observed=[], notified=notified)


def forward_by_name(name):
    def func(self, *args, **kwargs):
        return getattr(self, name)(*args, **kwargs)

    return func


def add_reactive_forwarders(cl: Any, functions: Iterable[Tuple[str, Callable]]):
    """
    For operators and methods that don't modify a state of an object (__neg_, etc.).
    """

    def add_one(cl: Any, name, func):
        def wrapped(self, *args):
            @reactive  # fixme: we should rather forward to the _target, not to __eval__
            def reactive_f(self_unwrapped, *args):
                return func(self_unwrapped, *args)

            prefix = ''
            if hasattr(self, '__notifier__'):
                preifx = self.__notifier__.name + '.'
            with ScopedName(name=preifx + name, final=True):
                return reactive_f(self, *args)

        setattr(cl, name, wrapped)

    for name, func in functions:
        add_one(cl, name, func)


def add_assignop_forwarders(cl: Any, functions: Iterable[Tuple[str, Callable]]):
    """
    For operators like '+=' and one-arg functions like append, remove
    """

    def add_one(cl: Any, name, func):
        def wrapped(self, arg1):
            target = self._target()
            self_unwrapped = target.__eval__()
            target.__assign__(func(self_unwrapped, arg1))
            return self

        setattr(cl, name, wrapped)

    for name, func in functions:
        add_one(cl, name, func)


def add_notifying_forwarders(cl: Any, functions: Iterable[Tuple[str, Callable]]):
    """
    For operators like '+=' and one-arg functions like append, remove
    """

    def add_one(cl: Any, name, func):
        def wrapped(self, *args):
            target = self._target()
            self_unwrapped = target.__eval__()
            with target.__notifier__:
                res = func(self_unwrapped, *args)
            return res

        setattr(cl, name, wrapped)

    for name, func in functions:
        add_one(cl, name, func)
