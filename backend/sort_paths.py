from typing import Tuple, List

import math
from svgelements import Circle
from svgpathtools import Path


class ClosedPath:
    def __init__(self, path: Path, new_start: float = 0):
        self.path = path
        self.new_start = new_start

    def point(self, point: float):
        return self.path.point(math.fmod(point + self.new_start, 1))

    def length(self):
        return self.path.length()

    def bbox(self):
        return self.path.bbox()

    def rotated(self, rotation, origin):
        return self.path.rotated(rotation, origin)


def calc_distance(a: complex, b: complex) -> float:
    return math.sqrt(((a.real - b.real) ** 2) + ((a.imag - b.imag) ** 2))


def find_closest_path(last_point: complex, paths: List[Path], _: Tuple[float, float]) -> (Path, List[Path]):
    """
    finds closest path by checking distance of the start_point of paths
    """
    closest_distance = None
    closest_path = None
    closest_path_idx = 0
    for i in range(len(paths)):
        p = paths[i]
        start_point = p.point(0)
        if closest_path is None:
            closest_distance = calc_distance(last_point, start_point)
            closest_path = p
            continue

        start_point = p.point(0)
        distance = calc_distance(last_point, start_point)
        if distance < closest_distance:
            closest_distance = distance
            closest_path = p
            closest_path_idx = i

    return closest_path, (paths[:closest_path_idx] + paths[closest_path_idx + 1:])


def find_closest_path_with_endpoint(last_point: complex, paths: list[Path], _: tuple[int, int]) -> (Path, list[Path]):
    """
    finds closest path by checking distance of the start_point and end_point of paths
    if the endpoint is closer then the path is reversed
    """
    closest_distance = None
    closest_path = None
    closest_path_idx = 0
    for i in range(len(paths)):
        p = paths[i]
        start_point = p.point(0)
        end_point = p.point(1)
        if closest_path is None:
            start_dist = calc_distance(last_point, start_point)
            end_dist = calc_distance(last_point, end_point)
            closest_distance = min(start_dist, end_dist)
            if closest_distance != start_dist:
                p.reverse()
            closest_path = p
            continue

        start_dist = calc_distance(last_point, start_point)
        end_dist = calc_distance(last_point, end_point)
        distance = min(start_dist, end_dist)
        if distance < closest_distance:
            closest_distance = distance
            if closest_distance != start_dist:
                p.reverse()
            closest_path = p
            closest_path_idx = i

    return closest_path, (paths[:closest_path_idx] + paths[closest_path_idx + 1:])


def find_closest_point(last_point: complex, path: Path, step=.05) -> Tuple[float, float]:
    progress = 0.0
    closest_dist = None
    closest_point = 0
    while progress <= 1.0:
        point = path.point(progress)
        dist = calc_distance(last_point, point)
        if closest_dist is None:
            closest_dist = dist
            continue

        if dist < closest_dist:
            closest_dist = dist
            closest_point = progress

        progress += step

    return closest_point, closest_dist


def find_closest_path_with_circular_path_check(last_point: complex, paths: list[Path], _: tuple[int, int],
                                               step=.05) -> (Path, list[Path]):
    """
    finds closest path with same strategy as find_closest_path_with_endpoint
    additionally it checks for points inside of closed paths
    """
    closest_distance = None
    closest_path = None
    closest_path_idx = 0
    for i in range(len(paths)):
        p = paths[i]
        start_point = p.point(0)
        end_point = p.point(1)
        if closest_path is None:
            if p.isclosed():
                closest_point, closest_distance = find_closest_point(last_point, p, step=step)
                closest_path = ClosedPath(p, new_start=closest_point)
            else:
                start_dist = calc_distance(last_point, start_point)
                end_dist = calc_distance(last_point, end_point)
                closest_distance = min(start_dist, end_dist)
                if closest_distance != start_dist:
                    p.reverse()
                closest_path = p
            continue

        start_dist = calc_distance(last_point, start_point)
        end_dist = calc_distance(last_point, end_point)
        if p.isclosed():
            closest_point, distance = find_closest_point(last_point, p, step=step)
            if distance < closest_distance:
                closest_distance = distance
                closest_path = ClosedPath(p, new_start=closest_point)
                closest_path_idx = i
        else:
            distance = min(start_dist, end_dist)
            if distance < closest_distance:
                closest_distance = distance
                if closest_distance == start_dist:
                    p.reverse()
                closest_path = p
                closest_path_idx = i

    if closest_path is None:
        print("path is none:", len(paths))
    return closest_path, (paths[:closest_path_idx] + paths[closest_path_idx + 1:])


def inside(bbox, point: complex) -> bool:
    return bbox[0] < point.real < bbox[2] and \
           bbox[1] < point.imag < bbox[3]


def find_collision_point(radar: Circle, path: Path, step=.05) -> bool:
    progress = 0
    bbox = path.bbox()
    while progress <= 1.0:
        point = radar.point(progress)
        if inside(bbox, point):
            return True

        progress += step

    return False


def contains_rect(circle: Circle, size: tuple[int, int]) -> bool:
    width, height = size
    points = [complex(0, 0), complex(width, 0), complex(0, height), complex(width, height)]
    for point in points:
        if calc_distance(complex(circle.cx, circle.cy), point) > circle.rx:
            return False

    return True


# TODO can be improved on by checking if the intersected shape is closed
# and then finding the closest point within that path and start there
def find_closest_path_with_radar_scan(last_point: complex, paths: list[Path], size: tuple[int, int], radar_step=2,
                                      step=.05) -> (Path, list[Path]):
    """
    finds closest path by checking for intersections with
    circles that are generated by enlarging the radius
    """

    radius = radar_step
    radar_path = Circle(cx=last_point.real, cy=last_point.imag, rx=radius, ry=radius)
    while not contains_rect(radar_path, size):
        for i in range(len(paths)):
            p = paths[i]
            if find_collision_point(radar_path, p, step):
                return p, (paths[:i] + paths[i + 1:])

        radius += radar_step
        radar_path = Circle(cx=last_point.real, cy=last_point.imag, rx=radius, ry=radius)


def sort_paths(start_point: complex,
               paths: list[Path], canvas_size: Tuple[float, float],
               sorting_algo=find_closest_path) -> list[Path]:
    last_point = start_point
    while len(paths) != 0:
        path, paths = sorting_algo(last_point, paths, canvas_size)
        yield path

        last_point = path.point(1)


SORTING_ALGORITHMS = {
    "none": None,
    "simple": find_closest_path,
    "simple_variant1": find_closest_path_with_endpoint,
    "simple_variant2": find_closest_path_with_circular_path_check,
    "radar_scan": find_closest_path_with_radar_scan
}
