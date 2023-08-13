from typing import List, Tuple

from svgpathtools import Path as ToolsPath, Line as ToolsLine

from path_quadtree import QuadTree, Rect, Point

import numpy as np


def get_height_intersections(paths: List[ToolsPath], canvas_dimensions: Tuple[float, float], n_lines=100, angle=0):
    quadtree = QuadTree(
        Rect(
            Point(complex(0, 0)),
            canvas_dimensions[0], canvas_dimensions[1]),
        capacity=20)

    canvas_width, canvas_height = canvas_dimensions
    line_step = int((canvas_height / n_lines) + .5)
    for path in paths:
        quadtree.insert_path(path.rotated(angle, complex(canvas_width / 2, canvas_height / 2)))

    heights = list(range(0, int(canvas_height), line_step))
    lines = {height: ToolsPath(ToolsLine(complex(-10000, height), complex(10000, height))) for height in heights}
    height_intersections = {height: [] for height in heights}

    # get all intersections
    for height, line in lines.items():
        _, found_paths = quadtree.get_intersections(line)
        for path in found_paths:
            try:
                path_intersections = path.intersect(line, tol=1e-12)
                for (T1, _, _), (_, _, _) in path_intersections:
                    height_intersections[height].append(complex(path.point(T1).real, height))
            except AssertionError as e:
                pass

    return height_intersections


def horizontal_lines(paths: List[ToolsPath], canvas_dimensions: Tuple[float, float], n_lines=100, angle=0):
    height_intersections = get_height_intersections(paths, canvas_dimensions, n_lines, angle)
    for height in sorted(height_intersections.keys()):
        path = ToolsPath()
        curr_intersections = sorted(height_intersections[height], key=lambda x: x.real)
        start = None
        for i in range(0, len(curr_intersections)):
            if i % 2 != 0 and i > 0:
                path.append(ToolsLine(start, curr_intersections[i]))
                yield path
                path = ToolsPath()
                continue

            start = curr_intersections[i]

        if len(path) > 0:
            yield path


def frange(start, stop=None, step=None):
    # if set start=0.0 and step = 1.0 if not specified
    start = float(start)
    if stop is None:
        stop = start + 0.0
        start = 0.0
    if step is None:
        step = 1.0

    count = 0
    while True:
        temp = float(start + count * step)
        if step > 0 and temp >= stop:
            break
        elif step < 0 and temp <= stop:
            break
        yield temp
        count += 1
