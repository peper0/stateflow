import asyncio
import contextlib
import functools
import inspect
import logging
from contextlib import suppress
from typing import Callable, Iterable, Union, overload

import asyncio_extras

from stateflow.common import CoroutineFunction, T, aev, ev, is_wrapper
from stateflow.errors import SilentError


def make_reactive_result(cr: 'CallResult[T]'):
    from stateflow.forwarders import Forwarders
    from stateflow.var import Cache
    res = Forwarders(Cache(cr))
    # TODO: make some configurable policies about: evaluating function immediately; treating errors in this call
    with suppress(SilentError):
        ev(res)
    return res


async def make_async_reactive_result(cr: 'CallResult[T]'):
    from stateflow.forwarders import Forwarders
    from stateflow.var import AsyncCache
    res = Forwarders(AsyncCache(cr))
    with suppress(SilentError):
        await aev(res)
    return res


class Reactive:
    def __init__(self, pass_args, other_deps, dep_only_args):
        self.dep_only_args = dep_only_args
        self.other_deps = other_deps
        self.pass_args = set(pass_args)

    def __call__(self, func):
        """
        Decorate the function.
        """

        if asyncio.iscoroutinefunction(func):
            def factory(decorated, args, kwargs):
                # import here to avoid circular dependency (AsyncReactiveProxy does Reactive.__call__ for it's members)
                from stateflow.call_result import AsyncCallResult
                call_result = AsyncCallResult(decorated, args, kwargs)
                if args_need_reaction(call_result.args, call_result.kwargs):
                    return make_async_reactive_result(call_result)
                else:
                    return decorated.really_call(args, kwargs)
        elif hasattr(func, '__call__'):
            def factory(decorated, args, kwargs):
                # import here to avoid circular dependency (SyncReactiveProxy does Reactive.__call__ for it's members)
                from stateflow.call_result import SyncCallResult
                res = SyncCallResult(decorated, args, kwargs)
                if args_need_reaction(res.args, res.kwargs):
                    return make_reactive_result(res)
                else:
                    return decorated.really_call(args, kwargs)
        else:
            raise Exception("{} is neither a function nor a coroutine function (async def...)".format(repr(func)))
        return DecoratedFunction(self, factory, func)


class DecoratedFunction:
    def __init__(self, decorator: Reactive, factory, func: Union[CoroutineFunction, Callable]):
        self.decorator = decorator
        self.factory = factory
        self.callable = func
        try:
            self.signature = inspect.signature(func)
        except ValueError:
            self.signature = None
        self.args_names = list(self.signature.parameters) if self.signature else None
        functools.update_wrapper(self, func)

    def really_call(self, args, kwargs):
        return self.callable(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        """
        Bind arguments and return an `Observable` that calls the function on __eval__ and notifies when any argument
        changes.
        """
        return self.factory(self, args, kwargs)

    def __get__(self, instance, instancetype):
        """
        Implement the descriptor protocol to make decorating instance method possible.
        """
        if instance is None:
            logging.error("instance is None")
        return functools.partial(self.__call__, instance)

    def __str__(self):
        return 'DecoratedFunction({})'.format(self.callable)


@overload
def reactive(f: Callable) -> Callable:
    pass


@overload
def reactive(pass_args: Iterable[str] = None,
             other_deps: Iterable[str] = None,
             dep_only_args: Iterable[str] = None) -> Callable:
    pass


def reactive(pass_args: Iterable[str] = None,
             other_deps: Iterable[str] = None,
             dep_only_args: Iterable[str] = None):
    if callable(pass_args):
        # a shortcut that allows simple @reactive instead of @reactive()
        return reactive()(pass_args)

    pass_args = set(pass_args or [])
    dep_only_args = set(dep_only_args or [])
    other_deps = other_deps or []

    return Reactive(pass_args=pass_args, other_deps=other_deps, dep_only_args=dep_only_args)


@overload
def reactive_finalizable(f: Callable) -> Callable:
    pass


@overload
def reactive_finalizable(pass_args: Iterable[str] = None,
                         other_deps: Iterable[str] = None,
                         dep_only_args: Iterable[str] = None) -> Callable:
    pass


class ReactiveCm(Reactive):
    def __call__(self, func):
        """
        Decorate the function.
        """
        if hasattr(func, '_isasync') and func._isasync:
            def factory(decorated, args, kwargs):
                # import here to avoid circular dependency (AsyncReactiveProxy does Reactive.__call__ for it's members)
                from stateflow.call_result import AsyncCmCallResult
                return make_async_reactive_result(AsyncCmCallResult(decorated, args, kwargs))

        elif hasattr(func, '__call__'):
            def factory(decorated, args, kwargs):
                from stateflow.call_result import CmCallResult
                return make_reactive_result(CmCallResult(decorated, args, kwargs))
        else:
            raise Exception("{} is neither a function nor a coroutine function (async def...)".format(repr(func)))
        return DecoratedFunction(self, factory, func)


def reactive_finalizable(pass_args: Iterable[str] = None,
                         other_deps: Iterable[str] = None,
                         dep_only_args: Iterable[str] = None,
                         ):
    if callable(pass_args):
        # a shortcut that allows simple @reactive instead of @reactive()
        return reactive_finalizable()(pass_args)

    pass_args = set(pass_args or [])
    dep_only_args = set(dep_only_args or [])
    other_deps = other_deps or []

    deco = ReactiveCm(pass_args, dep_only_args, other_deps)

    def wrap(f):
        if inspect.isasyncgenfunction(f):
            ff = asyncio_extras.async_contextmanager(f)
            ff._isasync = True

            # noinspection PyTypeChecker
            return deco(ff)
        else:
            return deco(contextlib.contextmanager(f))

    return wrap


def args_need_reaction(args: tuple, kwargs: dict):
    return any((is_wrapper(arg) for arg in args + tuple(kwargs.values())))
