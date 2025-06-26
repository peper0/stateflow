"""
Exceptions definitions.
"""

import traceback
from contextlib import suppress


class NotInitializedError(Exception):
    def __init__(self):
        super().__init__('not initialized')


class FinalizedError(Exception):
    def __init__(self):
        super().__init__('observable cannot be read once finalized')


class ArgEvalError(Exception):
    """
    A reactive argument is in error state. The argument error should be the *cause* of this error.
    """

    def __init__(self, arg_name, function_name, call_stack, cause):
        super().__init__()
        self.__cause__ = cause
        #        super().__init__("error in argument '{}' of '{}'".format(arg_name, function_name))
        self.call_stack = call_stack
        self.arg_name = arg_name
        self.function_name = function_name

    def __str__(self):
        # stack2 = traceback.extract_tb(self.__cause__.__traceback__.tb_next)
        return "While evaluating argument '{}' of '{}' called at (most recent call last):\n{}" \
            .format(self.arg_name, self.function_name,
                    ''.join(traceback.format_list(self.call_stack)))


class EvError(Exception):
    """
    The main purpose of this error is to hide a part of stack between "ev()" and the place where this exception was raised.
    """
    pass


class ValidationError:
    """
    An argument doesn't satisfy some criterion so the function is not called.
    """

    def __init__(self, description):
        super().__init__(description)


class NotAssignable(Exception):
    """
    Raised when the "__assign__" method is called on the Observable that doesn't support assignment.
    """
    pass


def raise_need_async_eval():
    raise Exception("called __eval__ on the value that depends on an asynchronously evaluated value; use __aeval__")


class BodyEvalError(Exception):
    """
    An exception occured while evaluation of some Observable.
    """

    def __init__(self, definition_stack, cause):
        self.defined_stack = definition_stack
        self.__cause__ = cause

    def __str__(self):
        stack2 = []
        with suppress(Exception):
            stack2 = traceback.extract_tb(self.__cause__.__traceback__)
        return "While evaluating function body at (most recent call last):\n" + ''.join(
            traceback.format_list(self.defined_stack + stack2))
