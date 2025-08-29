import logging
import weakref
from _weakrefset import WeakSet
from typing import Any, Set

from stateflow.common import INotifier, NotifyFunc
from stateflow.sync_refresher import get_default_refresher

logger = logging.getLogger('notify')

all_notifiers: WeakSet[Any] = WeakSet()

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


class DummyNotifier(INotifier):
    def __init__(self, priority: int) -> None:
        self._priority = priority
        self.name = 'dummy'

    def notify(self) -> None:
        pass

    def propagate(self) -> None:
        pass

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

        self._priority = 0

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

    def propagate(self) -> None:
        logger.debug(f"Notifier called: {self}")
        self.calls += 1
        if self.active:
            possibly_changed = self.notify_func()
            if possibly_changed:
                self._notify_observers()
        else:
            self._called_when_inactive = True

    def _notify_observers(self) -> None:
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

    def refresh(self) -> None:
        refresh_notifiers(self)


ACTIVE_NOTIFIER = Notifier(forced_active=True, name="ACTIVE")


def refresh_notifiers(*notifiers: INotifier) -> None:
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
