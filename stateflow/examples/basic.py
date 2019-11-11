"""
Operators
~~~~~~~~~~~~~~~~
Let's start with a trivial example.
>>> from stateflow import var, assign
>>> a = var(1)
>>> b = var(2)
>>> a_plus_b = a + b
>>> print(a_plus_b)
3
>>> assign(a, 4)
>>> print(a_plus_b)
6

What we do here is:
1. Define two variables: `a` and `b`.
2. Define a derived observable `a_plus_b` that is always equal to a sum of these variables.
3. Print the sum.
4. Change one of these variables and then print the sum again. Note that the sum is not explicitly computed again.


Functions
~~~~~~~~~~~~~~~~
If we want to declare a derived variable that cannot be computed using simple operators, the `reactive` decorator may be
helpful. Inside this function `a` and `b` are ordinary variables.
>>> from stateflow import var, reactive
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

It's also easy to make a reactive version of some already existing function:
>>> a = var()
>>> import math
>>> floor = reactive(math.floor)
>>> floor_a = floor(a)
>>> assign(a, 1.2)
>>> print(floor_a)
1


Methods
~~~~~~~~~~~~~~~~
>>> from stateflow import var, reactive
>>> a = var("Foo")
>>> upper_a = a.upper()
>>>
>>> print(upper_a)
FOO
>>> assign(a, "Bar")
>>> print(upper_a)
BAR


Fields
~~~~~~~~~~~~~~~~
>>> a = var(range(5))
>>> a_stop = a.stop
>>> print(a_stop)
5
>>> assign(a, range(10))
>>> print(a_stop)
10


Indexing in a variable
~~~~~~~~~~~~~~~~
>>> a = var([4, 3, 5])
>>> a_1 = a[1]
>>> print(a_1)
3
>>> assign(a, "bar")
>>> print(a_1)
a


Indexing using a variable
~~~~~~~~~~~~~~~~
>>> from stateflow import const
>>> sequence = 'foobar'
>>> index = var(0)
>>> element = const(sequence)[index]
>>> print(element)
f
>>> assign(index, 3)
>>> print(element)
b



"""

"""


#
# Note that square of "2" was not computed since the result would not be used.
#
# We can enforce calling of a reactive function every time when it's arguments change:
# >>> from stateflow import volatile
# >>> b = volatile(square)(a)
# computing square of 3
# >>> assign(a, 4)
# computing square of 4
# >>> assign(a, 5)
# computing square of 5
#
# The `volatile` function can be used as a decorator as well:
# >>> @volatile
# >>> @reactive
# ... def print_on_change(a):
# ...     print("variable is {}".format(a))
# >>>
# >>> a = var(1)
# >>> print_holder = print_on_change(a)
# variable is 1
# >>> assign(a, 2)
# variable is 2
# >>> assign(a, 3)
# variable is 3


Todo:

* ev
* members


* exception handling (many examples)

* reactive_finalizable
* volatile with condition
* replace volatile with something


"""
