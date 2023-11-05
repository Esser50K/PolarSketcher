import uuid
from threading import Event
from drawing_job.polar_sketcher_consumer import PolarSketcherConsumer
from drawing_job.ws_broadcast_consumer import WSBroadcastConsumer
from geventwebsocket.websocket import WebSocket
from path_generator import PathGenerator
from polar_sketcher_interface import PolarSketcherInterface
from drawing_job.drawing_job import DrawingJob


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

    def start_drawing_job(self, path_generator: PathGenerator, dryrun=False, angle_correction=True):
        job_id = uuid.uuid4()

        consumers = []
        if not dryrun:
            self._polar_sketcher_interface = PolarSketcherInterface(
                angle_correction=angle_correction)
            self._polar_sketcher_consumer = PolarSketcherConsumer(
                self._polar_sketcher_interface)
            consumers.append(self._polar_sketcher_consumer)

        self._ws_broadcast_consumer = WSBroadcastConsumer()
        consumers.append(self._ws_broadcast_consumer)

        self.current_job = DrawingJob(
            job_id, path_generator, consumers)
        self.current_job.start()
        return str(job_id)
