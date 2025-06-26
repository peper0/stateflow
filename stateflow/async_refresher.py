import asyncio
import gc
import logging
from contextlib import suppress
from typing import Any, Awaitable, Dict, NamedTuple, Optional, Set, TYPE_CHECKING, Union

import sys

logger = logging.getLogger('refresher')

if TYPE_CHECKING:
    from stateflow.notifier import Notifier


class QueueItem(NamedTuple):
    priority: int  # lower priority is called first
    id: Any  # FIXME: remove id (callable MUST be hashable, we use wrapper if it isn't)
    notifier: 'Notifier'
    stats: Dict[str, Any]

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, QueueItem):
            return self.priority < other.priority
        return NotImplemented


class AsyncRefresher:
    def __init__(self) -> None:
        self.queue: asyncio.PriorityQueue[QueueItem] = asyncio.PriorityQueue()
        self.task: Optional[asyncio.Task[None]] = None

    def maybe_start_task(self) -> None:
        if not self.task or self.task.done():
            self.task = asyncio.ensure_future(self.run())
            self.task.add_done_callback(self._handle_done)

    @staticmethod
    def _handle_done(f: asyncio.Future[Any]) -> None:
        if f.cancelled():
            logger.warning('refresh task was cancelled')
            return
        e = f.exception()
        if e:
            logger.exception('refresh task finished with exception, rethrowing')
            raise e

    def schedule_call(self, notifier: 'Notifier') -> None:
        logger.debug('  scheduled notification ({}) [{:X}] {}'.format(notifier.priority, id(notifier), notifier.name))
        t = QueueItem(notifier.priority, notifier, notifier, notifier.stats)
        self.queue.put_nowait(t)
        self.maybe_start_task()

    async def run(self) -> None:
        gc.collect()
        update_next: Optional[QueueItem] = None

        notified_notifiers: Set['Notifier'] = set()
        with suppress(asyncio.QueueEmpty):  # it's ok - if the queue is empty we just exit
            while True:
                notification = update_next if update_next else self.queue.get_nowait()  # type: QueueItem
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
                    # if asyncio.iscoroutine(res):
                    #     res = await res
                    notification.stats['exception'] = None

                    # if res:
                    #     logger.debug(' notification finished with True, notifying observers')
                    #     notifier._notify_observers()  # Use the internal method instead of a non-existent method
                    #     logger.debug(' finished')
                    # else:
                    #     logger.debug(' notification finished with False')

                except Exception as e:
                    logger.exception('ignoring exception when in notifying observer {}'.format(notification.notifier))
                    notification.stats['exception'] = e
        gc.collect()


refresher: Optional[AsyncRefresher] = None


def get_default_refresher() -> AsyncRefresher:
    global refresher
    if not refresher:
        refresher = AsyncRefresher()

    return refresher


async def wait_for_var(var: Optional[Any] = None) -> None:
    # fixme: waiting only for certain level (if var is not None)
    task = get_default_refresher().task
    if task:
        await task
