import svg_parse_utils
from typing import List, Tuple
from svgpathtools import Path, Line
from enum import Enum
from toolpath_generation.horizontal_lines import horizontal_lines
from toolpath_generation.connecting_lines import zigzag_lines, rect_lines
from sort_paths import find_closest_path, \
    find_closest_path_with_endpoint, \
    find_closest_path_with_circular_path_check, \
    find_closest_path_with_radar_scan, \
    sort_paths


class ToolpathAlgorithm(Enum):
    NONE = "none"
    LINES = "lines"
    ZIGZAG = "zigzag"
    RECTLINES = "rectlines"


def _get_toolpath_algo_func(toolpath_algo: ToolpathAlgorithm):
    toolpath_algorithms = {
        ToolpathAlgorithm.NONE: None,
        ToolpathAlgorithm.LINES: horizontal_lines,
        ToolpathAlgorithm.ZIGZAG: zigzag_lines,
        ToolpathAlgorithm.RECTLINES: rect_lines
    }

    if toolpath_algo not in toolpath_algorithms.keys():
        return None

    return toolpath_algorithms[toolpath_algo]


class PathsortAlgorithm(Enum):
    NONE = "none"
    CLOSEST_PATH = "closest_path"
    CLOSEST_PATH_WITH_REVERSED_START = "closest_path_with_reverse"
    CLOSEST_PATH_START_ANYWHERE = "closest_path_with_start_anywhere"
    RADAR_SCAN = "radar_scan"


def _get_path_sorting_algo_func(path_sorting_algorithm: PathsortAlgorithm):
    path_sort_algorithms = {
        PathsortAlgorithm.NONE: None,
        PathsortAlgorithm.CLOSEST_PATH: find_closest_path,
        PathsortAlgorithm.CLOSEST_PATH_WITH_REVERSED_START: find_closest_path_with_endpoint,
        PathsortAlgorithm.CLOSEST_PATH_START_ANYWHERE: find_closest_path_with_circular_path_check,
        PathsortAlgorithm.RADAR_SCAN: find_closest_path_with_radar_scan,

    }

    if path_sorting_algorithm not in path_sort_algorithms.keys():
        return None

    return path_sort_algorithms[path_sorting_algorithm]


def _generate_boundary_path(full_canvas_size: Tuple,
                            canvas_size: Tuple,
                            plotter_base_size: Tuple) -> Path:
    x_offset = full_canvas_size[0] - canvas_size[0]

    canvas_top_left = complex(x_offset, 0)
    base_top_left_corner = complex(
        full_canvas_size[0] - plotter_base_size[0], 0)
    base_bottom_left_corner = complex(
        full_canvas_size[0] - plotter_base_size[0], plotter_base_size[1])
    base_bottom_right_corner = complex(
        full_canvas_size[0], plotter_base_size[1])
    canvas_bottom_right = complex(full_canvas_size[0], canvas_size[1])
    canvas_bottom_left = complex(x_offset, canvas_size[1])

    path = Path()
    path.append(Line(canvas_top_left, base_top_left_corner))
    path.append(Line(base_top_left_corner, base_bottom_left_corner))
    path.append(Line(base_bottom_left_corner, base_bottom_right_corner))
    path.append(Line(base_bottom_right_corner, canvas_bottom_right))
    path.append(Line(canvas_bottom_right, canvas_bottom_left))
    path.append(Line(canvas_bottom_left, canvas_top_left))

    return path


CLOSE_PATH_COMMAND = "CLOSE_PATH"
PATH_END_COMMAND = "PATH_END"
DRAWING_END_COMMAND = "DRAWING_END"


class PathGenerator:
    def __init__(self):
        self.paths = []
        self.offset = (0, 0)
        self.canvas_size = (0, 0)
        self.render_scale = 1.0
        self.render_size = (0, 0)
        self.rotation = 0
        self.points_per_mm = 1

        self.path_sorting_algorithm = PathsortAlgorithm.NONE
        self.path_sort_start_point = complex(0, 0)

        self.toolpath_generation_algorithm = ToolpathAlgorithm.NONE
        self.toolpath_line_step = 10
        self.toolpath_angle = 0

    def load_svg(self, svg: str):
        _, all_paths = svg_parse_utils.parse(svg, self.canvas_size)
        self.add_paths(all_paths)

    def add_paths(self, paths: List[Path]):
        self.paths.extend(paths)

    def set_canvas_size(self, canvas_size: Tuple):
        self.canvas_size = canvas_size

    def set_offset(self, offset: Tuple):
        self.offset = offset

    def set_render_scale(self, render_scale: float):
        self.render_scale = render_scale

    # set the virtual canvas size in mm
    def set_render_size(self, render_size: Tuple):
        self.render_size = render_size

    def set_rotation(self, rotation: float):
        self.rotation = rotation

    def set_points_per_mm(self, points_per_mm: int):
        self.points_per_mm = points_per_mm

    def set_pathsort_algorithm(self, path_sorting_algorithm: PathsortAlgorithm):
        self.path_sorting_algorithm = path_sorting_algorithm

    def set_pathsort_start_point(self, start_point: complex):
        self.path_sort_start_point = start_point

    def set_toolpath_algorithm(self, toolpath_generation_algorithm: ToolpathAlgorithm):
        self.toolpath_generation_algorithm = toolpath_generation_algorithm

    def set_toolpath_line_number(self, line_step: int):
        self.toolpath_line_step = line_step

    def set_toolpath_angle(self, angle: int):
        self.toolpath_angle = angle

    def generate_points(self):
        render_scale = self.render_scale
        if self.render_size != (0, 0):
            render_scale_width = self.render_size[0] / self.canvas_size[0]
            render_scale_height = self.render_size[1] / self.canvas_size[1]
            render_scale *= max(render_scale_width, render_scale_height)

        paths = self.paths.copy()
        if self.toolpath_generation_algorithm is not ToolpathAlgorithm.NONE:
            toolpath_algorithm_func = _get_toolpath_algo_func(
                self.toolpath_generation_algorithm)
            paths = list(toolpath_algorithm_func(paths,
                                                 self.canvas_size,
                                                 line_step=self.toolpath_line_step,
                                                 angle=self.toolpath_angle))

        if self.path_sorting_algorithm is not PathsortAlgorithm.NONE:
            path_sort_algorithm = _get_path_sorting_algo_func(
                self.path_sorting_algorithm)
            paths = sort_paths(paths=paths,
                               start_point=self.path_sort_start_point,
                               canvas_size=self.canvas_size,
                               sorting_algo=path_sort_algorithm)

        for point in self.__get_all_points(paths=paths,
                                           canvas_size=self.canvas_size,
                                           render_translate=self.offset,
                                           render_scale=render_scale,
                                           rotation=self.rotation,
                                           toolpath_rotation=self.toolpath_angle):
            yield point

    def __get_all_points(self,
                         paths: list[Path],
                         canvas_size: Tuple[float, float],
                         render_translate=(0, 0),
                         render_scale=1.0,
                         rotation=0,
                         toolpath_rotation=0,
                         points_per_mm=2.0):
        """
        # TODO center bbox
        if center:
            scaled_bbox_width = bbox_width * render_scale
            scaled_bbox_height = bbox_height * render_scale
            scaled_bbox = list(map(lambda x: x * render_scale, self.svg.bbox()))
            scaled_offset = scaled_bbox[:2]
            render_translate = list(render_translate)  # convert to list
            render_translate[0] = -scaled_offset[0] + (width - scaled_bbox_width) / 2
            render_translate[1] = -scaled_offset[1] + (height - scaled_bbox_height) / 2
        """

        for path in paths:
            for point in self.__get_points(path,
                                           canvas_size,
                                           render_translate,
                                           render_scale,
                                           rotation,
                                           toolpath_rotation):
                yield point

            # signal end of path
            if len(path) > 0 and path.isclosedac():
                yield CLOSE_PATH_COMMAND

            yield PATH_END_COMMAND

    def __get_points(self,
                     path: Path,
                     canvas_size: Tuple[float, float],
                     render_translate=(0, 0),
                     render_scale=1.0,
                     rotation=0,
                     toolpath_rotation=0):
        try:
            path_len = path.length()
        except ZeroDivisionError:
            point = path.point(0)
            yield ((point.real * render_scale) + render_translate[0],
                   (point.imag * render_scale) + render_translate[1])
            return
        except Exception as e:
            print("path", len(path))
            print("error getting points:", e)
            raise e

        scaled_path_len = path_len * render_scale * 15
        total_points = int(scaled_path_len)
        if total_points == 0:
            return

        origin = complex(canvas_size[0] / 2, canvas_size[1] / 2)
        path = path.rotated(rotation - toolpath_rotation, origin)

        for i in range(0, total_points + 1):
            point = path.point(i / total_points)
            point = complex(point.real, point.imag)
            scaled_point = point * render_scale
            yield (scaled_point.real + render_translate[0],
                   scaled_point.imag + render_translate[1])
