import abc
import logging
import weakref
from _weakrefset import WeakSet
from typing import Any, Callable, Coroutine, Optional, Set, TypeVar, Union, cast

from stateflow.common import NotifyFunc
from stateflow.sync_refresher import get_default_refresher

logger = logging.getLogger('notify')

all_notifiers: WeakSet = WeakSet()

_got_finals = 0


def is_hashable(v: Any) -> bool:
    """Determine whether `v` can be hashed."""
    try:
        hash(v)
    except TypeError:
        return False
    return True


def is_notify_func(notify_func: Any) -> bool:
    return is_hashable(notify_func) and hasattr(notify_func, '__call__')


class INotifier(abc.ABC):
    """
    A node in a graph that notifications (about changes) are propagated.

    A notifier observes other notifiers. It means, that if one of the observed notifiers is "notifier", the current one
    will also be notified soon (unless it is "inactive"). Physically, the notifications are called by `Refresher`.

    A notifier can be "active" or "inactive". Inactive notifiers are ignored by the refresher. Notifier is active if
    it has at least one active observer.

    A notifier has a priority, which is used to determine the order of notifications. The priority is an integer, where
    lower numbers are called first. The priority of the notifier is always greater than the priority of all its observers.
    """
    name: str = ""

    @abc.abstractmethod
    def notify(self) -> None:
        
        """Notify the notifier that the related object should be updated (and all dependents). """
        ...

    # FIXME rename to "call_update"?
    @abc.abstractmethod
    def call(self) -> bool:
        """Call the update callback in the related object and notify active dependents."""
        ...

    @property
    @abc.abstractmethod
    def priority(self) -> int:
        """Return the priority of the notifier."""
        ...

    @property
    @abc.abstractmethod
    def active(self) -> bool:
        """Return whether the notifier is active (i.e. it has active observers)."""
        ...

    @abc.abstractmethod
    def add_observer(self, observer: 'INotifier') -> None:
        """Add an observer to this notifier. It fill be notified when this notifier is called"""
        ...

    @abc.abstractmethod
    def remove_observer(self, observer: 'INotifier') -> None:
        """Remove an observer from this notifier. It will not be notified anymore."""
        ...

    def refresh(self) -> None:
        refresh_notifiers(self)

class DummyNotifier(INotifier):
    def __init__(self, priority: int) -> None:
        self._priority = priority
        self.name = 'dummy'

    def notify(self) -> None:
        pass

    def call(self) -> bool:
        return False

    @property
    def priority(self) -> int:
        return self._priority

    @property
    def active(self) -> bool:
        return False

    def add_observer(self, observer: INotifier) -> None:
        return

    def remove_observer(self, observer: INotifier) -> None:
        return

    def refresh(self) -> None:
        return



class Notifier(INotifier):


    def __init__(self, notify_func: NotifyFunc = lambda: True, forced_active: bool = False, name: str = "") -> None:
        """
        Arguments:
            notify_func: A function that will be called when one of the observed notifiers is changed.
            forced_active: If True, this notifier is always active, even if there are no active observers.
        """
        self._observers: Set['Notifier'] = weakref.WeakSet()
        self._active_observers: Set['Notifier'] = weakref.WeakSet()
        self._observed: Set['Notifier'] = weakref.WeakSet()

        self._priority = 0  # lowest called first; should be greater than all observed

        self._forced_active = forced_active
        self._is_active = forced_active  # notifier is active iif at least one of its observers is active or _forced_active

        self._called_when_inactive = False

        self.name = name
        assert is_notify_func(notify_func)
        self.notify_func = notify_func
        self.calls = 0
        self.stats: dict[str, Any] = dict()
        self.frame = None
        all_notifiers.add(self)

    def notify(self) -> None:
        logger.debug(f"Notifier notified: {self}")
        get_default_refresher().schedule_call(self)

    def call(self) -> None:
        logger.debug(f"Notifier called: {self}")
        self.calls += 1
        if self.active:
            possibly_changed = self.notify_func()
            if possibly_changed:
                self._notify_observers()
        else:
            self._called_when_inactive = True

    def _notify_observers(self):
        for observer in self._observers:  # fixme: shouldn't we use _active_observers here?
            observer.notify()

    def add_observer(self, observer: 'Notifier') -> None:
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

    def _add_to_active(self, observer: 'Notifier') -> None:
        self._active_observers.add(observer)
        self._update_active()

    def remove_observer(self, observer: 'Notifier') -> None:
        assert observer in self._observers
        self._observers.remove(observer)
        observer._observed.remove(self)
        if observer in self._active_observers:
            self._remove_from_active(observer)

    def _remove_from_active(self, observer: 'Notifier') -> None:
        self._active_observers.remove(observer)
        self._update_active()

    def _update_active(self) -> None:
        """
        My active state might have changed, so I may need to readd myself to observed notifiers (or they wouldn't know
        someone active is observing them)
        """
        new_is_active = (len(self._active_observers) > 0 or self._forced_active)
        if new_is_active != self._is_active:
            self._is_active = new_is_active
            for observed in self._observed:
                if self._is_active:
                    observed._add_to_active(self)
                else:
                    observed._remove_from_active(self)
            if self._is_active and self._called_when_inactive:
                self._called_when_inactive = False
                self.notify()

    @property
    def priority(self) -> int:
        return self._priority

    @property
    def active(self) -> bool:
        # self._update_active()
        return self._is_active

    def _set_priority_at_least(self, min_priority: int) -> None:
        if self._priority < min_priority:
            self._priority = min_priority
            for observer in self._observers:
                observer._set_priority_at_least(min_priority + 1)

    def __repr__(self) -> str:
        return f"<Notifier name={self.name} id={id(self):x} priority={self.priority} active={self.active}>"



ACTIVE_NOTIFIER = Notifier(forced_active=True, name="ACTIVE")


def refresh_notifiers(*notifiers: Notifier) -> None:
    """
    Activates notifier for a moment, so if there is a call pending somewhere in (possibly indirectly) observed notifiers
    whole chain is called.
    """
    assert ACTIVE_NOTIFIER not in notifiers
    inactive_notifiers = [notifier for notifier in notifiers if not notifier.active]
    for notifier in inactive_notifiers:
        notifier.add_observer(ACTIVE_NOTIFIER)
    for notifier in inactive_notifiers:
        notifier.remove_observer(ACTIVE_NOTIFIER)

def dump_notifiers_to_dot(notifier: INotifier, filename: str = 'notifiers.dot') -> None:
    """
    Dumps the notifier graph to a dot file.
    """
    import pydot

    graph = pydot.Dot(graph_type='digraph')

    def add_node(n: INotifier) -> Any:
        node = pydot.Node(str(id(n)), label=n.name, shape='box', style="dashed" if not n.active else "solid")
        graph.add_node(node)
        return node

    def add_edge(from_node: Any, to_node: Any) -> None:
        edge = pydot.Edge(from_node, to_node)
        graph.add_edge(edge)

    nodes: dict[INotifier, Any] = {}
    def traverse(n: INotifier) -> None:
        if n in nodes:
            return
        nodes[n] = add_node(n)
        if isinstance(n, Notifier):
            for another_n in n._observers:
                traverse(another_n)
                add_edge(nodes[another_n], nodes[n])
            for another_n in list(n._observers) + list(n._observed):
                traverse(another_n)

    traverse(notifier)
    graph.write(filename, format='dot')
# class ActiveNotifier:
#     def __init__(self, notifier: Notifier):
#         self._notifier = notifier
#         self._active_notifier = Notifier(forced_active=True)
#
#     def __enter__(self):
#         self._notifier.add_observer(self._active_notifier)
#
#     def __exit__(self, exc_type, exc_val, exc_tb):
#         self._notifier.remove_observer(self._active_notifier)
