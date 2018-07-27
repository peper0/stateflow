"""
Operator example
~~~~~~~~~~~~~~~~

>>> from stateflow import var, assign
>>> a = var(1)
>>> b = var(2)
>>> a_plus_b = a + b
>>> print(a_plus_b)
3
>>> assign(a, 4)
>>> print(a_plus_b)
6


Function example
~~~~~~~~~~~~~~~~

>>> from stateflow import var, assign, reactive
>>> a = var(1)
>>> b = var(2)
>>>
>>> @reactive
... def elaborate(a, b):
...     return "{} + {} = {}".format(a, b, a+b)
>>>
>>> text = elaborate(a, b)
>>> print(text)
1 + 2 = 3
>>> assign(a, 4)
>>> print(text)
4 + 2 = 6

Todo:

* ev

* exception handling (many examples)

* reactive_finalizable
* volatile

"""
