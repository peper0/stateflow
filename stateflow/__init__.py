name = "stateflow"

from stateflow.common import Observable, assign, ev, ev_def, ev_exception, ev_one
from stateflow.decorators import reactive, reactive_finalizable
from stateflow.errors import ArgEvalError, BodyEvalError, NotAssignable, NotInitializedError, ValidationError, EvError
from stateflow.notifier import Notifier
from stateflow.utils import *

__all__ = ['Observable', 'assign', 'ev', 'ev_def', 'ev_exception', 'ev_one', 'reactive', 'reactive_finalizable',
           'ArgEvalError', 'BodyEvalError', 'NotAssignable', 'NotInitializedError', 'ValidationError', 'EvError',
           'Notifier']


BLEH="""Traceback (most recent call last):
  File "<doctest exceptions[5]>", line 3, in foo
    raise Exception('boo')
Exception: boo

The above exception was the direct cause of the following exception:

stateflow.errors.BodyEvalError: While evaluating function body at (most recent call last):
  File "/home/peper/opt/pycharm-community-2018.3.1/helpers/pycharm/docrunner.py", line 352, in <module>
    runner.start()
  File "/home/peper/opt/pycharm-community-2018.3.1/helpers/pycharm/docrunner.py", line 106, in start
    self.run(test)
  File "/home/peper/anaconda3/lib/python3.6/doctest.py", line 1476, in run
    return self.__run(test, compileflags, out)
  File "/home/peper/opt/pycharm-community-2018.3.1/helpers/pycharm/docrunner.py", line 140, in __run
    compileflags, 1), test.globs)
  File "<doctest exceptions[8]>", line 1, in <module>
    ev(foo(a))  #doctest: +ELLIPSIS
  File "<doctest exceptions[5]>", line 3, in foo
    raise Exception('boo')


The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/home/peper/opt/pycharm-community-2018.3.1/helpers/pycharm/docrunner.py", line 140, in __run
    compileflags, 1), test.globs)
  File "<doctest exceptions[8]>", line 1, in <module>
    ev(foo(a))  #doctest: +ELLIPSIS
  File "/home/peper/src/stateflow/stateflow/common.py", line 78, in ev
    return ev_strict(v)
  File "/home/peper/src/stateflow/stateflow/common.py", line 52, in ev_strict
    raise EvError() from e.with_traceback(None)
stateflow.errors.EvError"""

BLEH2="""Traceback (most recent call last):
  File "<doctest exceptions[5]>", line 3, in foo
    raise Exception('boo')
Exception: boo

The above exception was the direct cause of the following exception:

stateflow.errors.BodyEvalError: While evaluating function body at (most recent call last):
  File "/home/peper/opt/pycharm-community-2018.3.1/helpers/pycharm/docrunner.py", line 352, in <module>
    runner.start()
  File "/home/peper/opt/pycharm-community-2018.3.1/helpers/pycharm/docrunner.py", line 106, in start
    self.run(test)
  File "/home/peper/anaconda3/lib/python3.6/doctest.py", line 1476, in run
    return self.__run(test, compileflags, out)
  File "/home/peper/opt/pycharm-community-2018.3.1/helpers/pycharm/docrunner.py", line 140, in __run
    compileflags, 1), test.globs)
  File "<doctest exceptions[8]>", line 1, in <module>
    ev(foo(a))  #doctest: +ELLIPSIS
  File "<doctest exceptions[5]>", line 3, in foo
    raise Exception('boo')


The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/home/peper/opt/pycharm-community-2018.3.1/helpers/pycharm/docrunner.py", line 140, in __run
    compileflags, 1), test.globs)
  File "<doctest exceptions[8]>", line 1, in <module>
    ev(foo(a))  #doctest: +ELLIPSIS
  File "/home/peper/src/stateflow/stateflow/common.py", line 78, in ev
    return ev_strict(v)
  File "/home/peper/src/stateflow/stateflow/common.py", line 52, in ev_strict
    raise EvError() from e.with_traceback(None)"""