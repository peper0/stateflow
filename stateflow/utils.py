from contextlib import suppress
from typing import Callable

from stateflow.common import Observable, T
from stateflow.decorators import reactive
from stateflow.errors import NotInitializedError, ValidationError
from stateflow.forwarders import Forwarders
from stateflow.notifier import ScopedName
from stateflow.var import Const, Proxy, Var


def set_if_inequal(var_to_set, new_value):
    try:
        # print("{} is {}".format(repr(var_to_set), var_to_set.__eval__))
        if var_to_set.__eval__() == new_value:
            return
    except NotInitializedError:
        pass
    # print("setting {} to {}".format(repr(var_to_set), new_value))
    var_to_set.__assign__(new_value)


def bind_vars(*vars):
    @reactive
    def set_all(value):
        for var in vars:
            set_if_inequal(var, value)

    return [volatile(set_all(var)) for var in vars]


class VolatileProxy(Proxy[T]):
    def __init__(self, other_var: Observable[T]):
        with ScopedName('volatile'):
            super().__init__(other_var)
        self._notifier.notify_func = self._trigger

    def _trigger(self):
        with suppress(Exception):
            self._other_var.__eval__()  # trigger run even if the result is not used
        return True


def volatile(var):
    if var is not None:  # var may be none if we make "volatile(foo(x))" where foo is reactive and x is not observable
        return VolatileProxy(var)


def const(raw):
    return Forwarders(Const(raw))


def var(raw=Var.NOT_INITIALIZED):
    return Forwarders(Var(raw))


@reactive
def validate_arg(arg: Observable[T], is_valid: Callable[[Observable[T]], bool],
                 description='"{val}" does not satisfy the condition'):
    if not is_valid(arg):
        raise ValidationError(description.format(val=arg))
    return arg


@reactive
def not_none(arg: Observable[T]):
    if arg is None:
        raise ValidationError('should not be none')
    return arg


@reactive
def make_list(*args):
    return [a for a in args]


@reactive
def make_tuple(*args):
    return tuple(args)


make_dict = reactive(dict)


def rewrap_dict(d: dict):
    @reactive
    def foo(keys, *values):
        return {k: v for k, v in zip(keys, values)}

    return foo(d.keys(), *d.values())
