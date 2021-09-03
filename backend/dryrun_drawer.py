import json
import uuid
import pygame
from queue import Empty, Full
from old_experiments.svg_parser import SVGParser
from threading import Thread, Event
from multiprocessing import Process, Queue
from geventwebsocket.websocket import WebSocket
from typing import Union


class DrawingJob:
    def __init__(self, job_id, process: Process, shutdown_queue, update_queue):
        self.job_id = job_id
        self.process = process
        self.shutdown_queue = shutdown_queue
        self.update_queue = update_queue
        self._update_getter = None

        self.drawn_positions = []
        self.connected_ws: dict[str, (WebSocket, Event)] = {}

    def start(self):
        self._update_getter = Thread(target=self._read_updates)
        self._update_getter.start()

    def add_websocket(self, ws: WebSocket, event: Event):
        self.connected_ws[ws.origin] = (ws, event)
        ws.send(json.dumps({
            "type": "update",
            "payload": self.drawn_positions
        }))

    def _read_updates(self):
        while True:
            update = self.update_queue.get()
            if type(update) is bool:
                try:
                    self.process.join()
                    self.process.close()
                    self.process = None
                    event.set()
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
                        print("failed sending point to %s:" % origin, e)
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

    def draw(self, path: str, offset=(0, 0), scale=1.0, size=(0, 0)) -> str:
        self.parser.parse(path)
        return self.start_drawing(offset=offset, render_scale=scale, render_size=size)

    def start_drawing(self,
                      center=False,
                      scale_to_fit=False,
                      offset=(0, 0),
                      render_scale=1.0,
                      render_size=(0, 0),
                      canvas_scale=1,
                      use_viewbox_canvas=False,
                      points_per_mm=1,
                      fps=60) -> str:

        if self.current_job:
            self.current_job.stop()
            self.current_job = None

        shutdown_queue = Queue()
        update_queue = Queue()
        process = Process(target=self._start_drawing,
                          kwargs={"center": center,
                                  "scale_to_fit": scale_to_fit,
                                  "offset": offset,
                                  "render_scale": render_scale,
                                  "render_size": render_size,
                                  "canvas_scale": canvas_scale,
                                  "use_viewbox_canvas": use_viewbox_canvas,
                                  "points_per_mm": points_per_mm,
                                  "fps": fps,
                                  "shutdown_queue": shutdown_queue,
                                  "update_queue": update_queue})
        process.start()  # starting here instead of inside DrawingJob to avoid a weird issue
        job_id = uuid.uuid4()
        self.current_job = DrawingJob(job_id, process, shutdown_queue, update_queue)
        self.current_job.start()
        return str(job_id)


    def _start_drawing(self,
                       center=False,
                       scale_to_fit=False,
                       offset=(0, 0),
                       render_scale=1.0,
                       render_size=(0, 0),
                       canvas_scale=1,
                       use_viewbox_canvas=False,
                       points_per_mm=2,
                       fps=60,
                       shutdown_queue=Queue(),
                       update_queue=Queue()):
        svg = self.parser.svg
        canvas_size = self.parser.canvas_size
        bbox_width = svg.bbox()[2] - svg.bbox()[0]
        bbox_height = svg.bbox()[3] - svg.bbox()[1]
        if bbox_width > svg.viewbox.width or bbox_height > svg.viewbox.height:
            # This fixes the bbox size in case it happens
            # to be bigger than the viewbox for some reason
            width_scale = bbox_width / svg.viewbox.width
            height_scale = bbox_height / svg.viewbox.height
            fix_render_scale = max(width_scale, height_scale)  # meant to preserve aspect ratio
            bbox_width = bbox_width * fix_render_scale
            bbox_height = bbox_height * fix_render_scale

        width = int(canvas_size[0].amount * canvas_scale)
        height = int(canvas_size[1].amount * canvas_scale)

        print(bbox_width, bbox_height, svg.bbox(), svg.viewbox)
        render_translate = [0, 0]
        if scale_to_fit:
            width_scale = width / svg.viewbox.width
            height_scale = height / svg.viewbox.height
            render_scale = max(width_scale, height_scale)  # meant to preserve aspect ratio
        elif use_viewbox_canvas:
            width = int(svg.viewbox.width)
            height = int(svg.viewbox.height)

        if render_size != (0, 0):
            render_scale = render_size[0] / bbox_width

        scaled_bbox_width = bbox_width * render_scale
        scaled_bbox_height = bbox_height * render_scale

        if center:
            scaled_bbox = list(map(lambda x: x * render_scale, svg.bbox()))
            scaled_offset = scaled_bbox[:2]
            render_translate[0] = -scaled_offset[0] + (width - scaled_bbox_width) / 2
            render_translate[1] = -scaled_offset[1] + (height - scaled_bbox_height) / 2
        else:
            render_translate = offset

        # init canvas
        pygame.init()
        surface = pygame.display.set_mode((int(canvas_size[0].amount), int(canvas_size[1].amount)))
        surface.fill(pygame.Color('white'))  # set background to white
        clock = pygame.time.Clock()

        all_paths = self.parser.get_paths()
        for point in self.parser.get_all_points(paths=all_paths,
                                                render_translate=render_translate,
                                                render_scale=render_scale,
                                                scale_to_fit=scale_to_fit,
                                                points_per_mm=points_per_mm):
            pygame.draw.circle(surface,
                               pygame.Color('black'), point, 2 * max(.5, render_scale))
            pygame.display.update()
            pygame.event.pump()
            clock.tick(fps)
            update_queue.put(point)

            # if there is something in the queue we should quit
            try:
                if wait_for_exit(shutdown_queue, update_queue):
                    return
            except Empty:
                pass

        while True:
            if wait_for_exit(shutdown_queue, update_queue):
                return


def wait_for_exit(shutdown_queue: Queue, update_queue: Queue):
    try:
        shutdown_queue.get_nowait()
        pygame.quit()
        shutdown_queue.put(True)
        update_queue.put(True)
        return True
    except Empty:
        pass

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            shutdown_queue.put(True)
            update_queue.put(True)
            return True

    return False
