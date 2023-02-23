import json
import uuid
import time
from queue import Queue, Empty, Full
from threading import Thread, Event
from typing import Union, List

from geventwebsocket.websocket import WebSocket
from svgpathtools import Path

import svg_parse_utils
from sort_paths import SORTING_ALGORITHMS, sort_paths
from toolpath_generation.algorithm_getter import get_toolpath_algo

from path_generator import PathGenerator, PATH_END_COMMAND, DRAWING_END_COMMAND
from polar_sketcher_interface import PolarSketcherInterface, Status, Mode, Command


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
            print("failed closing ws from %s:" % self.unique_origin, type(e), e)
            self.event.set()


class DrawingJob:
    def __init__(self, job_id, path_generator: PathGenerator, polar_sketcher: PolarSketcherInterface):
        self.job_id = job_id
        self.path_generator = path_generator
        self.polar_sketcher = polar_sketcher

        self.drawn_paths = []
        self.current_path = []
        self.connected_ws: dict[str, DrawingJobWebConnection] = {}
        self.worker = Thread(target=self.run)
        self._stop = False

    def start(self):
        if self.polar_sketcher is not None:
            self.polar_sketcher.set_mode(Mode.HOME)
            self.polar_sketcher.wait_for_idle()
            status = self.polar_sketcher.calibrate()
            status = self.polar_sketcher.calibrate()
            status = self.polar_sketcher.calibrate()
            status = self.polar_sketcher.calibrate()
            print(status)
            self.polar_sketcher.set_mode(Mode.DRAW)
        self.worker.start()


    def add_web_connection(self, ws: WebSocket, event: Event):
        webconn = DrawingJobWebConnection(ws, event)
        self.connected_ws[webconn.unique_origin] = webconn
        webconn.ws.send(json.dumps({
            "type": "update",
            "payload": self.drawn_paths
        }))

    def run(self):
        first_point = (0, 0)
        previous_point = (0, 0)
        for point in self.path_generator.generate_points():
            if self._stop:
                break

            if point == PATH_END_COMMAND:
                self.drawn_paths.append(self.current_path)
                self.current_path = []

                if self.polar_sketcher is not None:
                    # Sending same position twice, one with pen down and the next with pen up
                    amplitude_pos, angle_pos = self.polar_sketcher.convert_to_stepper_positions(
                                                                            self.path_generator.canvas_size,
                                                                            first_point)
                    self.polar_sketcher.add_position(
                        amplitude_pos,
                        angle_pos,
                        pen=20,
                        amplitude_velocity=5000,
                        angle_velocity=1500
                    )
                    previous_point = (0, 0)

                # update all web connections
                self._broadcast(json.dumps({
                    "type": "update",
                    "payload": self.drawn_paths
                }))
            else:
                self.current_path.append(point)
                if self.polar_sketcher is not None:
                    amplitude_pos, angle_pos = self.polar_sketcher.convert_to_stepper_positions(
                                                                            self.path_generator.canvas_size,
                                                                            point)
                    self.polar_sketcher.add_position(
                        amplitude_pos,
                        angle_pos,
                        pen=0 if previous_point == (0, 0) else 20,
                        amplitude_velocity=5000,
                        angle_velocity=1500
                    )
                    print(self.polar_sketcher.update_status())

                if previous_point == (0, 0):
                    first_point = point
                previous_point = point

        if self.polar_sketcher is not None:
            while True:
                status = self.polar_sketcher.update_status()
                if status.nextPosToGoIdx != status.nextPosToPlaceIdx-1:
                    time.sleep(.1)
                else:
                    break
            self.polar_sketcher.set_mode(Mode.HOME)
        self._close_all_webconnections()
                
    def _close_all_webconnections(self):
        for _, webconn in self.connected_ws.items():
            webconn.close()
        self.connected_ws = {}

    def _broadcast(self, msg: str):
        to_delete = []
        for origin, web_conn in self.connected_ws.items():
            try:
                web_conn.ws.send(msg)
            except Exception as e:
                print("failed sending point to %s:" % origin, type(e), e)
                web_conn.event.set()
                to_delete.append(origin)

        for ws in to_delete:
            del self.connected_ws[ws]

    def stop(self, wait=True):
        self._stop = True
        if wait and self.worker.is_alive():
            self.worker.join()



class DrawingJobManager:
    def __init__(self):
        self.current_job: DrawingJob = None

    def stop(self):
        if self.current_job:
            self.current_job.stop()

    def get_job(self) -> DrawingJob:
        return self.current_job

    def start_drawing_job(self, path_generator: PathGenerator, polar_sketcher: PolarSketcherInterface):
        job_id = uuid.uuid4()
        self.current_job = DrawingJob(job_id, path_generator, polar_sketcher)
        self.current_job.start()
        return str(job_id)
