from collections import defaultdict
from typing import List, Tuple

from svgpathtools import Path, Line

from path_quadtree import SegmentIntersection
from .util import get_quadtree_height_intersections, get_brute_force_height_intersections


class PathInConstruction:
    def __init__(self,
                 path_in_construction: Path,
                 path_to_follow: Path,
                 point_in_path_to_follow: float,
                 direction_right=True):
        self.path: Path = path_in_construction
        self.path_to_follow = path_to_follow
        self.point_in_path_to_follow = point_in_path_to_follow
        self.direction_right = direction_right


def _continue_path(path_in_construction: PathInConstruction,
                   connection_intersection: SegmentIntersection,
                   continuation_intersection: SegmentIntersection,
                   zigzag: bool):
    connection_line = Line(path_in_construction.path.end,
                           connection_intersection.intersection_point)
    path_in_construction.path.append(connection_line)

    continuation_line = Line(connection_intersection.intersection_point,
                             continuation_intersection.intersection_point)
    path_in_construction.path.append(continuation_line)

    # update path in construction
    if not zigzag:
        path_in_construction.direction_right = not path_in_construction.direction_right
    path_in_construction.path_to_follow = continuation_intersection.segment.original_path
    path_in_construction.point_in_path_to_follow = continuation_intersection.point_in_original_path
    return path_in_construction


def _get_right_distance(path_in_construction: PathInConstruction,
                        intersection: SegmentIntersection) -> float:
    return abs(intersection.point_in_original_path - path_in_construction.point_in_path_to_follow)


def _get_left_distance(path_in_construction: PathInConstruction,
                       intersection: SegmentIntersection) -> float:
    return abs(path_in_construction.point_in_path_to_follow - intersection.point_in_original_path)


def _get_closest_intersection_pair(path_in_construction: PathInConstruction,
                                   intersection_pairs: List[Tuple[SegmentIntersection, SegmentIntersection]]
                                   ) -> Tuple[Tuple[SegmentIntersection, SegmentIntersection], int, float]:
    closest_intersection_pair_idx = -1
    closest_intersection_pair = tuple()
    distance_to_closest_intersection = 1
    for idx, (left_intersection, right_intersection) in enumerate(intersection_pairs):
        get_dist_func = _get_right_distance if path_in_construction.direction_right else _get_left_distance

        if left_intersection.segment.original_path == path_in_construction.path_to_follow:
            distance_to_left_intersection = get_dist_func(path_in_construction, left_intersection)

            if distance_to_left_intersection < distance_to_closest_intersection:
                distance_to_closest_intersection = distance_to_left_intersection
                closest_intersection_pair = (left_intersection, right_intersection)
                closest_intersection_pair_idx = idx

        if right_intersection.segment.original_path == path_in_construction.path_to_follow:
            distance_to_right_intersection = get_dist_func(path_in_construction, right_intersection)
            if distance_to_right_intersection < distance_to_closest_intersection:
                distance_to_closest_intersection = distance_to_right_intersection
                closest_intersection_pair = (left_intersection, right_intersection)
                closest_intersection_pair_idx = idx

    return closest_intersection_pair, closest_intersection_pair_idx, distance_to_closest_intersection


def _dispute_continuation(paths_in_construction: List[Tuple[PathInConstruction, float]]
                          ) -> Tuple[PathInConstruction, List[PathInConstruction]]:
    lowest_idx = 0
    lowest_distance = 1
    for idx, (path, distance) in enumerate(paths_in_construction):
        if distance < lowest_distance:
            lowest_distance = distance
            lowest_idx = idx

    finished_paths = list(map(lambda x: x[0],
                              paths_in_construction[:lowest_idx] + paths_in_construction[lowest_idx + 1:]))

    return paths_in_construction[lowest_idx][0], finished_paths


def _continue_paths_in_construction(paths_in_construction: List[PathInConstruction],
                                    intersection_pairs: List[Tuple[SegmentIntersection, SegmentIntersection]],
                                    zigzag: bool) -> \
        Tuple[
            List[PathInConstruction],
            List[Tuple[SegmentIntersection, SegmentIntersection]]]:
    intersection_pair_to_paths = defaultdict(list)
    finished_paths_in_construction = []
    for path_in_construction in paths_in_construction:
        closest_continuation_pair, intersection_pair_idx, distance = \
            _get_closest_intersection_pair(path_in_construction, intersection_pairs)

        # if a continuation for a path in construction has been found
        # that intersection pair needs to be removed from the candidates
        # for the other paths in construction
        if intersection_pair_idx != -1:
            # map the path in construction with its closest continuation intersection pair
            intersection_pair_to_paths[intersection_pair_idx].append((path_in_construction, distance))

        # if nothing has been found this means that the path is done and can be yielded
        else:
            finished_paths_in_construction.append(path_in_construction)

    # for all intersection_pairs where there is more than one path_in_construction to connect to
    # dispute which one will continue and which will have to be finished (currently the closest path wins)
    intersection_pairs_to_remove = []
    for intersection_pair_idx, path_in_construction_list in intersection_pair_to_paths.items():
        path_to_continue, finished_paths = _dispute_continuation(path_in_construction_list)
        closest_continuation_pair = intersection_pairs[intersection_pair_idx]

        finished_paths_in_construction.extend(finished_paths)
        intersection_pairs_to_remove.append(intersection_pairs[intersection_pair_idx])

        connection_intersection = closest_continuation_pair[1] \
            if path_to_continue.direction_right else closest_continuation_pair[0]
        continuation_intersection = closest_continuation_pair[0] \
            if path_to_continue.direction_right else closest_continuation_pair[1]

        _continue_path(path_to_continue,
                       connection_intersection,
                       continuation_intersection,
                       zigzag=zigzag)

    # cleanup used intersection pairs
    for intersection_pair in intersection_pairs_to_remove:
        intersection_pairs.remove(intersection_pair)

    # returns the finished paths ready to be yielded and
    # the remaining intersection pairs for new paths
    return finished_paths_in_construction, intersection_pairs


def connecting_lines(paths: list[Path],
                     canvas_dimensions: Tuple[int, int],
                     n_lines=100, angle=0,
                     use_quadtree=True,
                     zigzag=True):
    get_height_intersection_func = get_quadtree_height_intersections \
        if use_quadtree else get_brute_force_height_intersections
    height_intersections = get_height_intersection_func(paths,
                                                        canvas_dimensions,
                                                        n_lines, angle)

    paths_in_construction = []
    for height in sorted(height_intersections.keys()):
        sorted_height_intersections = sorted(height_intersections[height], key=lambda x: x.intersection_point.real)

        # HACK: duplicate initial intersection if it hits a vertice
        if len(sorted_height_intersections) == 1:
            sorted_height_intersections.append(sorted_height_intersections[0])

        intersection_pairs = []
        for i in range(0, len(sorted_height_intersections), 2):
            try:
                intersection_pairs.append((sorted_height_intersections[i], sorted_height_intersections[i + 1]))
            except Exception as e:
                print("error while creating intersection pairs:", e)
                print(i, len(sorted_height_intersections))
                pass

        finished_paths_in_construction, remaining_intersection_pairs = _continue_paths_in_construction(
            paths_in_construction, intersection_pairs, zigzag=zigzag)

        # yield the finished paths
        for path_in_construction in finished_paths_in_construction:
            yield path_in_construction.path
            paths_in_construction.remove(path_in_construction)

        for left, right in remaining_intersection_pairs:
            new_path = Path(Line(left.intersection_point, right.intersection_point))
            paths_in_construction.append(PathInConstruction(
                new_path,
                right.segment.original_path,
                right.point_in_original_path,
                direction_right=not zigzag
            ))

    # flush out the last ones
    for path_in_construction in paths_in_construction:
        yield path_in_construction.path


def rect_lines(paths: list[Path],
               canvas_dimensions: Tuple[int, int],
               n_lines=100,
               angle=0,
               use_quadtree=True):
    return connecting_lines(paths, canvas_dimensions, n_lines, angle, use_quadtree, zigzag=False)


def zigzag_lines(paths: list[Path],
                 canvas_dimensions: Tuple[int, int],
                 n_lines=100,
                 angle=0,
                 use_quadtree=True):
    return connecting_lines(paths, canvas_dimensions, n_lines, angle, use_quadtree, zigzag=True)
