import io
import os
from tempfile import NamedTemporaryFile
from svgelements import SVG, SVGText, SVGImage, Path, Shape, Length
from svgpathtools import Path as ToolsPath, svg2paths
from sort_paths import sort_paths


def split_svgpathtool_path(paths: list[ToolsPath]) -> list[ToolsPath]:
    all_subpaths = []
    subpath = ToolsPath()
    for path in paths:
        previous_end = None
        for segment in path:
            if previous_end is None:
                subpath.append(segment)
                previous_end = ToolsPath(segment).point(1)
                continue

            path_segment = ToolsPath(segment)
            if abs(previous_end - path_segment.point(0)) > .01:
                all_subpaths.append(subpath)
                subpath = ToolsPath()

            subpath.append(segment)
            previous_end = path_segment.point(1)

    if subpath.length() > 0:
        all_subpaths.append(subpath)

    return all_subpaths


def full_split_svgpathtool_paths(paths: list[ToolsPath]) -> list[ToolsPath]:
    all_subpaths = []
    for path in paths:
        for segment in path:
            all_subpaths.append(ToolsPath(segment))

    return all_subpaths


def split_path(path: Path) -> list[Path]:
    i = 0
    subpaths = []
    while True:
        try:
            subpath = Path(path.subpath(i))
            subpaths.append(subpath)
            i += 1
        except IndexError:
            break

    return subpaths


def get_points(path: Path, render_translate=(0, 0), render_scale=1.0, points_per_mm=2.0):
    try:
        path_len = path.length()
    except ZeroDivisionError:
        point = path.point(0)
        yield ((point.real * render_scale) + render_translate[0],
               (point.imag * render_scale) + render_translate[1])
        return
    except Exception as e:
        print("ERROR", e)
        print(path)
        raise e

    scaled_path_len = path_len * render_scale
    total_points = int(scaled_path_len * points_per_mm)
    if total_points == 0:
        return

    for point in (path.point(i / total_points) for i in range(0, total_points + 1)):
        yield ((point.real * render_scale) + render_translate[0],
               (point.imag * render_scale) + render_translate[1])


class SVGParser:
    def __init__(self,
                 path: str = None,
                 canvas_scale=1,
                 canvas_size: tuple[Length,Length] = (Length("600mm"), Length("600mm"))):
        self.svg = None
        self.svg_path = None
        self.paths = []
        if path:
            if not os.path.exists(path):
                f = NamedTemporaryFile("w")
                f.write(path)
                f.flush()
                path = f.name

            paths, _ = svg2paths(path)
            self.paths = split_svgpathtool_path(paths)
            self.svg = SVG.parse(path)
            self.svg_path = ToolsPath(*self.paths)
        self.canvas_scale = canvas_scale
        self.canvas_size = canvas_size  # (Length("600cm"), Length("600cm"))
        self.paths = None

    def parse(self, path: str, split_parse=False):
        self.paths = []
        if not os.path.exists(path):
            f = NamedTemporaryFile("w")
            f.write(path)
            f.flush()
            path = f.name

        self.svg = SVG.parse(path)
        subpaths = self.get_paths()
        if split_parse:
            paths, attrs = svg2paths(path)
            # self.paths = split_svgpathtool_path(paths)
            self.paths = full_split_svgpathtool_paths(paths)
            print("Split Paths", len(self.paths))
            self.svg_path = ToolsPath(*self.paths)
        else:
            parsed_paths = []
            for i in range(len(subpaths)):
                parsed_paths.append(ToolsPath(subpaths[i].d()))
            self.paths = parsed_paths

    def get_paths(self) -> list[Path]:
        if self.paths:
            return self.paths

        elements = []
        for element in self.svg.elements():
            try:
                if element.values['visibility'] == 'hidden':
                    continue
            except (KeyError, AttributeError):
                pass
            if isinstance(element, SVGText):
                elements.append(element)
            elif isinstance(element, Path):
                if len(element) != 0:
                    elements.append(element)
            elif isinstance(element, Shape):
                e = Path(element)
                e.reify()  # In some cases the shape could not have reified, the path must.
                if len(e) != 0:
                    elements.append(e)
            elif isinstance(element, SVGImage):
                try:
                    element.load()
                    if element.image is not None:
                        elements.append(element)
                except OSError:
                    pass

        self.paths = []
        for element in elements:
            self.paths.extend(split_path(element))

        return self.paths

    def get_all_points(self, paths: list[Path], render_translate=(0, 0), render_scale=1.0, optimize_paths=False,
                       scale_to_fit=True, center=False, use_viewbox_canvas=False, points_per_mm=2):
        bbox_width = self.svg.bbox()[2] - self.svg.bbox()[0]
        bbox_height = self.svg.bbox()[3] - self.svg.bbox()[1]
        width = int(self.canvas_size[0].amount * self.canvas_scale)
        height = int(self.canvas_size[1].amount * self.canvas_scale)

        if scale_to_fit:
            width_scale = width / self.svg.viewbox.width
            height_scale = height / self.svg.viewbox.height
            render_scale = min(width_scale, height_scale)  # meant to preserve aspect ratio
        elif use_viewbox_canvas:
            width = int(self.svg.viewbox.width)
            height = int(self.svg.viewbox.height)

        if center:
            scaled_bbox_width = bbox_width * render_scale
            scaled_bbox_height = bbox_height * render_scale
            scaled_bbox = list(map(lambda x: x * render_scale, self.svg.bbox()))
            scaled_offset = scaled_bbox[:2]
            render_translate = list(render_translate)  # convert to list
            render_translate[0] = -scaled_offset[0] + (width - scaled_bbox_width) / 2
            render_translate[1] = -scaled_offset[1] + (height - scaled_bbox_height) / 2

        if optimize_paths:
            paths = sort_paths(complex(0, self.svg.viewbox.height), paths, (width, height))

        for path in paths:
            for point in get_points(path, render_translate, render_scale, points_per_mm):
                yield point
