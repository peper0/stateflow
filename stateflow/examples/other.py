"""
Other examples
~~~~~~~~~~~~~~~~
Normally variables are being updated only when it's needed.

>>> from stateflow import reactive, var, const, assign
>>> @reactive
... def square(a):
...     print("computing square of {}".format(a))
...     return a*a
>>>
>>> a = var(1)
>>> b = square(a)
>>> assign(a, 2)
>>> # nothing is printed, no code is executed
>>> assign(a, 3)
>>> print(b)
computing square of 3
9
>>> c = square(4)
>>> # nothing is printed, no code is executed
>>> print(c)
computing square of 4
16



Repr examples
~~~~~~~~~~~~~~~~

>>> a = var(123)
>>> print(repr(a))
Var(123)

>>> a = const(var(123))
>>> print(repr(a))
Const(Var(123))

>>> a = var()
>>> print(repr(a))
Var(<NotInitializedError: not initialized>)

>>> a = var(var())
>>> print(repr(a))
Var(<NotInitializedError: not initialized>)


repr examples
~~~~~~~~~~~~~~~~

>>> a = var(123)
>>> repr(a)
'Var(123)'

>>> a = const(var(123))
>>> repr(a)
'Const(Var(123))'

>>> a = var()
>>> repr(a)
'Var(<NotInitializedError: not initialized>)'

>>> a = var(var())
>>> repr(a)
'Var(<NotInitializedError: not initialized>)'


ev
~~~~~~~~~~~~~~~~
>>> from stateflow import ev
>>>
>>> repr(ev(123))
'123'
>>> repr(ev(var(123)))
'123'
>>> repr(ev(var(var(123))))
'123'


ev_one
~~~~~~~~~~~~~~~~
>>> from stateflow import ev_one
>>>
>>> repr(ev_one(123))
Traceback (most recent call last):
  ...
AssertionError
>>> repr(ev_one(var(123)))
'123'
>>> repr(ev_one(var(var(123))))
'Var(123)'


assign
~~~~~~~~~~~~~~~~
>>> from stateflow import assign
>>>
>>> inner = var(123)
>>> a = var(inner)
>>> repr(a)
'Var(Var(123))'
>>> assign(ev_one(a), 2)
>>> repr(a)
'Var(Var(2))'
>>> assign(a, 2)
>>> repr(a)
'Var(2)'

a function with finalization
~~~~~~~~~~~~~~~~
>>> from stateflow import reactive
>>>
>>> @reactive
... def foo(a):
...     print("initialized with {}".format(a))
...     yield "something with {}".format(a)
...     print("finalized {}".format(a))
>>>
>>> a = var(123)
>>> b = foo(a)
>>> print(ev(b))
initialized with 123
something with 123
>>> print(ev(b))
something with 123
>>> assign(a, 456)
>>> c = ev(b)
finalized 123
initialized with 456
>>> finalize(c)

"""



from stateflow import reactive