import asyncio
import logging
import traceback
from abc import abstractmethod
from itertools import chain
from typing import Any, Dict, List, Set, Tuple

from stateflow import SilentError
from stateflow.common import Observable, T, ev, is_wrapper
from stateflow.decorators import DecoratedFunction
from stateflow.errors import ArgEvalError, EvalError, raise_need_async_eval
from stateflow.notifier import Notifier, ScopedName


class ArgsHelper:
    def __init__(self, args, kwargs, signature, callable):
        if signature:
            # support default parameters
            try:
                bound_args = signature.bind(*args, **kwargs)  # type: inspect.BoundArguments
                bound_args.apply_defaults()
            except Exception as e:
                raise Exception('during binding {}{}'.format(callable.__name__, signature)) from e
            args_names = list(signature.parameters)

            self.args = bound_args.args
            self.kwargs = bound_args.kwargs
            self.args_names = args_names[0:len(self.args)]
            self.args_names += [None] * (len(self.args) - len(self.args_names))
            self.kwargs_indices = [(args_names.index(name) if name in args_names else None)
                                   for name in self.kwargs.keys()]
        else:
            self.args = args
            self.kwargs = kwargs
            self.args_names = [None] * len(self.args)
            self.kwargs_indices = [None] * len(self.kwargs)

    def iterate_args(self):
        return ((index, name, arg) for name, (index, arg) in zip(self.args_names, enumerate(self.args)))

    def iterate_kwargs(self):
        return ((index, name, arg) for index, (name, arg) in zip(self.kwargs_indices, self.kwargs.items()))


def eval_args(args_helper: ArgsHelper, pass_args, func_name, call_stack) -> Tuple[List[Any], Dict[str, Any]]:
    def rewrap(index, name, arg):
        try:
            if index in pass_args or name in pass_args:
                return arg
            else:
                return ev(arg)
        except Exception as exception:
            raise ArgEvalError(name or str(index), func_name, call_stack, exception)

    return ([rewrap(index, name, arg) for index, name, arg in args_helper.iterate_args()],
            {name: rewrap(index, name, arg) for index, name, arg in args_helper.iterate_kwargs()})


def observe(arg, notifier):
    if isinstance(arg, Notifier):
        return arg.add_observer(notifier)
    else:
        return arg.__notifier__.add_observer(notifier)


def maybe_observe(arg, notifier):
    if is_wrapper(arg):
        observe(arg, notifier)


def observe_args(args_helper: ArgsHelper, pass_args: Set[str], notifier):
    for index, name, arg in chain(args_helper.iterate_args(), args_helper.iterate_kwargs()):
        if index not in pass_args and name not in pass_args:
            maybe_observe(arg, notifier)


class CallResult(Observable[T]):
    def __init__(self, decorated: DecoratedFunction, args, kwargs):
        with ScopedName(name=decorated.callable.__name__):
            self.decorated = decorated  # type: DecoratedFunction
            self._notifier = Notifier()

        # use dep_only_args
        for name in decorated.decorator.dep_only_args:
            if name in kwargs:
                arg = kwargs.pop(name)

                if isinstance(arg, (list, tuple)):
                    for a in arg:
                        observe(a, self.__notifier__)
                else:
                    observe(arg, self.__notifier__)

        # use other_deps
        for dep in decorated.decorator.other_deps:
            maybe_observe(dep, self.__notifier__)

        self.args_helper = ArgsHelper(args, kwargs, decorated.signature, decorated.callable)
        self.args = self.args_helper.args
        self.kwargs = self.args_helper.kwargs
        self._update_in_progress = False

        self.call_stack = traceback.extract_stack()[:-3]

        observe_args(self.args_helper, self.decorated.decorator.pass_args, self.__notifier__)

    @property
    def __notifier__(self):
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

    def _call(self):
        """
        returns one of:
        - an Observable,
        - a raw value (must be wrapped into Observable)
        - a coroutine (must be awaited),
        - a context manager (must be __enter__ed to obtain value, then __exited__ before next __enter__)
        - an async context manager (a mix of above)
        """
        assert self._update_in_progress == False, 'circular dependency containing "{}" called at:\n{}'.format(
            self.callable.__name__, self.call_stack)
        try:
            self._update_in_progress = True
            args, kwargs = eval_args(self.args_helper, self.decorated.decorator.pass_args,
                                     self.decorated.callable.__name__, self.call_stack)
            try:
                return self.decorated.really_call(args, kwargs)
            except SilentError as e:  # SilentError may be thrown from the function body too (e.g. from validators)
                # raise SilentError(EvalError(self.call_stack, e))
                raise e
            except Exception as e:
                raise EvalError(self.call_stack, e)
        finally:
            self._update_in_progress = False

    @abstractmethod
    def __eval__(self):
        pass


class SyncCallResult(CallResult[T]):
    def __eval__(self):
        return self._call()


class AsyncCallResult(CallResult[T]):
    async def __aeval__(self):
        return await self._call()

    def __eval__(self):
        raise Exception("called __eval__ on the value that depends on an asynchronously evaluated value; use __aeval__")


class CmCallResult(CallResult[T]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cm = None

    def __eval__(self):
        self._cleanup()
        self.cm = self._call()
        return self.cm.__enter__()

    def __del__(self):
        self._cleanup()

    def _cleanup(self):
        try:
            if self.cm:
                self.cm.__exit__(None, None, None)
                self.cm = None
        except Exception:
            logging.exception("ignoring exception in cleanup")


class AsyncCmCallResult(CallResult[T]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cm = None

    async def __aeval__(self):
        await self._cleanup()
        self.cm = self._call()
        return await self.cm.__aenter__()

    def __del__(self):
        asyncio.ensure_future(self._cleanup())

    async def _cleanup(self):
        try:
            if self.cm:
                cm = self.cm
                self.cm = None
                await cm.__aexit__(None, None, None)
        except Exception:
            logging.exception("ignoring exception in cleanup")

    def __eval__(self):
        raise_need_async_eval()
