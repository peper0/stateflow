import functools
import inspect
import logging
from abc import abstractmethod
from typing import Any, Callable, Mapping, NamedTuple, Sequence, TypeVar, Union

from stateflow.call_result import CmCallResult
from stateflow.common import CoroutineFunction, deprecated_interactive_mode, ev, is_observable
from stateflow.internal_utils import bind_arguments

T = TypeVar('T')


def maybe_eval(call_result: 'CallResult[T]'):
    if deprecated_interactive_mode:
        ev(call_result)


def args_need_reaction(args: tuple, kwargs: dict):
    return any((is_observable(arg) for arg in args + tuple(kwargs.values())))


async def postprocess_async_call_result(cr: 'AsyncCallResult[T]'):
    raise NotImplemented()
    # from stateflow.var import AsyncCache
    # res = AsyncCache(cr)
    # if deprecated_interactive_mode:
    #     await aev(res)
    # return res


class DecoratorParams(NamedTuple):
    pass_args: set[str] = None,
    other_deps: set[str] = None,
    dep_only_args: Sequence[str] = None


class ReactiveFunction:
    """
    A python callable wrapped to be reactive, i.e. when called it produces an `Observable` that will call the wrapped
    callable whenever any of the arguments changes. The real __call__ method is implemented in subclasses.
    """

    def __init__(self, func: Union[CoroutineFunction, Callable], decorator_params: DecoratorParams = DecoratorParams()):
        self.callable = func
        self.decorator_params = decorator_params
        try:
            self.signature = inspect.signature(func)
        except ValueError:
            self.signature = None
        self.args_names = list(self.signature.parameters) if self.signature else None
        functools.update_wrapper(self, func)

    def really_call(self, args, kwargs):
        return self.callable(*args, **kwargs)

    def __get__(self, instance, instancetype):
        """
        Implement the descriptor protocol to make decorating instance method possible.
        """
        if instance is None:
            logging.error("instance is None")
        return functools.partial(self.__call__, instance)

    def __str__(self):
        return 'DecoratedFunction({})'.format(self.callable)

    def dispatch_call(self, args: Sequence[Any], kwargs: Mapping[str, Any], result_factory: Callable):
        """The user called the reactive function. We either simply call the wrapped function or return a CallResult,
        that wraps the result and will be notified when the arguments change."""
        args, kwargs = bind_arguments(self.signature, args, kwargs)
        if not args_need_reaction(args, kwargs):
            # if no args need reaction, just call the function
            return self.really_call(args, kwargs)
        from stateflow.var import Cache  # avoid circular import
        cr = Cache(result_factory(self, args, kwargs))
        maybe_eval(cr)
        return cr

    @abstractmethod
    def __call__(self, *args, **kwargs):
        ...


class SyncReactiveFunction(ReactiveFunction):

    def __call__(self, *args, **kwargs):
        from stateflow.call_result import SyncCallResult  # local import to avoid circular import
        return self.dispatch_call(args, kwargs, SyncCallResult)


class ReactiveCmFunction(ReactiveFunction):
    """
    Wraps a function that returns a context manager which should be __enter__ed at the beginning and __exited__ on
    finalization (e.g. when the arguments change).
    """

    def __call__(self, *args, **kwargs):
        from stateflow.call_result import CmCallResult  # local import to avoid circular import
        return self.dispatch_call(args, kwargs, CmCallResult)


class AsyncReactiveFunction(ReactiveFunction):
    def __call__(self, *args, **kwargs):
        raise NotImplementedError()
        # from stateflow.call_result import AsyncCallResult  # avoid circular import
        # return postprocess_async_call_result(AsyncCallResult(self, args, kwargs))
