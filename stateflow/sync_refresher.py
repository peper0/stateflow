import asyncio
import gc
import logging
import sys
from contextlib import suppress
from typing import Any, NamedTuple

#FIXME: remove this logging configuration
# stderr_logger_handler = logging.StreamHandler(stream=sys.stderr)
# stderr_logger_handler.setLevel(logging.DEBUG)
logger = logging.getLogger('refresher')
# logger.addHandler(stderr_logger_handler)
# logger.setLevel(logging.INFO)


class QueueItem(NamedTuple):
    priority: int
    id: Any  # FIXME: remove id (callable MUST be hashable, we use wrapper if it isn't)
    notifier: 'Notifier'
    stats: dict

    def __lt__(self, other):
        return self.priority < other.priority


class SyncRefresher:
    def __init__(self):
        self.queue = asyncio.PriorityQueue()
        self._updates_in_progress = 0

    def schedule_call(self, notifier: 'Notifier'):
        logger.debug('  scheduled notification ({}) [{:X}] {}'.format(notifier.priority, id(notifier), notifier.name))
        t = QueueItem(notifier.priority, notifier, notifier, notifier.stats)
        self.queue.put_nowait(t)
        self.maybe_run()

    def force_run(self, max_priority=None):
        gc.collect()
        update_next = None

        notified_notifiers = set()
        with suppress(asyncio.QueueEmpty):  # it's ok - if the queue is empty we just exit
            while True:
                notification = update_next if update_next else self.queue.get_nowait()  # type: QueueItem
                if max_priority is not None and notification.priority > max_priority:
                    self.queue.put_nowait(notification)
                    break
                try:
                    update_next = self.queue.get_nowait()
                    if update_next.id == notification.id:  # skip notification if is same as next
                        continue
                except asyncio.QueueEmpty:
                    update_next = None

                try:
                    notification.stats['calls'] = notification.stats.get('calls', 0) + 1
                    notifier = notification.notifier
                    if notifier in notified_notifiers:
                        logger.debug('notifier [{:X}] {} called more than once'.format(id(notifier), notifier.name))
                    notified_notifiers.add(notifier)
                    logger.debug('call notification ({}) [{:X}] {}'.format(notifier.priority, id(notifier),
                                                                           notifier.name))

                    notifier.call()
                    notification.stats['exception'] = None

                except Exception as e:
                    logger.exception('ignoring exception when in notifying observer {}'.format(notification.notifier))
                    notification.stats['exception'] = e
        gc.collect()

    def maybe_run(self):
        """
        Run if there are no updates in progress
        """
        if self._updates_in_progress == 0:
            self.force_run()


refresher = None


def get_default_refresher():
    global refresher
    if not refresher:
        refresher = SyncRefresher()

    return refresher


def wait_for_var(var=None):
    get_default_refresher().force_run(max_priority=var.__notifier__().priority if var is not None else None)


class UpdateTransaction:
    def __enter__(self):
        get_default_refresher()._updates_in_progress += 1

    def __exit__(self, exc_type, exc_val, exc_tb):
        get_default_refresher()._updates_in_progress -= 1
        get_default_refresher().maybe_run()
