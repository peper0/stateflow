import operator
from abc import abstractmethod
from functools import wraps
from math import ceil, floor

from stateflow.common import T
from stateflow.decorators import reactive
from stateflow.var import Proxy
from stateflow.wrapping import add_assignop_forwarders, add_notifying_forwarders, add_reactive_forwarders

UNARY_OPERATORS = [
    ('__neg__', operator.__neg__),
    ('__pos__', operator.__pos__),
    ('__abs__', operator.__abs__),
    ('__invert__', operator.__invert__),
    ('__round__', round),
    ('__floor__', floor),
    ('__ceil__', ceil),
]


def right_2arg(func):
    @wraps(func)
    def f(a1, a2):
        return func(a2, a1)

    return f


BINARY_OPERATORS = [
    # arith         # arith        
    ('__add__', operator.__add__),
    ('__sub__', operator.__sub__),
    ('__mul__', operator.__mul__),
    ('__floordiv__', operator.__floordiv__),
    ('__truediv__', operator.__truediv__),
    ('__mod__', operator.__mod__),
    ('__divmod__', divmod),
    ('__pow__', operator.__pow__),
    ('__radd__', right_2arg(operator.__add__)),
    ('__rsub__', right_2arg(operator.__sub__)),
    ('__rmul__', right_2arg(operator.__mul__)),
    ('__rfloordiv__', right_2arg(operator.__floordiv__)),
    ('__rtruediv__', right_2arg(operator.__truediv__)),
    ('__rmod__', right_2arg(operator.__mod__)),
    ('__rdivmod__', right_2arg(divmod)),
    ('__rpow__', right_2arg(operator.__pow__)),
    # logic
    ('__and__', operator.__and__),
    ('__or__', operator.__or__),
    ('__xor__', operator.__xor__),
    ('__lshift__', operator.__lshift__),
    ('__rshift__', operator.__rshift__),
    ('__rand__', operator.__and__),
    ('__ror__', right_2arg(operator.__or__)),
    ('__rxor__', right_2arg(operator.__xor__)),
    ('__rlshift__', right_2arg(operator.__lshift__)),
    ('__rrshift__', right_2arg(operator.__rshift__)),
]

CMP_OPERATORS = [
    ('__eq__', operator.__eq__),
    ('__ge__', operator.__ge__),
    ('__gt__', operator.__gt__),
    ('__le__', operator.__le__),
    ('__lt__', operator.__lt__),
    ('__ne__', operator.__ne__),
]

OTHER_NONMODYFING_0ARG = [
    ('__len__', len),
    ('__length_hint__', operator.length_hint),
    ('__reversed__', reversed),
    # '__iter__',  # it's not so simple
]

OTHER_NONMODYFING_1ARG = [
    ('__getitem__', operator.getitem),
    # ('__missing__',
    ('__contains__', operator.contains),
]

ASSIGN_MOD_OPERATORS = [
    # arith
    ('__iadd__', operator.__iadd__),
    ('__isub__', operator.__isub__),
    ('__imul__', operator.__imul__),

    ('__ifloordiv__', operator.__ifloordiv__),
    ('__itruediv__', operator.__itruediv__),
    ('__imod__', operator.__imod__),
    ('__ipow__', operator.__ipow__),
    # logic        operator.# logic
    ('__iand__', operator.__iand__),
    ('__ior__', operator.__ior__),
    ('__ixor__', operator.__ixor__),
    ('__ilshift__', operator.__ilshift__),
    ('__irshift__', operator.__irshift__),
]

OTHER_MODYFING_1ARG = [
    ('__delitem__', operator.delitem),
]

OTHER_MODYFING_2ARG = [
    ('__setitem__', operator.setitem),
]


class ForwardersBase:
    @abstractmethod
    def _target(self):
        """
        Forwarded methods are called on the object returned by this function.
        :return:
        """
        raise NotImplementedError()


class ConstForwarders(ForwardersBase):
    @abstractmethod
    def _target(self):
        raise NotImplementedError()

    def __bool__(self):
        return bool(self._target().__eval__())

    def __trunc__(self):
        # python raises an exception if __trunc__ returns non-int
        return int(self._target().__eval__())

    def __str__(self):
        return self._target().__eval__().__str__()

    def __bytes__(self):
        return self._target().__eval__().__bytes__()

    def __format__(self, format_spec):
        return format(self._target().__eval__(), format_spec)

    @reactive
    def __call__(self, *args, **kwargs):
        """
        The argument `self` is evaluated inside this call so there is not infinite recursion (`self` is no more of
        `ConstForwarders` class).
        """
        # This one is not necessary const. But it may be. We don't know.
        return self.__call__(*args, **kwargs)

    @reactive
    def __getattr__(self, item):
        """
        The argument `self` is evaluated inside this call so there is not infinite recursion (`self` is no more of
        `ConstForwarders` class).
        """
        # This one is not necessary const. But it may be. We don't know.
        return getattr(self, item)


class MutatingForwarders(ForwardersBase):
    @abstractmethod
    def _target(self):
        raise NotImplementedError()

    def __imatmul__(self, other):
        """
        A fancy way to assign values to a variable ("v @= 5" instead of "v.__assign__(5)")
        """
        target = self._target()
        target.__assign__(other)
        return self


add_reactive_forwarders(ConstForwarders, UNARY_OPERATORS + OTHER_NONMODYFING_0ARG)
add_reactive_forwarders(ConstForwarders, BINARY_OPERATORS + CMP_OPERATORS + OTHER_NONMODYFING_1ARG)

add_assignop_forwarders(ConstForwarders, ASSIGN_MOD_OPERATORS)
add_notifying_forwarders(MutatingForwarders, OTHER_MODYFING_1ARG + OTHER_MODYFING_2ARG)


class Forwarders(Proxy[T], ConstForwarders, MutatingForwarders):
    def _target(self):
        return self
