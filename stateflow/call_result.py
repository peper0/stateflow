import asyncio
from inspect import Signature
import logging
import traceback
from abc import abstractmethod
from itertools import chain
from typing import Any, Dict, List, Mapping, Sequence, Set, Tuple, Callable, Optional, TypeVar, Union, cast, Type, Iterator, ContextManager, AsyncContextManager, Protocol, Generic, ForwardRef, Iterable
from types import TracebackType

from stateflow.common import Observable, T, ev, is_observable
from stateflow.errors import ArgEvalError, BodyEvalError, raise_need_async_eval, EvError
from stateflow.internal_utils import bind_arguments
from stateflow.notifier import Notifier, INotifier


# Forward reference for ReactiveFunction which is defined in function.py
ReactiveFunction = ForwardRef('stateflow.function.ReactiveFunction')


class ArgsHelper:
    def __init__(self, args: Tuple[Any, ...], kwargs: Dict[str, Any], signature: Optional[Signature], callable: Callable) -> None:
        if signature:
            # support default parameters
            try:
                self.args, self.kwargs = bind_arguments(signature, args, kwargs)
            except Exception as e:
                raise Exception('during binding {}{}'.format(callable.__name__, signature)) from e
            args_names = list(signature.parameters)


            self.args_names = args_names[0:len(self.args)]
            self.args_names += [None] * (len(self.args) - len(self.args_names))
            self.kwargs_indices = [(args_names.index(name) if name in args_names else None)
                                   for name in self.kwargs.keys()]
        else:
            self.args = args
            self.kwargs = kwargs
            self.args_names = [None] * len(self.args)
            self.kwargs_indices = [None] * len(self.kwargs)

    def iterate_args(self) -> Iterable[Tuple[int, Optional[str], Any]]:
        return ((index, name, arg) for name, (index, arg) in zip(self.args_names, enumerate(self.args)))

    def iterate_kwargs(self) -> Iterable[Tuple[Optional[int], str, Any]]:
        return ((index, name, arg) for index, (name, arg) in zip(self.kwargs_indices, self.kwargs.items()))


def eval_args(args_helper: ArgsHelper, pass_args: Set[str], func_name: str, call_stack: List[Any]) -> Tuple[List[Any], Dict[str, Any]]:
    def rewrap(index: Optional[int], name: Optional[str], arg: Any) -> Any:
        try:
            if index in pass_args or name in pass_args:
                return arg
            else:
                return ev(arg)
        except EvError as exception:
            raise ArgEvalError(name or str(index), func_name, call_stack, exception.__cause__)
        except Exception as e:
             raise ArgEvalError(name or str(index), func_name, call_stack,
                                e.with_traceback(e.__traceback__.tb_next.tb_next.tb_next))

    return ([rewrap(index, name, arg) for index, name, arg in args_helper.iterate_args()],
            {name: rewrap(index, name, arg) for index, name, arg in args_helper.iterate_kwargs()})


def observe(arg: Any, notifier: INotifier) -> None:
    if isinstance(arg, INotifier):
        return arg.add_observer(notifier)
    else:
        return arg.__notifier__().add_observer(notifier)


def maybe_observe(arg: Any, notifier: INotifier) -> None:
    if is_observable(arg):
        observe(arg, notifier)


def observe_args(args_helper: ArgsHelper, pass_args: Set[str], notifier: INotifier) -> None:
    for index, name, arg in chain(args_helper.iterate_args(), args_helper.iterate_kwargs()):
        if index not in pass_args and name not in pass_args:
            maybe_observe(arg, notifier)


def callable_name(c: Callable[..., Any]) -> str:
    if hasattr(c, '__name__'):
        return c.__name__
    else:
        return "<unknown>"

class CallResult(Observable[T]):
    """
    An observable that represents the result of a reactive function call. It will be updated when the function's
    arguments change.
    """
    def __init__(self, reactive_function: ReactiveFunction, args: Tuple[Any, ...], kwargs: Dict[str, Any]) -> None:
        self.reactive_function = reactive_function
        self._notifier = Notifier()
        self._notifier.name = 'CallResult of {}'.format(callable_name(reactive_function.callable))

        # use dep_only_args
        for name in reactive_function.decorator_params.dep_only_args:
            if name in kwargs:
                arg = kwargs.pop(name)

                if isinstance(arg, (list, tuple)):
                    for a in arg:
                        observe(a, self.__notifier__())
                else:
                    observe(arg, self.__notifier__())

        # use other_deps
        for dep in reactive_function.decorator_params.other_deps:
            maybe_observe(dep, self.__notifier__())

        self.args_helper = ArgsHelper(args, kwargs, reactive_function.signature, reactive_function.callable)
        self.args = self.args_helper.args
        self.kwargs = self.args_helper.kwargs
        self._update_in_progress = False

        self.call_stack = traceback.extract_stack()[:-3]

        observe_args(self.args_helper, self.reactive_function.decorator_params.pass_args, self.__notifier__())

    def __notifier__(self) -> Notifier:
        return self._notifier

    # @contextmanager
    # def _handle_exception(self, reraise=True):
    #     try:
    #         yield
    #
    #     except Exception as e:
    #         if isinstance(e, HideStackHelper):
    #             e = e.__cause__
    #         if isinstance(e, SilentError):
    #             e = e.__cause__
    #             reraise = False  # SilentError is not re-raised by definition
    #         self._exception = e
    #         if reraise:
    #             raise HideStackHelper() from e

    def _call(self) -> None:
        """
        returns one of:
        - an Observable,
        - a raw value (must be wrapped into Observable)
        - a coroutine (must be awaited),
        - a context manager (must be __enter__ed to obtain value, then __exited__ before next __enter__)
        - an async context manager (a mix of above)

        :raise BodyEvalError or ArgEvalError. Other exceptions are kind of internal error.
        """
        assert self._update_in_progress == False, 'circular dependency containing "{}" called at:\n{}'.format(
            callable_name(self.reactive_function.callable), self.call_stack)
        try:
            self._update_in_progress = True
            args, kwargs = eval_args(self.args_helper, self.reactive_function.decorator_params.pass_args,
                                     callable_name(self.reactive_function.callable), self.call_stack)

            try:
                return self.reactive_function.really_call(args, kwargs)
            except Exception as e:
                raise BodyEvalError(self.call_stack, e.with_traceback(e.__traceback__.tb_next.tb_next))
        finally:
            self._update_in_progress = False

    @abstractmethod
    def __eval__(self) -> Any:
        pass


class SyncCallResult(CallResult[T]):
    def __eval__(self) -> Any:
        return self._call()


class AsyncCallResult(CallResult[T]):
    async def __aeval__(self) -> Any:
        return await self._call()

    def __eval__(self) -> Any:
        raise Exception("called __eval__ on the value that depends on an asynchronously evaluated value; use __aeval__")


class CmCallResult(CallResult[T]):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.cm: Optional[ContextManager[Any]] = None

    def __eval__(self) -> Any:
        self.__finalize__()
        self.cm = self._call()
        return self.cm.__enter__()

    def __del__(self) -> None:
        self.__finalize__()

    def __finalize__(self) -> None:
        try:
            if self.cm:
                self.cm.__exit__(None, None, None)
                self.cm = None
        except Exception:
            logging.exception("ignoring exception in cleanup")


class AsyncCmCallResult(CallResult[T]):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.cm: Optional[AsyncContextManager[Any]] = None

    async def __aeval__(self) -> Any:
        await self.__afinalize__()
        self.cm = self._call()
        return await self.cm.__aenter__()

    def __del__(self) -> None:
        asyncio.ensure_future(self.__afinalize__())

    async def __afinalize__(self) -> None:
        try:
            if self.cm:
                cm = self.cm
                self.cm = None
                await cm.__aexit__(None, None, None)
        except Exception:
            logging.exception("ignoring exception in cleanup")

    def __eval__(self) -> Any:
        raise_need_async_eval()
