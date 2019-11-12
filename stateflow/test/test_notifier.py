import unittest
from unittest.mock import Mock

from stateflow import Notifier
from stateflow.notifier import ACTIVE_NOTIFIER
from stateflow.sync_refresher import UpdateTransaction


class NotifierTests(unittest.TestCase):
    def setUp(self):
        self.cbk = Mock(return_value=True)
        self._notifier = Notifier(self.cbk)

    def test_calls_callback_when_active(self):
        self._notifier.add_observer(ACTIVE_NOTIFIER)
        self._notifier.notify()
        self.cbk.assert_called_once()

    def test_calls_callback_once_per_transaction(self):
        self._notifier.add_observer(ACTIVE_NOTIFIER)
        with UpdateTransaction():
            self._notifier.notify()
            self._notifier.notify()
        self.cbk.assert_called_once()
        self.cbk.reset_mock()

        with UpdateTransaction():
            self._notifier.notify()
        self.cbk.assert_called_once()

    def test_dont_call_callback_when_not_active(self):
        self._notifier.notify()
        self.cbk.assert_not_called()

    def test_activeness_may_change(self):
        self._notifier.add_observer(ACTIVE_NOTIFIER)
        self._notifier.remove_observer(ACTIVE_NOTIFIER)
        self._notifier.notify()
        self.cbk.assert_not_called()

        self._notifier.add_observer(ACTIVE_NOTIFIER)
        self.cbk.assert_called_once()  # called since was dirty whan activated
        self.cbk.reset_mock()

        self._notifier.notify()
        self.cbk.assert_called_once()  #
        self.cbk.reset_mock()


class TwoNotifiersTests(unittest.TestCase):
    def setUp(self):
        """
        notifier2 observes notifier1
        """
        self.cbk1 = Mock(return_value=True)
        self.cbk2 = Mock(return_value=True)
        self._notifier1 = Notifier(self.cbk1)
        self._notifier2 = Notifier(self.cbk2)
        self._notifier1.add_observer(self._notifier2)

    def test_observer_has_greater_priority_number(self):
        self.assertGreater(self._notifier2.priority, self._notifier1.priority)

    def test_dont_call_callback_when_not_active(self):
        self._notifier1.notify()
        self.cbk1.assert_not_called()
        self.cbk2.assert_not_called()

    def test_both_called_if_second_active(self):
        self._notifier2.add_observer(ACTIVE_NOTIFIER)
        self._notifier1.notify()
        self.cbk1.assert_called_once()
        self.cbk2.assert_called_once()
        self.cbk1.reset_mock()
        self.cbk2.reset_mock()

        self._notifier2.remove_observer(ACTIVE_NOTIFIER)
        self._notifier1.notify()
        self.cbk1.assert_not_called()
        self.cbk2.assert_not_called()

    def test_first_called_if_first_active(self):
        self._notifier1.add_observer(ACTIVE_NOTIFIER)
        self._notifier1.notify()
        self.cbk1.assert_called_once()
        self.cbk2.assert_not_called()

    def test_second_not_called_if_first_returned_false(self):
        self._notifier2.add_observer(ACTIVE_NOTIFIER)
        self.cbk1.return_value = False
        self._notifier1.notify()
        self.cbk1.assert_called_once()
        self.cbk2.assert_not_called()
