"""
Operators
~~~~~~~~~~~~~~~~
Let's start with a trivial example.
>>> from stateflow import var, assign, reactive, ev
>>> a = var(1)
>>> @reactive
... def foo(notused):
...     raise Exception('boo')
>>> @reactive
... def bar(first_arg):
...     return first_arg
>>> try: ev(foo(a))  #doctest: +ELLIPSIS
... except: traceback.print_exc(file=sys.stdout)
Traceback (most recent call last):
  File ... in foo
    raise Exception('boo')
Exception: boo
<BLANKLINE>
The above exception was the direct cause of the following exception:
<BLANKLINE>
stateflow.errors.BodyEvalError: While evaluating function body at (most recent call last):
...
    try: ev(foo(a))  #doctest: +ELLIPSIS
  File ... in foo
    raise Exception('boo')
<BLANKLINE>
<BLANKLINE>
The above exception was the direct cause of the following exception:
<BLANKLINE>
Traceback (most recent call last):
...
    try: ev(foo(a))  #doctest: +ELLIPSIS
  ...
stateflow.errors.EvError
>>> b = bar(foo(a))
>>> c = bar(b)
>>> try: print(c)  #doctest: +ELLIPSIS
... except: traceback.print_exc(file=sys.stdout)
Traceback (most recent call last):
  File ... in foo
    raise Exception('boo')
Exception: boo
<BLANKLINE>
The above exception was the direct cause of the following exception:
<BLANKLINE>
stateflow.errors.BodyEvalError: While evaluating function body at (most recent call last):
...
    b = bar(foo(a))
  File ... in foo
    raise Exception('boo')
<BLANKLINE>
<BLANKLINE>
The above exception was the direct cause of the following exception:
<BLANKLINE>
stateflow.errors.ArgEvalError: While evaluating argument 'first_arg' of 'bar' instanced at (most recent call last):
...
    b = bar(foo(a))
<BLANKLINE>
<BLANKLINE>
The above exception was the direct cause of the following exception:
<BLANKLINE>
stateflow.errors.ArgEvalError: While evaluating argument 'first_arg' of 'bar' instanced at (most recent call last):
...
    c = bar(b)
<BLANKLINE>
<BLANKLINE>
The above exception was the direct cause of the following exception:
<BLANKLINE>
Traceback (most recent call last):
...
    try: print(c)  #doctest: +ELLIPSIS
  ...
    raise EvError() from e.with_traceback(None)
stateflow.errors.EvError
"""

import doctest, sys, traceback
