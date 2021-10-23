import json
import uuid
from queue import Queue, Empty, Full
from svg_parser import SVGParser
from threading import Thread, Event
from geventwebsocket.websocket import WebSocket
from toolpath_generation import TOOLPATHS
from sort_paths import SORTING_ALGORITHMS, sort_paths
from typing import Union

class DrawingJob:
    def __init__(self, job_id, worker: Thread, shutdown_queue, update_queue):
        self.job_id = job_id
        self.worker = worker
        self.shutdown_queue = shutdown_queue
        self.update_queue = update_queue
        self._update_getter = None

        self.drawn_positions = []
        self.connected_ws: dict[str, (WebSocket, Event)] = {}

    def start(self):
        self.worker.start()
        self._update_getter = Thread(target=self._read_updates)
        self._update_getter.start()

    def add_websocket(self, ws: WebSocket, event: Event):
        key = ws.origin + str(uuid.uuid4())
        self.connected_ws[ws.origin + str(uuid.uuid4())] = (ws, event)
        ws.send(json.dumps({
            "type": "update",
            "payload": self.drawn_positions
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

    def _read_updates(self):
        while True:
            update = self.update_queue.get()
            if type(update) is bool:
                try:
                    # don't know why it won't join
                    #self.worker.join()
                    self.worker = None
                    self._close_all_websockets()
                    return
                except Empty:
                    pass

            if type(update) is tuple:
                self.drawn_positions.append(update)
                to_delete = []
                for origin, ws_event in self.connected_ws.items():
                    ws, event = ws_event
                    try:
                        ws.send(json.dumps({
                            "type": "update",
                            "payload": [update]
                        }))
                    except Exception as e:
                        print("failed sending point to %s:" % origin, type(e), e)
                        event.set()
                        to_delete.append(origin)

                for ws in to_delete:
                    del self.connected_ws[ws]

    def stop(self):
        try:
            self.shutdown_queue.put(True)
        except Full:
            return


class DryrunDrawer:
    def __init__(self, parser: SVGParser):
        self.parser = parser
        self.drawing_process = None
        self.queue = None
        self.current_job = None

    def stop(self):
        if self.current_job:
            self.current_job.stop()

    def get_job(self) -> Union[DrawingJob, None]:
        return self.current_job

    def draw(self,
             path: str,
             offset=(0, 0),
             scale=1.0,
             size=(0, 0),
             rotation=0,
             toolpath_config=None,
             pathsort_config=None) -> str:
        if toolpath_config is None:
            toolpath_config = {}
        if pathsort_config is None:
            pathsort_config = {}

        self.parser.parse(path)
        return self.start_drawing(offset=offset,
                                  render_scale=scale,
                                  render_size=size,
                                  rotation=rotation,
                                  toolpath_config=toolpath_config,
                                  pathsort_config=pathsort_config)

    def start_drawing(self,
                      offset=(0, 0),
                      render_scale=1.0,
                      render_size=(0, 0),
                      rotation=0,
                      points_per_mm=.2,
                      toolpath_config=None,
                      pathsort_config=None) -> str:
        if toolpath_config is None:
            toolpath_config = {}
        if pathsort_config is None:
            pathsort_config = {}

        if self.current_job:
            self.current_job.stop()
            self.current_job = None

        shutdown_queue = Queue()
        update_queue = Queue()
        worker = Thread(target=self._start_drawing,
                        kwargs={"offset": offset,
                                "render_scale": render_scale,
                                "render_size": render_size,
                                "rotation": rotation,
                                "points_per_mm": points_per_mm,
                                "shutdown_queue": shutdown_queue,
                                "update_queue": update_queue,
                                "toolpath_config": toolpath_config,
                                "pathsort_config": pathsort_config})
        job_id = uuid.uuid4()
        self.current_job = DrawingJob(job_id, worker, shutdown_queue, update_queue)
        self.current_job.start()
        return str(job_id)

    def _start_drawing(self,
                       offset=(0, 0),
                       render_scale=1.0,
                       render_size=(0, 0),
                       rotation=0,
                       points_per_mm=2,
                       shutdown_queue=Queue(),
                       update_queue=Queue(),
                       toolpath_config=None,
                       pathsort_config=None):
        if toolpath_config is None:
            toolpath_config = {}
        if pathsort_config is None:
            pathsort_config = {}

        render_translate = offset
        if render_size != (0, 0):
            render_scale_width = render_size[0] / self.parser.canvas_size[0].amount
            render_scale_height = render_size[1] / self.parser.canvas_size[1].amount
            render_scale *= max(render_scale_width, render_scale_height)

        all_paths = self.parser.paths

        toolpath = TOOLPATHS[toolpath_config["algorithm"]] \
            if "algorithm" in toolpath_config.keys() and toolpath_config["algorithm"] in TOOLPATHS.keys() \
            else None

        if toolpath is not None:
            all_paths = list(toolpath(all_paths,
                                      (self.parser.canvas_size[0].amount, self.parser.canvas_size[1].amount),
                                      n_lines=toolpath_config["n_lines"],
                                      angle=toolpath_config["angle"]))

        pathsort_algo = SORTING_ALGORITHMS[pathsort_config["algorithm"]] \
            if "algorithm" in pathsort_config.keys() and pathsort_config["algorithm"] in SORTING_ALGORITHMS.keys() \
            else None

        if pathsort_algo is not None:
            all_paths = sort_paths(paths=all_paths,
                                   start_point=complex(pathsort_config["x"], pathsort_config["y"]),
                                   canvas_size=(self.parser.canvas_size[0].amount, self.parser.canvas_size[1].amount),
                                   sorting_algo=pathsort_algo)

        for point in self.parser.get_all_points(paths=all_paths,
                                                render_translate=render_translate,
                                                render_scale=render_scale,
                                                rotation=rotation,
                                                toolpath_rotation=toolpath_config["angle"],
                                                points_per_mm=points_per_mm):
            update_queue.put(point)

            # if there is something in the queue we should quit
            try:
                if wait_for_exit(shutdown_queue, update_queue):
                    return
            except Empty:
                pass

        shutdown_queue.put(True)
        update_queue.put(True)
        return


def wait_for_exit(shutdown_queue: Queue, update_queue: Queue):
    try:
        shutdown_queue.get_nowait()
        shutdown_queue.put(True)
        update_queue.put(True)
        return True
    except Empty:
        pass

    return False
