import time

import math
from svgelements import Circle, Rect
from svgpathtools import Path, Line


def circle(cx: float, cy: float, radius: float) -> Path:
    return Path(Circle(cx, cy, radius).d())


def rect(cx: float, cy: float, width: float, height: float) -> Path:
    return Path(Rect(cx, cy, width, height).d())


class SubPath:
    def __init__(self, path: Path, t1: float, t2: float):
        self.t1 = t1
        self.t2 = t2
        self.path = path

    def point(self, point: float):
        t = (self.t2 - self.t1) * point
        return self.path.point(t)

    def length(self):
        return self.path.length()

    def rotated(self, degs, origin=(0, 0)):
        return self.path.rotated(degs, origin)

    # def __getattr__(self, attr):
    #     return getattr(self.path, attr)

    # def __setattr__(self, name, value):
    #     return setattr(self.path, name, value)


def horizontal_lines(paths: list[Path], canvas_dimensions: tuple[float, float], n_lines=100, angle=0):
    canvas_width, canvas_height = canvas_dimensions
    line_step = canvas_height / n_lines
    paths = [path.rotated(angle, complex(canvas_width / 2, canvas_height / 2)) for path in paths]

    heights = list(map(int, (frange(0, canvas_height, line_step))))
    lines = {height: Line(complex(-10000, height), complex(10000, height)) for height in heights}
    height_intersections = {height: [] for height in heights}

    start = time.time()
    # get all intersections
    for height, line in lines.items():
        for path in paths:
            try:
                path_intersections = path.intersect(line, tol=1e-12)
                for (T1, _, _), (_, _, _) in path_intersections:
                    height_intersections[height].append(complex(path.point(T1).real, height))
            except AssertionError as e:
                pass

    total_time = time.time() - start
    print("TOTAL TIME TO FIND INTERSECTIONS WAS:", total_time, "ms")

    for height in sorted(height_intersections.keys()):
        path = Path()
        curr_intersections = sorted(height_intersections[height], key=lambda x: x.real)
        start = None
        for i in range(0, len(curr_intersections)):
            if i % 2 != 0 and i > 0:
                path.append(Line(start, curr_intersections[i]))
                yield path
                path = Path()
                continue

            start = curr_intersections[i]

        if len(path._segments) > 0:
            yield path


def circular_lines(paths: list[Path], canvas_dimensions: tuple[float, float], n_lines=100, angle=0):
    canvas_width, canvas_height = canvas_dimensions
    # add canvas rect so that circles can start only within the canvas
    paths.append(rect(0, 0, canvas_width, canvas_height))
    paths = [path.rotated(angle, complex(canvas_width / 2, canvas_height / 2)) for path in paths]

    max_radius = math.sqrt((canvas_width ** 2) + (canvas_height ** 2))
    line_step = max_radius / n_lines
    radiuses = list(map(int, (frange(0, max_radius, line_step))))
    circles = {radius: circle(0, 0, radius) for radius in radiuses}
    radius_intersections = {radius: [] for radius in radiuses}

    # get all intersections
    for radius, circle_path in circles.items():
        for path in paths:
            try:
                path_intersections = circle_path.intersect(path, tol=1e-12)
                for (T1, _, _), (_, _, _) in path_intersections:
                    radius_intersections[radius].append((T1, circle_path))
            except AssertionError as e:
                pass

    for radius in sorted(radius_intersections.keys()):
        if len(radius_intersections[radius]) == 0:
            continue

        circle_path = radius_intersections[radius][0][1]
        curr_intersections = sorted(radius_intersections[radius], key=lambda x: x[0])
        for i in range(0, len(curr_intersections) - 1):
            if i % 2 != 0:
                yield SubPath(circle_path, curr_intersections[i], curr_intersections[i + 1])


def zigzag_lines(paths: list[Path], canvas_dimensions: tuple, n_lines=100, angle=0):
    canvas_width, canvas_height = canvas_dimensions
    line_step = canvas_height / n_lines
    paths = [path.rotated(angle, complex(canvas_width / 2, canvas_height / 2)) for path in paths]

    heights = list(map(int, (frange(0, canvas_height, line_step))))
    lines = {height: Line(complex(0, height), complex(10000, height)) for height in heights}
    height_intersections = {height: [] for height in heights}
    max_intersections = 0

    # get all intersections
    for height, line in lines.items():
        for path in paths:
            try:
                path_intersections = path.intersect(line)
                for (T1, _, _), (_, _, _) in path_intersections:
                    height_intersections[height].append((complex(path.point(T1).real, height), path.d()))
            except AssertionError as e:
                pass

    for height, intersections in height_intersections.items():
        height_intersections[height] = sorted(height_intersections[height], key=lambda x: x[0].real)
        if len(height_intersections[height]) > max_intersections:
            max_intersections = len(height_intersections[height])

    for nth_intersection in range(0, max_intersections - 1, 2):
        path = Path()
        last_point = None
        last_line_intersection_paths = []
        for height in sorted(height_intersections.keys()):
            curr_intersections = []
            curr_intersection_paths = []
            for intersection, intersection_path in height_intersections[height]:
                curr_intersections.append(intersection)
                curr_intersection_paths.append(intersection_path)

            if last_line_intersection_paths != curr_intersection_paths:
                if len(path._segments) > 0:
                    yield path
                path = Path()
                last_point = None
            last_line_intersection_paths = curr_intersection_paths

            if len(curr_intersections) <= nth_intersection:
                if len(path._segments) > 0:
                    yield path
                path = Path()
                last_point = None
                continue

            intersection1 = curr_intersections[nth_intersection]
            if last_point is not None:
                path.append(Line(last_point, intersection1))
            last_point = intersection1

            if len(curr_intersections) <= nth_intersection + 1:
                if len(path._segments) > 0:
                    yield path
                path = Path()
                last_point = None
                continue

            intersection2 = curr_intersections[nth_intersection + 1]
            path.append(Line(last_point, intersection2))
            last_point = intersection2

        if len(path._segments) > 0:
            yield path


def rect_lines(paths: list[Path], canvas_dimensions: tuple, n_lines=100, angle=0, diagonals=False):
    """
    this algorithm will fill in shapes with rectangular zigzag paths
    it will start a new path everytime a line changes in number of intersections
    this may results in having a lot of single horizontal lines since the previous paths
    will always be interrupted.
    """
    canvas_width, canvas_height = canvas_dimensions
    line_step = canvas_height / n_lines
    paths = [path.rotated(angle, complex(canvas_width / 2, canvas_height / 2)) for path in paths]

    heights = list(map(int, (frange(0, canvas_height, line_step))))
    lines = {height: Line(complex(0, height), complex(10000, height)) for height in heights}
    height_intersections = {height: [] for height in heights}
    max_intersections = 0

    # get all intersections
    for height, line in lines.items():
        for path in paths:
            try:
                path_intersections = path.intersect(line)
                for (T1, _, _), (_, _, _) in path_intersections:
                    height_intersections[height].append((complex(path.point(T1).real, height), path.d()))
            except AssertionError as e:
                pass

    for height, intersections in height_intersections.items():
        height_intersections[height] = sorted(height_intersections[height], key=lambda x: x[0].real)
        if len(height_intersections[height]) > max_intersections:
            max_intersections = len(height_intersections[height])

    for nth_intersection in range(0, max_intersections - 1, 2):
        even = False
        path = Path()
        last_point = None
        last_line_intersection_paths = []
        for height in sorted(height_intersections.keys()):
            if not diagonals:
                even = not even
            curr_intersections = []
            curr_intersection_paths = []
            for intersection, intersection_path in height_intersections[height]:
                curr_intersections.append(intersection)
                curr_intersection_paths.append(intersection_path)

            if last_line_intersection_paths != curr_intersection_paths:
                if len(path._segments) > 0:
                    yield path
                path = Path()
                last_point = None
            last_line_intersection_paths = curr_intersection_paths

            first_point = nth_intersection if even else nth_intersection + 1
            second_point = nth_intersection + 1 if even else nth_intersection

            if len(curr_intersections) <= first_point:
                if len(path._segments) > 0:
                    yield path
                path = Path()
                last_point = None
                continue

            intersection1 = curr_intersections[first_point]
            if last_point is not None:
                path.append(Line(last_point, intersection1))
            last_point = intersection1

            if len(curr_intersections) <= second_point:
                if len(path._segments) > 0:
                    yield path
                path = Path()
                last_point = None
                continue

            intersection2 = curr_intersections[second_point]
            path.append(Line(last_point, intersection2))
            last_point = intersection2

        if len(path._segments) > 0:
            yield path


def get_hierarchy(paths: list[Path]):
    paths_copy = [path for path in paths]
    hierarchical_paths = {path.d(): [[path.d(), path]] for path in paths}
    # get all the parent child relationships
    while len(paths_copy) > 0:
        path1 = paths_copy[0]
        paths_copy = paths_copy[1:]
        for path2 in paths_copy:
            try:
                if path2.is_contained_by(path1):
                    hierarchical_paths[path1.d()].append([path2.d(), path2])
                elif path1.is_contained_by(path2):
                    hierarchical_paths[path2.d()].append([path1.d(), path1])
            except AssertionError:
                pass
    return hierarchical_paths


def check_collision_paths(last_line_paths, current_line_paths, idx):
    if idx >= len(last_line_paths) or idx >= len(current_line_paths):
        return False

    return last_line_paths[idx] != current_line_paths[idx]


def rect_lines2(paths: list[Path], canvas_dimensions: tuple, n_lines=100, angle=0, diagonals=False):
    """
    this algorithm will fill in shapes with rectangular zigzag paths
    it first groups paths by parent and direct children (paths contained by other path)
    this will make the paths less interrupted than in rect_lines since the number of collisions
    should change less frequently. Although it still does happen for drawings that have many paths inside a single one.
    """
    canvas_width, canvas_height = canvas_dimensions
    line_step = canvas_height / n_lines
    paths = [path.rotated(angle, complex(canvas_width / 2, canvas_height / 2)) for path in paths]

    heights = list(map(int, (frange(0, canvas_height, line_step))))
    lines = {height: Line(complex(0, height), complex(10000, height)) for height in heights}

    paths_copy = [path for path in paths]
    hierarchical_paths = {path.d(): [[path.d(), path]] for path in paths}

    # get all the parent child relationships
    while len(paths_copy) > 0:
        path1 = paths_copy[0]
        paths_copy = paths_copy[1:]

        for path2 in paths_copy:
            try:
                if path2.is_contained_by(path1):
                    hierarchical_paths[path1.d()].append([path2.d(), path2])
                elif path1.is_contained_by(path2):
                    hierarchical_paths[path2.d()].append([path1.d(), path1])
            except AssertionError:
                pass

    # this is to check if the paths for previously used already
    paths_collided = {path.d(): False for path in paths}
    # sorting paths by the ones that hold the most
    sorted_paths = sorted([(path, children) for path, children in hierarchical_paths.items()],
                          key=lambda path_children: len(path_children[1]),
                          reverse=True)

    # find only direct children to collide with
    collision_groups = []
    for path_str, children in sorted_paths:
        direct_children = set([path_id for path_id, _ in children])
        paths_collided[path_str] = True
        for child_str, child in children:
            if child_str == path_str:
                continue

            for grandchild_str, _ in hierarchical_paths[child_str]:
                if paths_collided[grandchild_str]:
                    continue

                if grandchild_str == child_str:
                    continue

                try:
                    direct_children.remove(grandchild_str)
                    paths_collided[grandchild_str] = True
                except KeyError:
                    pass

        collision_groups.append(direct_children)

    paths_collided = {path.d(): False for path in paths}
    for group in collision_groups:
        height_intersections = {height: [] for height in heights}
        max_intersections = 0

        # get all intersections
        for height, line in lines.items():
            for path_str in group:
                if paths_collided[path_str]:
                    continue

                # index 0 is always is the same path
                _, path = hierarchical_paths[path_str][0]
                for segment in path:
                    try:
                        path_segment = Path(segment)
                        path_intersections = path_segment.intersect(line, tol=1e-12)
                        for (T1, _, _), (_, _, _) in path_intersections:
                            height_intersections[height].append(
                                (complex(path_segment.point(T1).real, height), path.d()))
                    except AssertionError as e:
                        pass

        for height, intersections in height_intersections.items():
            height_intersections[height] = sorted(height_intersections[height], key=lambda x: x[0].real)
            if len(height_intersections[height]) > max_intersections:
                max_intersections = len(height_intersections[height])

        for nth_intersection in range(0, max_intersections - 1, 2):
            even = False
            path = Path()
            last_point = None
            last_line_intersection_paths = []
            for height in sorted(height_intersections.keys()):
                if not diagonals:
                    even = not even
                curr_intersections = []
                curr_intersection_paths = []
                for intersection, intersection_path in height_intersections[height]:
                    curr_intersections.append(intersection)
                    curr_intersection_paths.append(intersection_path)

                if last_line_intersection_paths != curr_intersection_paths:
                    if len(path._segments) > 0:
                        yield path
                    path = Path()
                    last_point = None
                last_line_intersection_paths = curr_intersection_paths

                first_point = nth_intersection if even else nth_intersection + 1
                second_point = nth_intersection + 1 if even else nth_intersection

                if len(curr_intersections) <= first_point:
                    if len(path._segments) > 0:
                        yield path
                    path = Path()
                    last_point = None
                    continue

                intersection1 = curr_intersections[first_point]
                if last_point is not None:
                    path.append(Line(last_point, intersection1))
                last_point = intersection1

                if len(curr_intersections) <= second_point:
                    if len(path._segments) > 0:
                        yield path
                    path = Path()
                    last_point = None
                    continue

                intersection2 = curr_intersections[second_point]
                path.append(Line(last_point, intersection2))
                last_point = intersection2

            if len(path._segments) > 0:
                yield path

        for path_str in group:
            paths_collided[path_str] = True


def rect_lines3(paths: list[Path], canvas_dimensions: tuple, n_lines=100, angle=0):
    """
    this algorithm will fill in shapes with rectangular zigzag paths
    it first groups paths by parent and direct children (paths contained by other path)
    then it generates all the paths in only one loop
    keeping track of which are currently still being generated and detects when new ones should be started
    this avoids any possibly unnecessary path interruption
    """
    canvas_width, canvas_height = canvas_dimensions
    line_step = canvas_height / n_lines
    paths = [path.rotated(angle, complex(canvas_width / 2, canvas_height / 2)) for path in paths]

    # using more area than the canvas has because some paths go out of the canvas after being rotated
    # they should be considered for all the calculations even if they aren't drawn
    heights = list(map(int, (frange(-canvas_height / 2, canvas_height + canvas_height / 2, line_step))))
    lines = {height: Line(complex(0, height), complex(10000, height)) for height in heights}

    hierarchical_paths = get_parent_child_paths_map(paths)
    collision_groups = get_direct_parent_child_paths(hierarchical_paths)

    paths_collided = {path.d(): False for path in paths}
    ongoing_paths = []
    for group in collision_groups:
        height_intersections = {}

        # get all intersections for current group at this height
        for height, line in lines.items():
            # intersection = point, point_in_path, path
            height_intersections[height] = get_even_path_intersections(line, group, hierarchical_paths, paths_collided)

            finished_paths = set()
            ongoing_paths_next_points = {}
            # continue ongoing paths
            for i in range(len(ongoing_paths)):
                path, last_point_in_path, last_collision_path, going_right = ongoing_paths[i]

                # the point that the end of the last line of the ongoing path will connect to
                connection_point = get_connection_point(ongoing_paths[i], height_intersections[height])

                # if no more intersections left for this path then it is finished
                if connection_point is None:
                    yield path
                    finished_paths.add(i)
                    continue

                # the continuation point on the other side will be be +1 or -1 on the height_intersections array
                # -1 is the intersection_idx
                connection_point_index = connection_point[-1]
                j = (connection_point_index + (1 if going_right else -1))
                continuation_point = None

                # if it is out of bounds there is no continuation point
                if j > 0 and j < len(height_intersections[height]):
                    point, point_in_path, collision_path = height_intersections[height][j]
                    distance = point_in_path - last_point_in_path if not going_right else last_point_in_path - point_in_path
                    if distance < 0:
                        distance = 1 + distance
                    continuation_point = *height_intersections[height][j], distance, j

                # check if other ongoing paths chose the same points
                # the one that is closest wins
                found = False
                for ongoing_paths_idx, next_points in ongoing_paths_next_points.items():
                    other_connection_point, other_continuation_point = next_points
                    # check if already kicked out or if it's the same path
                    # do not check if continuation point is None because that is valid
                    if other_connection_point is None or \
                            ongoing_paths_idx == i:
                        continue

                    # compare points
                    if connection_point[0] == other_connection_point[0] or \
                            (other_continuation_point and connection_point[0] == other_continuation_point[0]):
                        found = True

                    # dispute which path gets the intersection point, loser is set to finish
                    if connection_point[0] == other_connection_point[0]:
                        # idx -2 is the distance ot the previous point in the respective path
                        if connection_point[-2] < other_connection_point[-2]:
                            ongoing_paths_next_points[ongoing_paths_idx] = (None, None)
                            ongoing_paths_next_points[i] = (connection_point, continuation_point)
                        else:
                            ongoing_paths_next_points[i] = (None, None)
                        break
                    elif other_continuation_point and connection_point[0] == other_continuation_point[0]:
                        # idx -2 is the distance ot the previous point in the respective path
                        if connection_point[-2] < other_connection_point[-2]:
                            ongoing_paths_next_points[ongoing_paths_idx] = (None, None)
                            ongoing_paths_next_points[i] = (connection_point, continuation_point)
                        else:
                            ongoing_paths_next_points[i] = (None, None)
                        break

                # nothing to dispute, path keeps going
                if not found:
                    ongoing_paths_next_points[i] = (connection_point, continuation_point)

            # add the next points to the ongoing paths
            all_connection_and_continuation_points = set()
            for ongoing_paths_idx, (connection_point, continuation_point) in ongoing_paths_next_points.items():
                if connection_point is None:
                    yield ongoing_paths[ongoing_paths_idx][0]
                    finished_paths.add(ongoing_paths_idx)
                    continue

                all_connection_and_continuation_points.add(connection_point[0])
                if continuation_point is not None:
                    all_connection_and_continuation_points.add(continuation_point[0])

                path, last_point_in_path, last_collision_path, going_right = ongoing_paths[ongoing_paths_idx]

                connection_line = Line(path.point(1), connection_point[0])
                path.append(connection_line)
                # the path might have a connection point and not have a continuation point
                if continuation_point is None:
                    yield path
                    finished_paths.add(ongoing_paths_idx)
                    continue

                continuation_line = Line(connection_point[0], continuation_point[0])
                path.append(continuation_line)
                ongoing_paths[ongoing_paths_idx] = (path,
                                                    continuation_point[1],  # point in collision path
                                                    continuation_point[2],  # collision path
                                                    not going_right)

            # remove the already used intersections and start new paths with the rest
            height_intersections[height] = [height_intersection for height_intersection in height_intersections[height]
                                            if height_intersection[0] not in all_connection_and_continuation_points]

            # filter out finished paths
            ongoing_paths = [ongoing_paths[i] for i in range(len(ongoing_paths)) if i not in finished_paths]

            try:
                # start new paths with the remaining intersection pairs
                for i in range(0, len(height_intersections[height]), 2):
                    point1, point_in_path1, collision_path1 = height_intersections[height][i]
                    point2, point_in_path2, collision_path2 = height_intersections[height][i + 1]
                    ongoing_paths.append((Path(Line(point1, point2)), point_in_path2, collision_path2, False))
            except Exception as e:
                print("error trying to create new paths", e)
                raise e

        for path_str in group:
            paths_collided[path_str] = True

    for ongoing_path in ongoing_paths:
        yield ongoing_path[0]


# returns a map where the key is a path string
# and the value is a list of paths that are contained within that path
def get_parent_child_paths_map(paths: [Path]) -> dict[str, list[str, Path]]:
    paths_copy = [path for path in paths]
    path_hierarchy = {path.d(): [[path.d(), path]] for path in paths}
    while len(paths_copy) > 0:
        path1 = paths_copy[0]
        paths_copy = paths_copy[1:]

        for path2 in paths_copy:
            try:
                if path2.is_contained_by(path1):
                    path_hierarchy[path1.d()].append([path2.d(), path2])
                elif path1.is_contained_by(path2):
                    path_hierarchy[path2.d()].append([path1.d(), path1])
            except AssertionError:
                pass
            except Exception as e:
                print("unexpected error calculating hierarchy:", e)

    return path_hierarchy


# filters out the non direct children from the parent children hierarchy
# useful for when calculating infill algorithms
def get_direct_parent_child_paths(hierarchical_paths: dict[str, list[str, Path]]) -> list[set[str]]:
    # sorting paths by the ones that hold the most
    sorted_paths = sorted([(path_str, children) for path_str, children in hierarchical_paths.items()],
                          key=lambda path_children: len(path_children[1]),
                          reverse=True)

    # find only direct children to collide with
    collision_groups = []
    for path_str, children in sorted_paths:
        # the first path in the children is actually
        # the parent path so that one is included too
        direct_children = set([path_str for path_str, _ in children])

        # the first one id always the same path as the current key
        # so we can skip it
        for child_str, child in children[1:]:
            for grandchild_str, _ in hierarchical_paths[child_str][1:]:
                # remove all the children the grandchildren
                # from our direct children set
                try:
                    direct_children.remove(grandchild_str)
                except KeyError:
                    pass

        collision_groups.append(direct_children)

    return collision_groups


def get_even_path_intersections(
        intersection_line: Line,
        collision_group: set[str],
        hierarchical_paths: dict[str, list[str, Path]],
        paths_collided: dict[str, bool]) -> list[tuple[complex, float, Path]]:
    # in case the actual line hits and odd number of
    # intersections we repeat the process with the line slightly shifted
    original_height = intersection_line.start.imag
    intersections = []
    while True:
        for path_str in collision_group:
            if paths_collided[path_str]:
                continue

            # index 0 is always is the same path
            _, path = hierarchical_paths[path_str][0]
            try:
                path_intersections = path.intersect(intersection_line, tol=1e-12)
                for (T1, _, _), (_, _, _) in path_intersections:
                    intersections.append((complex(path.point(T1).real, original_height), T1, path))
            except AssertionError:
                pass

        # if we found an even number of intersections we good
        if len(intersections) % 2 == 0:
            break

        # slightly shift line down to avoid hitting edges
        # so that the total number of collisions is even
        intersection_line = intersection_line.translated(complex(0, -1))
        intersections = []

    return sorted(intersections, key=lambda x: x[0].real)


def get_connection_point(
        ongoing_path: tuple[Path, float, Path, bool],
        height_intersections: list[tuple[complex, float, Path]]) \
        -> tuple[complex, float, Path, float, int]:
    path, last_point_in_path, last_collision_path, going_right = ongoing_path
    # closest_intersection_point = *height_intersection, distance, intersection_idx
    closest_intersection_point_left = None
    closest_intersection_point_right = None

    # find connection point along same path
    for j in range(len(height_intersections)):
        intersection_idx = j
        point, point_in_path, collision_path = height_intersections[intersection_idx]
        # connection point must be along the same path
        if collision_path != last_collision_path:
            continue

        # point_in_path is a value between 0 and 1 representing
        # a point within that path

        right_distance = point_in_path - last_point_in_path
        if right_distance < 0:
            right_distance = 1 + right_distance

        left_distance = last_point_in_path - point_in_path
        if left_distance < 0:
            left_distance = 1 + left_distance

        # set initial left and right points
        # depending on which direction the path is moving a
        # connection point is chosen, the other one will be the continuation point
        if closest_intersection_point_right is None or closest_intersection_point_left is None:
            closest_intersection_point_right = *height_intersections[intersection_idx], \
                                               right_distance, intersection_idx
            closest_intersection_point_left = *height_intersections[intersection_idx], \
                                              left_distance, intersection_idx
            continue

        # check if this point is closer than the previously found [-2] is the distance
        if right_distance < closest_intersection_point_right[-2]:
            closest_intersection_point_right = *height_intersections[j], right_distance, j

        if left_distance < closest_intersection_point_left[-2]:
            closest_intersection_point_left = *height_intersections[j], left_distance, j

    # if no more intersections left for this path then it is finished
    if (closest_intersection_point_left is None and not going_right) or (
            closest_intersection_point_right is None and going_right):
        return None

    # the point that the end of the last line will connect to
    return closest_intersection_point_right if going_right else closest_intersection_point_left


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


def print_hashed(d):
    from pprint import pprint
    out = {}
    for k, v in d.items():
        out[hash(k)] = list(map(lambda x: [hash(x[0]), hash(x[1].d())], v))
    pprint(out)


TOOLPATHS = {
    "none": None,
    "lines": horizontal_lines,
    # "lines": circular_lines,
    "zigzag": zigzag_lines,
    "rectlines": rect_lines
}
