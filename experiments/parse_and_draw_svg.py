import os
import sys
from tempfile import NamedTemporaryFile
from typing import List

import pygame
from svgelements import *
from svgpathtools import svg2paths, Path as ToolsPath, Line as ToolsLine

from toolpaths_generation_algorithms import horizontal_lines as new_horizontal_lines

PIXELS_BETWEEN_POINTS = 5
CANVAS_WIDTH = 600
CANVAS_HEIGHT = 600


def bbox_to_pygame_rect(xmin, xmax, ymin, ymax):
    # left, top, width, height
    return xmin, ymax, xmax - xmin, ymin - ymax


def linearize_paths(paths: List[ToolsPath]) -> List[ToolsPath]:
    out_paths = []
    for path in paths:
        subpath = ToolsPath()

        number_of_steps = int((path.length() / PIXELS_BETWEEN_POINTS) + .5)
        real_end = start = path.point(0)
        for i in range(1, number_of_steps):
            end = path.point(min(1.0, i / number_of_steps))
            subpath.append(ToolsLine(start, end))
            start = end

        subpath.append(ToolsLine(start, real_end))
        out_paths.append(subpath)

    return out_paths


def split_svgpaths(paths: List[ToolsPath]) -> List[ToolsPath]:
    all_subpaths = []
    for path in paths:
        subpaths = path.continuous_subpaths()
        all_subpaths.extend(subpaths)

    return all_subpaths


def parse_svgpathtools(path: str, split=True) -> List[ToolsPath]:
    paths, _ = svg2paths(path)
    if split:
        paths = split_svgpaths(paths)

    return paths


def parse_svgelements(path: str, split=True) -> List[ToolsPath]:
    f = None
    if not os.path.exists(path):
        f = NamedTemporaryFile("w")
        f.write(path)
        f.flush()
        path = f.name

    svg = SVG.parse(path, width=CANVAS_WIDTH, height=CANVAS_HEIGHT)
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
            e.reify()  # In some cases the shape could not have reified, the path must.
            if len(e) != 0:
                paths.append(ToolsPath(e.d()))

    if split:
        paths = split_svgpaths(paths)

    return paths


def draw_lines(paths: List[ToolsPath], surface, color, stroke=2):
    for path in paths:
        number_of_steps = int((path.length() / PIXELS_BETWEEN_POINTS) + .5)
        real_end = start = path.point(0)
        for i in range(1, number_of_steps):
            end = path.point(min(1.0, i / number_of_steps))
            pygame.draw.line(surface, color,
                             (start.real, start.imag), (end.real, end.imag),
                             stroke)
            start = end

        pygame.draw.line(surface, color,
                         (start.real, start.imag), (real_end.real, real_end.imag),
                         stroke)


def draw_points(paths: List[ToolsPath], surface, color, stroke=2):
    for path in paths:
        number_of_steps = int((path.length() / PIXELS_BETWEEN_POINTS) + .5)
        for i in range(number_of_steps):
            point = path.point(min(1.0, i / number_of_steps))
            pygame.draw.circle(surface,
                               color, (point.real, point.imag), stroke)


def draw_paths(paths: List[ToolsPath], surface, lines=False, color=pygame.Color("blue")):
    if lines:
        draw_lines(paths, surface, color)
    else:
        draw_points(paths, surface, color)


def _draw_bboxes(paths: List[ToolsPath], surface, color):
    for path in paths:
        pygame.draw.rect(surface,
                         color,
                         bbox_to_pygame_rect(*path.bbox()),
                         2)


def draw_bboxes(paths: List[ToolsPath], surface, segments=False, color=pygame.Color('red')):
    if segments:
        new_paths = []
        for path in paths:
            for segment in path:
                new_paths.append(ToolsPath(segment))
        paths = new_paths

    _draw_bboxes(paths, surface, color)


def main():
    file_path = sys.argv[1] if len(sys.argv) > 1 else "/Users/esser50k/Downloads/albert_hoffman_alone_simplified.svg"
    # paths = parse_svgpathtools(file_path)
    svg_paths = parse_svgelements(file_path)
    print("INITAL N PATHS:", len(svg_paths))
    n_segments = 0
    for path in svg_paths:
        for _ in path:
            n_segments += 1

    print("INITIAL N SEGMENTS:", n_segments)

    pygame.init()

    surface = pygame.display.set_mode((CANVAS_WIDTH, CANVAS_HEIGHT))
    surface.fill(pygame.Color('white'))
    # draw_paths(svg_paths, surface, lines=True)
    # draw_bboxes(svg_paths, surface, segments=True)

    # svg_paths = linearize_paths(svg_paths)
    # draw_paths(svg_paths, plain_path_surface, lines=True)

    # svg_paths = list(horizontal_lines(svg_paths, (CANVAS_WIDTH, CANVAS_HEIGHT), angle=0))
    svg_paths = list(new_horizontal_lines(svg_paths, (CANVAS_WIDTH, CANVAS_HEIGHT), n_lines=100, angle=0))
    draw_paths(svg_paths, surface, lines=True, color=pygame.Color("black"))
    # draw_bboxes(svg_paths, surface, segments=True, color=pygame.Color("green"))

    pygame.display.update()  # copy surface to display
    while True:  # loop to wait till window close
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                exit()


if __name__ == '__main__':
    main()
