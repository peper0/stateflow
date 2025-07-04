from functools import wraps
from typing import Callable

from stateflow.common import Observable, T, ev, is_observable
from stateflow.decorators import reactive
from stateflow.errors import NotInitializedError, ValidationError
from stateflow.notifier import ACTIVE_NOTIFIER
from stateflow.var import Const, NotifiedProxy, Var


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


class VolatileProxy(NotifiedProxy[T]):
    def __init__(self, inner):
        super().__init__(inner)
        self._notifier.add_observer(ACTIVE_NOTIFIER)
        self._notifier.name = "Volatile"
        self._notify() # if notifier was active, the notify would not be called again

    def _notify(self):
        ev(self._inner)


def volatile(var_or_callable):
    # FIXME: to be rethinked
    if is_observable(var_or_callable):
        return VolatileProxy(var_or_callable)
    elif isinstance(var_or_callable, Callable):
        func = var_or_callable

        @wraps(func)
        def wrapper(*args, **kwargs):
            res = func(*args, **kwargs)
            if is_observable(res):
                return volatile(res)
            else:
                return res

        return wrapper
    else:
        raise TypeError("argument type should be Callable or Observable (got {})".format(type(var_or_callable)))


def const(raw):
    return Const(raw)


def var(raw=Var.NOT_INITIALIZED):
    return Var(raw)


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
