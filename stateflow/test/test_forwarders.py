import asynctest
from numpy.testing import assert_array_equal

from stateflow import ArgEvalError, const, ev, var
from stateflow.errors import EvalError


class Forwarders(asynctest.TestCase):
    async def test_operator_add(self):
        a = var(2)
        b = const(5)
        res = a + b
        self.assertEqual(ev(res), 7)

        a @= 6
        self.assertEqual(ev(res), 11)  # 6+5

    async def test_operator_mul_numpy(self):
        import numpy as np
        a = var(2)
        b = np.array([1, 2])
        res = a * b
        assert_array_equal(ev(res), np.array([2, 4]))

    async def test_operator_cmp(self):
        a = var(2)
        b = var(5)
        a_greater = a > b
        self.assertFalse(ev(a_greater))

        a @= 5
        self.assertFalse(ev(a_greater))

        a @= 6
        self.assertTrue(ev(a_greater))

    async def test_operator_neg(self):
        a = var(2)
        res = -a
        self.assertEqual(ev(res), -2)

        a @= -5
        self.assertEqual(ev(res), 5)

    async def test_operator_assign_add(self):
        a = var(2)
        res = a + 5
        self.assertEqual(ev(res), 7)

        a += 3
        self.assertEqual(ev(a), 5)
        self.assertEqual(ev(res), 10)

    async def test_operator_getitem_and_exception(self):
        a = var(('a', 'b'))
        res = a[1]
        self.assertEqual(ev(res), 'b')

        a @= ('A', 'B', 'C')
        self.assertEqual(ev(res), 'B')

        a @= ('A',)
        with self.assertRaises(EvalError):
            ev(res)

        a @= 5
        with self.assertRaises(EvalError):
            ev(res)

        # check if it works again
        a @= (1, 2, 3)
        self.assertEqual(ev(res), 2)

    async def test_operator_getitem_setitem_delitem(self):
        a = var()
        res = a[1]
        with self.assertRaises(ArgEvalError):
            ev(res)

        a @= [1, 2, 3]
        self.assertEqual(ev(res), 2)

        a[1] = 'hej'
        self.assertEqual(ev(res), 'hej')

        del a[1]
        self.assertEqual(ev(res), 3)

    async def test_operator_var_index(self):
        a = var()
        b = var()
        res = a[b]

        b @= 2
        a @= [1, 2, 3]
        self.assertEqual(ev(res), 3)

        b @= 0
        self.assertEqual(ev(res), 1)
