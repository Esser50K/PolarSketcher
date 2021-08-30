import pygame
from queue import Empty, Full
from old_experiments.svg_parser import SVGParser
from multiprocessing import Process, Queue

scale = 1
offset = 250

# variables also on the arduino
# microstepping mode
stepperMode = 32
# fancy variable to give space for the pen when platform is turning around the edge
platformOffsetBuffer = 50 * stepperMode
# offset of the stepper motor platform in full steps
platformOffset = 255 * stepperMode
# max amplitude in full steps (times microstepping mode)
maxAmplitude = (2000 * stepperMode) + platformOffset
# max angle (which is 90º) in full steps (times microstepping mode)
maxAngle = 880 * stepperMode


class DryrunDrawer:
    def __init__(self, parser: SVGParser):
        self.parser = parser
        self.drawing_process = None
        self.queue= None

    def stop(self):
        if self.queue:
            try:
                self.queue.put_nowait(True)
                self.queue.get()
            except Full:
                return

    def draw(self, path: str, offset=(0, 0), scale=1.0):
        self.parser.parse(path)
        self.start_drawing(offset=offset, render_scale=scale)

    def start_drawing(self,
                      center=False,
                      scale_to_fit=False,
                      offset=(0, 0),
                      render_scale=1.0,
                      canvas_scale=1,
                      use_viewbox_canvas=False,
                      points_per_mm=1,
                      fps=60):
        self.queue = Queue()
        self.drawing_process = Process(target=self._start_drawing,
                                       kwargs={"center": center,
                                               "scale_to_fit": scale_to_fit,
                                               "offset": offset,
                                               "render_scale": render_scale,
                                               "canvas_scale": canvas_scale,
                                               "use_viewbox_canvas": use_viewbox_canvas,
                                               "points_per_mm": points_per_mm,
                                               "fps": fps})
        self.drawing_process.start()

    def _start_drawing(self,
                       center=False,
                       scale_to_fit=False,
                       offset=(0, 0),
                       render_scale=1.0,
                       canvas_scale=1,
                       use_viewbox_canvas=False,
                       points_per_mm=2,
                       fps=60,
                       queue: Queue = Queue()):
        svg = self.parser.svg
        canvas_size = self.parser.canvas_size
        bbox_width = svg.bbox()[2] - svg.bbox()[0]
        bbox_height = svg.bbox()[3] - svg.bbox()[1]
        width = int(canvas_size[0].amount * canvas_scale)
        height = int(canvas_size[1].amount * canvas_scale)

        render_translate = [0, 0]
        if scale_to_fit:
            width_scale = width / svg.viewbox.width
            height_scale = height / svg.viewbox.height
            render_scale = max(width_scale, height_scale)  # meant to preserve aspect ratio
        elif use_viewbox_canvas:
            width = int(svg.viewbox.width)
            height = int(svg.viewbox.height)

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

            # if there is something in the queue we should quit
            try:
                if wait_for_exit(queue):
                    return
            except Empty:
                pass

        while True:
            if wait_for_exit(queue):
                return


def wait_for_exit(queue: Queue):
    try:
        queue.get_nowait()
        pygame.quit()
        queue.put(True)
        return True
    except Empty:
        pass

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            queue.put(True)
            return True

    return False
