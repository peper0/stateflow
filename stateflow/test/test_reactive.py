import gc
import logging
import unittest
from unittest.mock import Mock

import pytest

from stateflow import EvError, Observable, assign, ev, ev_exception, reactive, \
    var, volatile
from stateflow.notifier import dump_notifiers_to_dot


# logging.basicConfig(level=logging.DEBUG)
# logging.getLogger('refresher').setLevel(logging.DEBUG)

# TODO: moove to some test utils
class ValueAndTypeEq:
    def __init__(self, value):
        self._value = value

    def __eq__(self, other):
        return isinstance(other, type(self._value)) and self._value == other


@reactive
def my_sum(a, b):
    return a + b


class SimpleReactive(unittest.TestCase):
    def test_vals_positional(self):
        res = my_sum(2, 5)
        self.assertIsInstance(res, int)
        self.assertEqual(res, 7)

    def test_vals_keyword(self):
        res = my_sum(a=2, b=5)
        self.assertIsInstance(res, int)
        self.assertEqual(res, 7)

    def test_var_val_positional(self):
        a = var(2)
        res = my_sum(a, 5)
        self.assertIsInstance(res, Observable)
        self.assertEqual(ev(res), 7)

    def test_var_val_keyword(self):
        a = var(2)
        res = my_sum(a=a, b=5)
        self.assertIsInstance(res, Observable)
        self.assertEqual(ev(res), 7)

    def test_var_var(self):
        a = var(2)
        b = var(5)
        res = my_sum(a=a, b=b)
        self.assertIsInstance(res, Observable)
        self.assertEqual(ev(res), 7)

    def test_var_changes(self):
        a = var(2)
        b = var(5)
        res = my_sum(a=a, b=b)
        a @= 6
        self.assertEqual(ev(res), 11)  # 6+5
        b @= 3
        self.assertEqual(ev(res), 9)  # 6+3

    def test_exception_propagation(self):
        a = var(None)
        b = var()
        res = my_sum(a=a, b=b)
        self.assertIsNotNone(ev_exception(res))
        with self.assertRaises(EvError):
            ev(res)


# @reactive
# async def async_sum(a, b):
#     return a + b
#
#
# class SimpleReactiveAsync(asynctest.TestCase):
#     async def test_vals_positional(self):
#         self.assertEqual(await async_sum(2, 5), 7)
#
#     async def test_vals_keyword(self):
#         self.assertEqual(await async_sum(a=2, b=5), 7)
#
#     async def test_call_result_as_argument(self):
#         self.assertEqual(await async_sum(2, await async_sum(4, 1)), 7)
#
#     async def test_var_val_positional(self):
#         a = var(2)
#         res = await async_sum(a, 5)
#         self.assertIsInstance(res, Observable)
#         self.assertEqual(await aev(res), 7)
#
#     async def test_var_val_keyword(self):
#         a = var(2)
#         res = await async_sum(a=a, b=5)
#         self.assertIsInstance(res, Observable)
#         self.assertEqual(await aev(res), 7)
#
#     async def test_var_var(self):
#         a = var(2)
#         b = var(5)
#         res = await async_sum(a=a, b=b)
#         self.assertIsInstance(res, Observable)
#         self.assertEqual(await aev(res), 7)
#
#     async def test_var_changes(self):
#         a = var(2)
#         b = var(5)
#         res = await async_sum(a=a, b=b)
#         a @= 6
#         self.assertEqual(11, await aev(res))  # 6+5
#         b.__assign__(3)
#         self.assertEqual(9, await aev(res))  # 6+3
#
#     async def test_exception_propagation(self):
#         a = var(3)
#         b = var()
#         res = await async_sum(a=a, b=b)
#         self.assertIsNotNone(ev_exception(res))
#         with self.assertRaisesRegex(Exception, r'.*b.*'):
#             await aev(res)


class ReactiveWithYield(unittest.TestCase):

    def setUp(self):
        self.inside = 0  # how many "theads" are waiting in yield

    def tearDown(self):
        gc.collect()
        # await asyncio.sleep(0.01)
        self.assertEqual(self.inside, 0)

    @reactive
    def sum_with_yield(self, a, b):
        self.inside += 1
        # do work and return the result
        yield a + b
        # cleanup
        self.inside -= 1

    def test_returns_proper_value(self):
        pytest.skip("TODO")
        res = self.sum_with_yield(2, 5)
        # in this case we must return something that finalizes the function when destroyed
        self.assertIsInstance(res, Observable)
        self.assertEqual(ev(res), 7)

    def test_lost_reference_should_exit_from_yield(self):
        pytest.skip("TODO")

        res = self.sum_with_yield(2, 5)
        # in this case we must return something that finalizes the function when destroyed
        self.assertEqual(self.inside, 1)
        del res
        gc.collect()
        self.assertEqual(self.inside, 0)

    def test_finalize_should_exit_from_yield(self):
        pytest.skip("TODO")

        res = self.sum_with_yield(2, 5)
        # in this case we must return something that finalizes the function when destroyed
        self.assertEqual(self.inside, 1)
        res.__finalize__()
        self.assertEqual(self.inside, 0)

    def test_chainging_argument_should_exit_from_yield(self):
        b = var(5)
        res = self.sum_with_yield(2, b=b)
        self.assertIsInstance(res, Observable)
        self.assertEqual(ev(res), 7)
        self.assertEqual(self.inside, 1)
        b @= (1)
        self.assertEqual(ev(res), 3)
        self.assertEqual(self.inside, 1)  # one exited, one entered
        res.__finalize__()
        self.assertEqual(self.inside, 0)

    def test_exception_propagation(self):
        b = var()
        res = self.sum_with_yield(2, b=b)
        self.assertIsInstance(res, Observable)
        gc.collect()
        self.assertIsNotNone(ev_exception(res))
        self.assertEqual(0, self.inside)
        with self.assertRaises(EvError) as r:
            ev(res)
        b @= 5
        self.assertIsNone(ev_exception(res))
        self.assertEqual(7, ev(res))
        self.assertEqual(1, self.inside)


# @reactive_finalizable
# async def async_sum_with_yield(a, b):
#     global inside
#     inside += 1
#     yield a + b
#     # cleanup
#     inside -= 1
#
#
# class AsyncReactiveWithYield(asynctest.TestCase):
#     async def setUp(self):
#         gc.collect()
#         await asyncio.sleep(0.01)
#         self.assertEqual(inside, 0)
#
#     async def tearDown(self):
#         gc.collect()
#         await asyncio.sleep(0.01)
#         self.assertEqual(inside, 0)
#
#     async def test_a(self):
#         b = var(5)
#         res = await async_sum_with_yield(2, b=b)
#         self.assertIsInstance(res, Observable)
#         self.assertEqual(await aev(res), 7)
#         self.assertEqual(inside, 1)
#         b @= 1
#         self.assertEqual(await aev(res), 3)
#         self.assertEqual(inside, 1)
#         del res
#         await asyncio.sleep((0.1))
#
#     async def test_exception_propagation(self):
#         b = var()
#         res = await async_sum_with_yield(2, b=b)  # type: Observable
#         self.assertEqual(inside, 0)
#         self.assertIsNotNone(ev_exception(res))
#         with self.assertRaisesRegex(Exception, r'.*b.*'):
#             await aev(res)
#
#         b @= 5
#         # self.assertEqual(inside, 1)
#         # self.assertIsNone(res.exception)
#         # self.assertEqual(raw(res), 7)


# class Builtin(asynctest.TestCase):
#     async def test_vars(self):
#         a = var([1, 2])
#         l = reactive(len)(a)
#         self.assertEqual(unwrap(l), 2)
#
#         a @= [3]
#         await wait_for_var(l)
#         self.assertEqual(unwrap(l), 1)


# @reactive(args_fwd_none=['a', 'b'])
# def none_proof_sum(a, b):
#     return a + b
#
#
# class SimpleReactiveBypassed(asynctest.TestCase):
#     async def test_vals(self):
#         self.assertEqual(none_proof_sum(2, 5), 7)
#         self.assertIsNone(none_proof_sum(2, None))
#         self.assertIsNone(none_proof_sum(None, 5))
#
#     async def test_vars(self):
#         a = var(None)
#         b = var(None)
#         res = none_proof_sum(a, b)
#         await wait_for_var(res)
#         self.assertIsNone(raw(res))
#         b.set(2)
#         await wait_for_var(res)
#         self.assertIsNone(raw(res))
#         a.set(3)
#         await wait_for_var(res)
#         self.assertEqual(raw(res), 5)


class VolatileAndMock(unittest.TestCase):
    def setUp(self):
        self.a = var(0)
        self.mock = Mock()
        self.func = reactive(self.mock)

    def test_no_calls_without_volatile(self):
        res = self.func(self.a)
        self.mock.assert_not_called()
        assign(self.a, 10)
        self.mock.assert_not_called()

    def test_calls_with_volatile(self):
        res = self.func(self.a)
        assign(self.a, 10)
        self.mock.assert_not_called()
        resv = volatile(res)
        self.mock.assert_called_once()
        self.mock.reset_mock()

        assign(self.a, 20)
        self.mock.assert_called_once()


class OtherDeps(unittest.TestCase):
    def setUp(self):
        self.some_observable = var()

        self.mock = Mock()
        self.func = reactive(other_deps=[self.some_observable])(self.mock)

    def test_vars(self):
        a = var(None)
        resv = volatile(self.func(a))
        self.mock.assert_called_once_with(None)
        self.mock.reset_mock()

        a @= 55
        self.mock.assert_called_once_with(ValueAndTypeEq(55))
        self.mock.reset_mock()

        self.some_observable @= 10
        self.mock.assert_called_once_with(55)
        self.mock.reset_mock()

        self.some_observable.__notifier__().call()
        self.mock.assert_called_once_with(55)
        self.mock.reset_mock()


called_times = 0
some_observable = var()
some_observable2 = var()

called_times2 = 0


@reactive(dep_only_args=['ignored_arg'])
def inc_called_times2(a):
    global called_times2
    called_times2 += 1
    return a


class DepOnlyArgs(unittest.TestCase):
    def setUp(self):
        self.observable1 = var()
        self.observable2 = var()

        self.mock = Mock()
        self.func = reactive(dep_only_args=['ignored_arg'])(self.mock)

    def test_vars(self):
        a = var(55)
        res = volatile(self.func(a, ignored_arg=self.observable1))
        self.mock.assert_called_once_with(ValueAndTypeEq(55))

        self.mock.reset_mock()

        a @= 10
        self.mock.assert_called_once_with(ValueAndTypeEq(10))
        self.mock.reset_mock()

        self.observable1.__notifier__().notify()
        self.mock.assert_called_once_with(10)
        self.mock.reset_mock()

    def test_iterable(self):
        a = var(55)
        res = volatile(self.func(a, ignored_arg=[self.observable1, self.observable2]))
        self.mock.assert_called_once_with(ValueAndTypeEq(55))
        self.mock.reset_mock()

        self.observable1.__notifier__().notify()
        self.mock.assert_called_once_with(55)
        self.mock.reset_mock()

        self.observable2.__notifier__().notify()
        self.mock.assert_called_once_with(55)
        self.mock.reset_mock()


class DefaultArgs(unittest.TestCase):
    def setUp(self):
        self.mock = Mock()
        self.some_observable = var(3)

        @reactive
        def func_with_default(a, param_with_default=self.some_observable):
            self.mock(a, param_with_default)
            return a + param_with_default

        self.func = func_with_default

    def test_with_const_arg(self):
        res = self.func(5)
        self.assertIsInstance(res, Observable)
        resv = volatile(res)
        self.assertEqual(8, ev(res))
        self.mock.assert_called_once_with(ValueAndTypeEq(5), ValueAndTypeEq(3))
        self.mock.reset_mock()

        logging.info("setting observable to 100")
        self.some_observable @= 100
        self.mock.assert_called_once_with(5, 100)
        self.mock.reset_mock()

    def test_with_const_default_arg(self):
        res = self.func(5, param_with_default=6)
        self.assertIsInstance(res, int)
        self.mock.assert_called_once_with(5, 6)
        self.mock.reset_mock()


@reactive(pass_args=['a'])
def pass_args(a, b):
    global called_times2
    called_times2 += 1
    return ev(a) + b


class PassArgs(unittest.TestCase):
    def setUp(self):
        self.mock = Mock()
        self.func = reactive(pass_args=['a'])(self.mock)

    def test_1(self):
        global some_observable
        a = var(5)
        b = var(3)
        res = pass_args(a, b)
        self.assertIsInstance(res, Observable)
        self.assertEqual(8, ev(res))
        self.assertEqual(1, called_times2)
        a @= 10
        self.assertEqual(8, ev(res))
        self.assertEqual(1, called_times2)
        b @= 100
        self.assertEqual(110, ev(res))
        self.assertEqual(2, called_times2)
