from typing import List, Tuple, Dict

from svgpathtools import Path, Line

from path_quadtree import QuadTree, Point, Rect, SegmentIntersection, PathSegment


def get_quadtree_height_intersections(paths: List[Path],
                                      canvas_dimensions: Tuple[float, float],
                                      line_step=10,
                                      angle=0) -> Dict[float, List[SegmentIntersection]]:
    # exaggerating dimensions of quadtree in order to catch rotated paths that end up outside the canvas
    quadtree = QuadTree(
        Rect(
            Point(complex(-canvas_dimensions[0]
                  * 2, -canvas_dimensions[1] * 2)),
            canvas_dimensions[0] * 4, canvas_dimensions[1] * 4),
        capacity=20)

    canvas_width, canvas_height = canvas_dimensions
    # line_step = int((canvas_height / n_lines) + .5)
    for path in paths:
        quadtree.insert_path(path.rotated(
            angle, complex(canvas_width / 2, canvas_height / 2)))

    heights = list(range(-int(canvas_height) * 2,
                   int(canvas_height) * 2, line_step))
    lines = {height: Path(Line(complex(-canvas_width, height), complex(canvas_width * 2, height))) for height in
             heights}
    height_intersections = {height: [] for height in heights}

    # get all intersections
    for height, line in lines.items():
        intersections = quadtree.get_intersections(line)
        for intersection in intersections:
            height_intersections[height].append(intersection)

    return height_intersections


def get_brute_force_height_intersections(paths: List[Path],
                                         canvas_dimensions: Tuple[int, int],
                                         line_step=10,
                                         angle=0) -> Dict[float, List[SegmentIntersection]]:
    canvas_width, canvas_height = canvas_dimensions
    # line_step = int((canvas_height / n_lines) + .5)
    paths = [path.rotated(angle, complex(
        canvas_width / 2, canvas_height / 2)) for path in paths]

    heights = list(range(-int(canvas_height) * 2,
                   int(canvas_height) * 2, line_step))
    lines = {height: Path(Line(complex(-canvas_width, height), complex(canvas_width * 2, height))) for height in
             heights}
    height_intersections = {height: [] for height in heights}

    # get all intersections
    for height, line in lines.items():
        for path in paths:
            try:
                path_intersections = path.intersect(line, tol=1e-12)
                for (T1, seg1, t1), (_T2, _seg2, _t2) in path_intersections:
                    intersection_point = path.point(T1)
                    height_intersections[height].append(SegmentIntersection(intersection_point,
                                                                            point_in_path=t1,
                                                                            point_in_original_path=T1,
                                                                            segment=PathSegment(
                                                                                segment=seg1,
                                                                                original_path=path
                                                                            )))
            except Exception as e:
                print("An error occurred trying to get an intersection:", e)
                print("Path D:", path.d())
                print("Collision Path D:", line.d())

    return height_intersections
