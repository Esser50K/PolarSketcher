from typing import List, Tuple

from svgpathtools import Path, Line

from .util import get_quadtree_height_intersections, get_brute_force_height_intersections


def horizontal_lines(paths: List[Path],
                     canvas_dimensions: Tuple[float, float],
                     n_lines=100,
                     angle=0,
                     use_quadtree=True):
    get_height_intersection_func = get_quadtree_height_intersections \
        if use_quadtree else get_brute_force_height_intersections
    height_intersections = get_height_intersection_func(paths,
                                                        canvas_dimensions,
                                                        n_lines, angle)

    for height in sorted(height_intersections.keys()):
        path = Path()
        curr_intersections = sorted(height_intersections[height], key=lambda x: x.real)
        start = None
        for i in range(0, len(curr_intersections)):
            if i % 2 != 0:
                path.append(Line(start, curr_intersections[i]))
                yield path
                path = Path()
                continue

            start = curr_intersections[i]

        if len(path._segments) > 0:
            yield path
