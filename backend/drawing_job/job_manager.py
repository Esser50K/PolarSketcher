import uuid
import time
from typing import Union, Tuple, List
from threading import Thread, Event
from drawing_job.consumer_models import Consumer, ConsumerPoint
from drawing_job.polar_sketcher_consumer import PolarSketcherConsumer
from drawing_job.ws_broadcast_consumer import WSBroadcastConsumer
from geventwebsocket.websocket import WebSocket
from path_generator import PathGenerator
from polar_sketcher_interface import PolarSketcherInterface, Mode


def gen_intermediate_points(start_point, end_point, points_per_unit=.1):
    start_x, start_y = start_point
    end_x, end_y = end_point

    # Calculate the distance between the start and end points
    distance = (((end_x - start_x) ** 2) + ((end_y - start_y) ** 2)) ** 0.5
    if distance == 0:
        yield end_point
        return

    # Calculate the number of points to generate
    num_points = int(distance * points_per_unit)

    if num_points == 0:
        return

    # Generate intermediate points with uniform spacing
    for i in range(num_points + 1):
        ratio = i / num_points
        x = start_x + (end_x - start_x) * ratio
        y = start_y + (end_y - start_y) * ratio
        yield int(x), int(y)


class DrawingJobWebConnection:
    def __init__(self, ws: WebSocket, event: Event):
        self.unique_origin = ws.origin + str(uuid.uuid4())
        self.ws = ws
        self.event = event

    def close(self):
        try:
            self.event.set()
            self.ws.close()
        except Exception as e:
            print("failed closing ws from %s:" %
                  self.unique_origin, type(e), e)
            self.event.set()


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


class DrawingJobManager:
    def __init__(self):
        self.current_job: DrawingJob = None
        self._ws_broadcast_consumer = None
        self._polar_sketcher_interface = None
        self._polar_sketcher_consumer = None

    def stop(self):
        if self.current_job:
            self.current_job.stop()
            self.current_job = None

    def get_job(self) -> DrawingJob:
        return self.current_job

    def add_ws_client(self, ws: WebSocket) -> Event:
        return self._ws_broadcast_consumer.add_ws_client(ws)

    def start_drawing_job(self, path_generator: PathGenerator, dryrun=False):
        job_id = uuid.uuid4()

        consumers = []
        if not dryrun:
            self._polar_sketcher_interface = PolarSketcherInterface()
            self._polar_sketcher_consumer = PolarSketcherConsumer(
                self._polar_sketcher_interface)
            consumers.append(self._polar_sketcher_consumer)

        self._ws_broadcast_consumer = WSBroadcastConsumer()
        consumers.append(self._ws_broadcast_consumer)

        self.current_job = DrawingJob(
            job_id, path_generator, consumers)
        self.current_job.start()
        return str(job_id)
