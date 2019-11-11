import logging
import weakref
from _weakrefset import WeakSet
from typing import Set

from stateflow.common import NotifyFunc
from stateflow.sync_refresher import get_default_refresher

logger = logging.getLogger('notify')

all_notifiers = WeakSet()

_got_finals = 0


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

    def notify_observers(self):
        pass


class Notifier:
    def __init__(self, notify_func: NotifyFunc = lambda: True, forced_active=False):
        self._observers = weakref.WeakSet()  # type: Set[Notifier]
        self._active_observers = weakref.WeakSet()  # type: Set[Notifier]
        self._observed = weakref.WeakSet()  # type: Set[Notifier]

        self._priority = 0  # lowest called first; should be greater than all observed

        self._forced_active = forced_active
        self._is_active = forced_active  # notifier is active iif at least one of it's observers is active or _forced_active

        self._called_when_inactive = False

        self.name = "FIXME"
        assert is_notify_func(notify_func)
        self.notify_func = notify_func
        self.calls = 0
        self.stats = dict()
        self.frame = None
        all_notifiers.add(self)

    def notify(self):
        get_default_refresher().schedule_call(self)

    def call(self):
        self.calls += 1
        if self.active:
            possibly_changed = self.notify_func()
            if possibly_changed:
                self._notify_observers()
        else:
            self._called_when_inactive = True

    def _notify_observers(self):
        for observer in self._observers:
            observer.notify()

    def add_observer(self, observer: 'Notifier'):
        """
        :param observer: A notifier that will be notified (WARNING! it must be owned somewhere else; it's especially
                       important for bound methods or partially bound functions). It must be hashable and equality
                       comparable. If there are more than one calls to the same notifier pending, they are reduced to
                       one only. It will take part in the topological sort when obtaining an order of
                       notifications. It's priority will be enforced to be greater than the priority of this object.
        """
        observer._set_priority_at_least(self.priority + 1)
        self._observers.add(observer)
        observer._observed.add(self)
        if observer.active:
            self._add_to_active(observer)

    def _add_to_active(self, observer):
        self._active_observers.add(observer)
        self._update_active()

    def remove_observer(self, observer: 'Notifier'):
        assert observer in self._observers
        self._observers.remove(observer)
        observer._observed.remove(self)
        if observer in self._active_observers:
            self._remove_from_active(observer)

    def _remove_from_active(self, observer):
        self._active_observers.remove(observer)
        self._update_active()

    def _update_active(self):
        if (len(self._active_observers) > 0 or self._forced_active) != self._is_active:
            self._is_active = len(self._active_observers) > 0
            for observed in self._observed:
                if self._is_active:
                    observed._add_to_active(self)
                else:
                    observed._remove_from_active(self)
            if self._is_active and self._called_when_inactive:
                self._called_when_inactive = False
                self.notify()

    @property
    def priority(self):
        return self._priority

    @property
    def active(self):
        # self._update_active()
        return self._is_active

    def _set_priority_at_least(self, min_priority):
        if self._priority < min_priority:
            self._priority = min_priority
            for observer in self._observers:
                observer._set_priority_at_least(min_priority + 1)


