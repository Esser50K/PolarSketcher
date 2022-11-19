import json
import uuid
from queue import Queue, Empty, Full
from threading import Thread, Event
from typing import Union, List, Tuple

from geventwebsocket.websocket import WebSocket
from svgelements import SVG
from svgpathtools import Path

import svg_parse_utils
from polar_sketcher_connector import PolarSketcherConnector
from sort_paths import SORTING_ALGORITHMS, sort_paths
from toolpath_generation.algorithm_getter import get_toolpath_algo

DRAWING_END_COMMAND = "DRAWING_END"
PATH_END_COMMAND = "PATH_END"


class DrawingJob:
    def __init__(self, job_id, worker: Thread, shutdown_queue, update_queue):
        self.job_id = job_id
        self.worker = worker
        self.shutdown_queue = shutdown_queue
        self.update_queue = update_queue
        self._update_getter = None

        self.drawn_paths = []
        self.current_path = []
        self.connected_ws: dict[str, (WebSocket, Event)] = {}

    def start(self):
        self.worker.start()
        self._update_getter = Thread(target=self._read_updates)
        self._update_getter.start()

    def add_websocket(self, ws: WebSocket, event: Event):
        key = ws.origin + str(uuid.uuid4())
        self.connected_ws[key] = (ws, event)
        ws.send(json.dumps({
            "type": "update",
            "payload": self.drawn_paths
        }))

    def _close_all_websockets(self):
        for origin, ws_event in self.connected_ws.items():
            ws, event = ws_event
            try:
                event.set()
                ws.close()
            except Exception as e:
                print("failed closing ws from %s:" % origin, type(e), e)
                event.set()
        self.connected_ws = {}

    def _broadcast(self, msg: str):
        to_delete = []
        for origin, ws_event in self.connected_ws.items():
            ws, event = ws_event
            try:
                ws.send(msg)
            except Exception as e:
                print("failed sending point to %s:" % origin, type(e), e)
                event.set()
                to_delete.append(origin)

        for ws in to_delete:
            del self.connected_ws[ws]

    def _read_updates(self):
        while True:
            update = self.update_queue.get()
            if type(update) is str:
                if update == DRAWING_END_COMMAND:
                    try:
                        # don't know why it won't join
                        # self.worker.join()
                        self.worker = None
                        self._close_all_websockets()
                        return
                    except Empty:
                        pass
                elif update == PATH_END_COMMAND:
                    self.drawn_paths.append(self.current_path)
                    self.current_path = []
                    self._broadcast(json.dumps({
                        "type": "update",
                        "payload": self.drawn_paths
                    }))

            if type(update) is tuple:
                self.current_path.append(update)

    def stop(self):
        try:
            self.shutdown_queue.put(True)
        except Full:
            return


class DryrunDrawer:
    def __init__(self, canvas_size: Tuple[float, float]):
        self.current_job: DrawingJob = None
        self.canvas_size = canvas_size

    def stop(self):
        if self.current_job:
            self.current_job.stop()

    def get_job(self) -> Union[DrawingJob, None]:
        return self.current_job

    def draw(self,
             svg_str: str,  # can be svg content or file path
             offset=(0, 0),
             render_scale=1.0,
             render_size=(0, 0),
             rotation=0,
             points_per_mm=.5,
             toolpath_config=None,
             pathsort_config=None,
             dryrun=True) -> str:

        svg, all_paths = svg_parse_utils.parse(svg_str, self.canvas_size)
        if self.current_job:
            self.current_job.stop()
            self.current_job = None

        shutdown_queue = Queue()
        update_queue = Queue()
        worker = Thread(target=self._start_drawing,
                        kwargs={"svg": svg,
                                "paths": all_paths,
                                "offset": offset,
                                "render_scale": render_scale,
                                "render_size": render_size,
                                "rotation": rotation,
                                "points_per_mm": points_per_mm,
                                "shutdown_queue": shutdown_queue,
                                "update_queue": update_queue,
                                "dryrun": dryrun,
                                "toolpath_config": toolpath_config,
                                "pathsort_config": pathsort_config})
        job_id = uuid.uuid4()
        self.current_job = DrawingJob(job_id, worker, shutdown_queue, update_queue)
        self.current_job.start()
        return str(job_id)

    def _start_drawing(self,
                       svg: SVG,
                       paths: List[Path],
                       offset=(0, 0),
                       render_scale=1.0,
                       render_size=(0, 0),
                       rotation=0,
                       points_per_mm=2,
                       shutdown_queue=Queue(),
                       update_queue=Queue(),
                       toolpath_config=None,
                       pathsort_config=None,
                       dryrun=True):
        if toolpath_config is None:
            toolpath_config = {}
        if pathsort_config is None:
            pathsort_config = {}

        polar_sketcher = None
        if not dryrun:
            polar_sketcher = PolarSketcherConnector()

        render_translate = offset
        if render_size != (0, 0):
            render_scale_width = render_size[0] / self.canvas_size[0]
            render_scale_height = render_size[1] / self.canvas_size[1]
            render_scale *= max(render_scale_width, render_scale_height)

        toolpath_algorithm_func = get_toolpath_algo(toolpath_config["algorithm"]) \
            if "algorithm" in toolpath_config.keys() else None

        if toolpath_algorithm_func is not None:
            paths = list(toolpath_algorithm_func(paths,
                                                 self.canvas_size,
                                                 n_lines=toolpath_config["n_lines"],
                                                 angle=toolpath_config["angle"]))

        pathsort_algo = SORTING_ALGORITHMS[pathsort_config["algorithm"]] \
            if "algorithm" in pathsort_config.keys() and pathsort_config["algorithm"] in SORTING_ALGORITHMS.keys() \
            else None

        if pathsort_algo is not None:
            paths = sort_paths(paths=paths,
                               start_point=complex(pathsort_config["x"], pathsort_config["y"]),
                               canvas_size=self.canvas_size,
                               sorting_algo=pathsort_algo)

        for point in svg_parse_utils.get_all_points(paths=paths,
                                                    canvas_size=self.canvas_size,
                                                    render_translate=render_translate,
                                                    render_scale=render_scale,
                                                    rotation=rotation,
                                                    toolpath_rotation=toolpath_config["angle"],
                                                    points_per_mm=points_per_mm):
            if polar_sketcher is not None:
                polar_sketcher.draw_point(point)

            if point is None:
                update_queue.put(PATH_END_COMMAND)
            else:
                update_queue.put(point)

            # if there is something in the queue we should quit
            if wait_for_exit(shutdown_queue, update_queue):
                if polar_sketcher is not None:
                    polar_sketcher.shutdown()
                return

        update_queue.put(DRAWING_END_COMMAND)
        if polar_sketcher is not None:
            polar_sketcher.shutdown()


def wait_for_exit(shutdown_queue: Queue, update_queue: Queue):
    try:
        shutdown_queue.get_nowait()  # should trigger the exception on this line
        update_queue.put(True)
        return True
    except Empty:
        pass

    return False
