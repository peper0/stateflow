"""
Exceptions definitions.
"""

import traceback


class NotInitializedError(Exception):
    def __init__(self):
        super().__init__('not initialized')


class SilentError(Exception):
    """
    An exception that is silently propagated and not raised unless explicit unwrapping is done on the variable.
    The error that is silenced should be the cause of this error.
    """

    def __init__(self, cause=None, *args):
        super().__init__(*args)
        if cause:
            self.__cause__ = cause


class ArgEvalError(SilentError):
    """
    A reactive argument is in error state. The argument error should be the cause of this error.
    """

    def __init__(self, arg_name, function_name, call_stack, cause):
        super().__init__(cause)
        #        super().__init__("error in argument '{}' of '{}'".format(arg_name, function_name))
        self.call_stack = call_stack
        self.arg_name = arg_name
        self.function_name = function_name

    def __str__(self):
        # stack2 = traceback.extract_tb(self.__cause__.__traceback__.tb_next)
        return "\nError while evaluating argument '{}' of '{}' called at (most recent call last):\n{}" \
            .format(self.arg_name, self.function_name,
                    ''.join(traceback.format_list(self.call_stack)))


class ValidationError(SilentError):
    """
    An argument doesn't satisfy some criterion so the function is not called.
    """

    def __init__(self, description):
        super().__init__(None, description)


class NotAssignable(Exception):
    """
    Raised when the "__assign__" method is called on the Observable that doesn't support assignment.
    """
    pass


def raise_need_async_eval():
    raise Exception("called __eval__ on the value that depends on an asynchronously evaluated value; use __aeval__")


class EvalError(Exception):
    """
    An exception occured while evaluation of some Observable.
    """

    def __init__(self, definition_stack, cause):
        self.defined_stack = definition_stack
        self.__cause__ = cause

    def __str__(self):
        stack2 = traceback.extract_tb(self.__cause__.__traceback__.tb_next.tb_next)
        return "\nError while evaluation (most recent call last):\n" + ''.join(
            traceback.format_list(self.defined_stack + stack2))
