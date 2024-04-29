from enum import Enum
from queue import Queue, Empty
from typing import TypeVar, Generic, Any

from ibind.support.py_utils import ensure_list_arg, OneOrMany

T = TypeVar("T", str, Enum)


class QueueAccessor(Generic[T]):  # pragma: no cover
    """
    Provides access to a queue with an associated key.

    This class encapsulates a queue and provides methods to interact with it, such as retrieving items
    and checking if the queue is empty. It is generic and can be associated with a key of any type.

    Constructor Parameters:
        queue (Queue): The queue to be accessed.
        key (T): The key associated with this queue accessor.
    """

    def __init__(self, queue: Queue, key: T):
        self.__queue__ = queue
        self._key = key

    def get(self, block: bool = False, timeout=None) -> Any:
        """
        Attempts to retrieve an item from the queue.

        This method tries to get an item from the queue. If the queue is empty and 'block' is False,
        it immediately returns None. Otherwise, it blocks until an item is available or until the
        timeout (if provided in 'kwargs') elapses.

        Parameters:
            block (bool, optional): Whether to block if the queue is empty. Defaults to False.
            timeout (Optional[float]): The maximum time in seconds to block waiting for an item.
                                       A value of None indicates an indefinite wait. Only effective if 'block' is True.


        Returns:
            The item retrieved from the queue, or None if the queue is empty and 'block' is False.
        """
        try:
            return self.__queue__.get(block=block, timeout=timeout)
        except Empty:
            return None

    def empty(self) -> bool:
        """
         Checks if the queue is empty.

         Returns:
             bool: True if the queue is empty, False otherwise.
         """
        return self.__queue__.empty()

    @property
    def key(self) -> T:
        return self._key

    def __str__(self):
        return f'QueueAccessor(key={self._key}, size={self.__queue__.qsize()})'


class QueueController(Generic[T]):
    """
    A generic controller class for managing multiple queues, each identified by a unique key.

    This class is generic and can work with any type of key (T). It allows the creation and management
    of multiple queues, each associated with a unique key of type T. The class provides methods to
    register new queues, retrieve existing queues, and add data to queues based on their keys.

    Example Usage:
      - Using strings as keys:
        queue_controller = QueueController[str]()
        queue_controller.register_queues(['queue1', 'queue2'])
        queue_controller.put_to_queue('queue1', data)

      - Using integers as keys:
        queue_controller = QueueController[int]()
        queue_controller.register_queues([1, 2])
        queue_controller.put_to_queue(1, data)
    """

    def __init__(self):
        self._queues = {}

    @ensure_list_arg('keys')
    def register_queues(self, keys: OneOrMany[T]):
        """
        Registers new queues associated with the given keys.

        This method creates new queues for each provided key that does not already have an associated queue.

        Parameters:
            keys (List[T]): A list of keys for which queues need to be registered.
        """
        for key in keys:
            if key not in self._queues:
                self._queues[key] = Queue()

    def new_queue_accessor(self, key: T) -> QueueAccessor:
        """
        Creates a QueueAccessor for a specific queue based on the provided key.

        Parameters:
            key (T): The key associated with the queue for which the QueueAccessor is to be created.

        Returns:
            QueueAccessor: An accessor for the queue associated with the given key.

        Raises:
            AttributeError: If no queue exists for the given key.
        """
        return QueueAccessor(self.get_queue(key), key)

    def get_queue(self, key: T) -> Queue:  # pragma: no cover
        """
        Retrieves the queue associated with the given key.

        Parameters:
            key (T): The key for which the queue is to be retrieved.

        Returns:
            Queue: The queue associated with the given key.

        Raises:
            AttributeError: If no queue exists for the given key.
        """
        try:
            return self._queues[key]
        except KeyError:
            raise AttributeError(f'Invalid queue key: "{key}", expected: {list(self._queues.keys())}')

    def put_to_queue(self, key: T, data):
        """
        Puts data into the queue associated with the specified key.

        This method retrieves the queue for the given key and adds the provided data to it.

        Parameters:
            key (T): The key of the queue into which the data is to be put.
            data: The data to be added to the queue.

        Raises:
            AttributeError: If no queue exists for the given key.
        """
        queue = self.get_queue(key)
        queue.put(data)
