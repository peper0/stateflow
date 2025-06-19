import asyncio
import contextlib
import functools
import inspect
import logging
from typing import Callable, Sequence, Union, overload

from typing_extensions import deprecated

from stateflow.call_result import CmCallResult
from stateflow.common import CoroutineFunction, T, is_observable
from stateflow.function import AsyncReactiveFunction, DecoratorParams, ReactiveCmFunction, SyncReactiveFunction





@deprecated("Use ReactiveFunctionBase-derived classes")
class DecoratedFunction:
    def __init__(self, factory, func: Union[CoroutineFunction, Callable], decorator_params: DecoratorParams):
        self.factory = factory
        self.callable = func
        self.decorator = decorator_params
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


#FIXME: try composition instead of inheritance

@overload
def reactive(f: Callable) -> Callable:
    pass


@overload
def reactive(pass_args: Sequence[str] = None,
             other_deps: Sequence[str] = None,
             dep_only_args: Sequence[str] = None) -> Callable:
    pass



def reactive(pass_args: Sequence[str] = None,
             other_deps: Sequence[str] = None,
             dep_only_args: Sequence[str] = None):
    if callable(pass_args):
        # a shortcut that allows simple @reactive instead of @reactive()
        return reactive()(pass_args)

    decorator_params = DecoratorParams(
        pass_args=set(pass_args or []),
        dep_only_args=set(dep_only_args or []),
        other_deps=other_deps or []
    )


    def wrapper(func):
        """
        Decorate the function.
        """
        # FIXME: put every creating code into a function
        if asyncio.iscoroutinefunction(func):
            return AsyncReactiveFunction(func, decorator_params)
        elif inspect.isgeneratorfunction(func):
            return ReactiveCmFunction(contextlib.contextmanager(func), decorator_params)
        elif hasattr(func, '__call__'):
            return SyncReactiveFunction(func, decorator_params)
        # elif inspect.isasyncgenfunction(func) or inspect.isgeneratorfunction(func):
        #     import asyncio_extras
        #     ff = asyncio_extras.async_contextmanager(func)
        #     ff._isasync = True
        #     if hasattr(func, '_isasync') and func._isasync:
        #         def factory(decorated, args, kwargs):
        #             # import here to avoid circular dependency (AsyncReactiveProxy does Reactive.__call__ for its members)
        #             from stateflow.call_result import AsyncCmCallResult
        #             return make_async_reactive_result(AsyncCmCallResult(decorated, args, kwargs))
        #
        #     elif hasattr(func, '__call__'):
        #         def factory(decorated, args, kwargs):
        #             from stateflow.call_result import CmCallResult
        #             return postprocess_call_result(CmCallResult(decorated, args, kwargs))
        #     else:
        #         raise Exception("{} is neither a function nor a coroutine function (async def...)".format(repr(func)))
        #     return DecoratedFunction(factory, func, decorator_params)
        # else:
        #     return deco(contextlib.contextmanager(f))
        else:
            raise Exception("{} is neither a function nor a coroutine function (async def...)".format(repr(func)))




    return wrapper


# @overload
# def reactive_finalizable(f: Callable) -> Callable:
#     pass
#
#
# @overload
# def reactive_finalizable(pass_args: Iterable[str] = None,
#                          other_deps: Iterable[str] = None,
#                          dep_only_args: Iterable[str] = None) -> Callable:
#     pass



# def reactive_finalizable(pass_args: Iterable[str] = None,
#                          other_deps: Iterable[str] = None,
#                          dep_only_args: Iterable[str] = None,
#                          ):
#     if callable(pass_args):
#         # a shortcut that allows simple @reactive instead of @reactive()
#         return reactive_finalizable()(pass_args)
#
#     pass_args = set(pass_args or [])
#     dep_only_args = set(dep_only_args or [])
#     other_deps = other_deps or []
#
#     deco = ReactiveCm(pass_args, dep_only_args, other_deps)
#
#     def wrap(f):
#         if inspect.isasyncgenfunction(f):
#             import asyncio_extras
#             ff = asyncio_extras.async_contextmanager(f)
#             ff._isasync = True
#
#             # noinspection PyTypeChecker
#             return deco(ff)
#         else:
#             return deco(contextlib.contextmanager(f))
#
#     return wrap



