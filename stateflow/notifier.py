import logging
import weakref
from _weakrefset import WeakSet
from contextlib import contextmanager
from typing import Set

from stateflow.common import NotifyFunc

logger = logging.getLogger('notify')


def is_hashable(v):
    """Determine whether `v` can be hashed."""
    try:
        hash(v)
    except TypeError:
        return False
    return True


def is_notify_func(notify_func):
    return is_hashable(notify_func) and hasattr(notify_func, '__call__')


class DummyNotifier:
    def __init__(self, priority):
        self.priority = priority
        self.name = 'dummy'

    def add_observer(self, notifier: 'Notifier'):
        pass

    def remove_observer(self, notifier: 'Notifier'):
        pass

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def notify(self):
        pass


all_notifiers = WeakSet()

_got_finals = 0


class ScopedName:
    names = []

    def __init__(self, name, final=False):
        """
        :param name:
        :param final: Don't chain with ScopedName()s already on the stack
        """
        self.name = name
        self.final = final

    def __enter__(self):
        global _got_finals
        if self.name is not None and _got_finals == 0:
            self.names.append(self.name)
        if self.final:
            _got_finals += 1

    def __exit__(self, exc_type, exc_val, exc_tb):
        global _got_finals
        if self.final:
            _got_finals -= 1
        if self.name is not None and _got_finals == 0:
            res = self.names.pop()
            assert res == self.name


class Notifier:
    def __init__(self, notify_func: NotifyFunc = lambda: True):
        self._observers = weakref.WeakSet()  # type: Set[Notifier]
        self.name = '/'.join(ScopedName.names)
        assert is_notify_func(notify_func)
        self.notify_func = notify_func
        self.calls = 0
        self.stats = dict()
        self.frame = None
        all_notifiers.add(self)
        self.pending_updates = 0
        self.possibly_changed = False
        self.recursion_in_progress = False
        #  lowest called first; should be greater than all observed

    def notify(self):
        self.begin_update()
        self.finish_update(True)

    def add_observer(self, observer: 'Notifier'):
        self._observers.add(observer)
        if self.pending_updates > 0:
            observer.begin_update()

    def remove_observer(self, observer: 'Notifier'):
        self._observers.remove(observer)
        if self.pending_updates > 0:
            observer.begin_update()

    def _observer_begin_update(self, observer):
        assert self.recursion_in_progress == False
        self.recursion_in_progress = True
        try:
            observer.begin_update()
        except Exception as e:
            logging.exception('ignoring exception in finish_update')
        finally:
            self.recursion_in_progress = False

    def begin_update(self):
        if self.recursion_in_progress:
            return  # handle circular dependencies
        self.pending_updates += 1
        if self.pending_updates == 1:
            self.possibly_changed = False
            observers = self._observers  # it may change during the following calls
            for observer in observers:
                self._observer_begin_update(observer)

    def _observer_finish_update(self, observer, possibly_changed):
        assert self.recursion_in_progress == False
        self.recursion_in_progress = True
        try:
            observer.finish_update(possibly_changed)
        except Exception as e:
            logging.exception('ignoring exception in finish_update')
        finally:
            self.recursion_in_progress = False

    def finish_update(self, possibly_changed):
        if self.recursion_in_progress:
            return  # handle circular dependencies
        assert self.pending_updates > 0
        self.possibly_changed = self.possibly_changed or possibly_changed
        if self.pending_updates == 1:
            try:
                if self.possibly_changed:
                    self.notify_func()
            except Exception as e:
                logging.exception('ignoring exception in finish_update')
            observers = self._observers  # it may change during the following calls
            for observer in observers:
                self._observer_finish_update(observer, possibly_changed)

        self.pending_updates -= 1

    def __enter__(self):
        self.begin_update()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.finish_update(True)


@contextmanager
def many_notifiers(*notifiers):
    for notifier in notifiers:
        notifier.begin_update()

    try:
        yield
    finally:
        for notifier in reversed(notifiers):
            notifier.finish_update(True)
