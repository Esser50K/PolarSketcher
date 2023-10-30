import time
from typing import Union, Tuple, List
from threading import Thread
from drawing_job.consumer_models import Consumer, ConsumerPoint
from path_generator import PathGenerator


class DrawingJob:
    def __init__(self, job_id, path_generator: PathGenerator, consumers: List[Consumer]):
        self.job_id = job_id
        self.path_generator = path_generator
        self.consumers = consumers

        self.worker = Thread(target=self.run)
        self._stop = False

    def start(self):
        self.worker.start()

    def _init_consumers(self):
        for consumer in self.consumers:
            consumer.init()

    def _shutdown_consumers(self):
        for consumer in self.consumers:
            consumer.shutdown()

    def _broadcast_to_consumers(self, point: Union[Tuple, str]):
        consumer_point = ConsumerPoint(point, self.path_generator.canvas_size)
        for consumer in self.consumers:
            consumer.consume(consumer_point)

    def run(self):
        # give a chance for the main thread to return the job_id to the frontend
        time.sleep(.05)
        self._init_consumers()
        for point in self.path_generator.generate_points():
            if self._stop:
                break

            self._broadcast_to_consumers(point)

        self._shutdown_consumers()

    def stop(self, wait=True):
        self._stop = True
        if wait and self.worker.is_alive():
            self.worker.join()
