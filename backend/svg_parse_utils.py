import os
from tempfile import NamedTemporaryFile
from typing import List, Tuple

from svgelements import SVG, Path, Shape
from svgpathtools import Path as ToolsPath


def parse(path: str, canvas_size: Tuple[float, float], split=True) -> Tuple[SVG, List[ToolsPath]]:
    f = None
    if not os.path.exists(path):
        f = NamedTemporaryFile("w")
        f.write(path)
        f.flush()
        path = f.name

    svg = SVG.parse(path, width=canvas_size[0], height=canvas_size[1])
    if f is not None:
        f.close()

    paths = []
    for element in svg.elements():
        try:
            if element.values['visibility'] == 'hidden':
                continue
        except (KeyError, AttributeError):
            pass

        if isinstance(element, Path):
            if len(element) != 0:
                paths.append(ToolsPath(element.d()))
        elif isinstance(element, Shape):
            e = Path(element)
            # In some cases the shape could not have reified, the path must.
            e.reify()
            if len(e) != 0:
                paths.append(ToolsPath(e.d()))

    if split:
        paths = split_svgpaths(paths)

    return svg, paths


def split_svgpaths(paths: List[ToolsPath]) -> List[ToolsPath]:
    all_subpaths = []
    for path in paths:
        subpaths = path.continuous_subpaths()
        all_subpaths.extend(subpaths)

    return all_subpaths


def get_all_points(paths: list[Path],
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
        for point in get_points(path, canvas_size, render_translate, render_scale, rotation, toolpath_rotation,
                                points_per_mm):
            yield point

        # signal end of path
        yield None


def get_points(path: ToolsPath, canvas_size: Tuple[float, float], render_translate=(0, 0), render_scale=1.0, rotation=0,
               toolpath_rotation=0, points_per_mm=2.0):
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

    scaled_path_len = path_len * render_scale
    total_points = int(scaled_path_len * points_per_mm)
    if total_points == 0:
        return

    origin = complex(canvas_size[0] / 2, canvas_size[1] / 2)
    path = path.rotated(rotation - toolpath_rotation, origin)

    for i in range(0, total_points + 1):
        point = path.point(i / total_points)
        scaled_point = point * render_scale
        yield (scaled_point.real + render_translate[0],
               scaled_point.imag + render_translate[1])
