from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple, Union


@dataclass
class ConsumerPoint:
    def __init__(self, point: Union[Tuple, str], canvas_size: Tuple):
        self.point = point
        self.canvas_size = canvas_size


class Consumer(ABC):
    @abstractmethod
    def init(self):
        pass

    @abstractmethod
    def shutdown(self):
        pass

    @abstractmethod
    def consume(self, point: ConsumerPoint):
        pass
