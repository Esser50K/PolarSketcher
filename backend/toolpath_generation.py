from svgpathtools import Path, Line
from dataclasses import dataclass


@dataclass
class Segment:
    def __init__(self, segment, path):
        self.segment = segment
        self.parent_path = path


def line_intersection(line1, line2) -> complex:
    xdiff = (line1[0][0] - line1[1][0], line2[0][0] - line2[1][0])
    ydiff = (line1[0][1] - line1[1][1], line2[0][1] - line2[1][1])

    def det(a, b):
        return a[0] * b[1] - a[1] * b[0]
    div = det(xdiff, ydiff)
    if div == 0:
        raise Exception('lines do not intersect')
    d = (det(*line1), det(*line2))
    x = det(d, xdiff) / div
    y = det(d, ydiff) / div
    return complex(x, y)


# getting intersections by linearizing path. SLOW.
def get_intersections_horizontal(line: Line, path: Path, step=.02) -> list[complex]:
    intersections = []
    line_start = line.point(0)
    line_end = line.point(1)
    line_height = line_start[1]

    min_y, max_y = path.bbox()[1], path.bbox()[3]
    if not (min_y < line_height < max_y):
        return []

    n_steps = int((path.length() / step)+.5)
    previous_point = path.point(0)
    for step_idx in range(1, n_steps):
        path_point = path.point(step_idx * step)
        if not (previous_point[1] < line_height < path_point[1] or
                previous_point[1] > line_height > path_point[1]):
            # if the line height is not between the height
            # of the other two points they don't intersect
            previous_point = path_point
            continue

        intersection = line_intersection((line_start, line_end), (previous_point, path_point))
        if not (0 < intersection.real < line.length()):
            continue

        intersections.append(complex(intersection.real, line_height))
        previous_point = path_point

    return intersections


def get_all_horizontal_intersections(lines: list[Line], path: Path, step=.02) -> dict[int, list[complex]]:
    intersections = {}
    n_steps = int((path.length() / step) + .5)
    previous_point = path.point(0)
    for step_idx in range(1, n_steps):
        path_point = path.point(step_idx * step)
        for line in lines:
            line_start = line.point(0)
            line_end = line.point(1)
            line_height = line_start[1]
            if line_height not in intersections.keys():
                intersections[line_height] = []

            min_y, max_y = path.bbox()[1], path.bbox()[3]
            if not (min_y < line_height < max_y):
                continue

            if not (previous_point[1] < line_height < path_point[1] or
                    previous_point[1] > line_height > path_point[1]):
                # if the line height is not between the height
                # of the other two points they don't intersect
                previous_point = path_point
                continue

            intersection = line_intersection((line_start, line_end), (previous_point, path_point))
            if not (0 < intersection.real < line.length()):
                continue

            intersections[line_height].append(intersection)
            previous_point = path_point

    return intersections


def get_horizontal_intersection_points(paths: list[Path], canvas_size: tuple[int, int], line_step, step=.02):
    canvas_width, canvas_height = canvas_size
    lines = {}
    intersections = {}
    heights = []
    max_intersections = 0

    # get all interactions
    for height in range(0, canvas_height, line_step):
        heights.append(height)
        intersections[height] = []
        lines[height] = Line(complex(0, height), complex(canvas_width, height))

        for path in paths:
            line_intersections = get_intersections_horizontal(lines[height], path, step)
            intersections[height].extend(line_intersections)
            if len(line_intersections) > max_intersections:
                max_intersections = len(line_intersections)

    return intersections


def horizontal_lines(paths: list[Path], canvas_dimensions: tuple, n_lines=100):
    canvas_width, canvas_height = canvas_dimensions
    line_step = canvas_height / n_lines

    heights = list(map(int, (frange(0, canvas_height, line_step))))
    lines = {height: Line(complex(0, height), complex(10000, height)) for height in heights}
    height_intersections = {height: [] for height in heights}

    # get all intersections
    for height, line in lines.items():
        for path in paths:
            try:
                path_intersections = path.intersect(line, tol=1e-12)
                for (T1, _, _), (_, _, _) in path_intersections:
                    height_intersections[height].append(complex(path.point(T1).real, height))
            except AssertionError as e:
                pass

    for height in sorted(height_intersections.keys()):
        path = Path()
        curr_intersections = sorted(height_intersections[height], key=lambda x: x.real)
        start = None
        for i in range(0, len(curr_intersections)):
            if i%2 != 0:
                path.append(Line(start, curr_intersections[i]))
                yield path
                path = Path()
                continue

            start = curr_intersections[i]

        if len(path._segments) > 0:
            yield path


def zigzag_lines(paths: list[Path], canvas_dimensions: tuple, n_lines=100):
    canvas_width, canvas_height = canvas_dimensions
    line_step = canvas_height / n_lines

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

    for nth_intersection in range(0, max_intersections-1, 2):
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

            if len(curr_intersections) <= nth_intersection+1:
                if len(path._segments) > 0:
                    yield path
                path = Path()
                last_point = None
                continue

            intersection2 = curr_intersections[nth_intersection+1]
            path.append(Line(last_point, intersection2))
            last_point = intersection2

        if len(path._segments) > 0:
            yield path


def rect_lines(paths: list[Path], canvas_dimensions: tuple, n_lines=100, diagonals=False):
    """
    this algorithm will fill in shapes with rectangular zigzag paths
    it will start a new path everytime a line changes in number of intersections
    this may results in having a lot of single horizontal lines since the previous paths
    will always be interrupted.
    """
    canvas_width, canvas_height = canvas_dimensions
    line_step = canvas_height / n_lines

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

    for nth_intersection in range(0, max_intersections-1, 2):
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

            first_point = nth_intersection if even else nth_intersection+1
            second_point = nth_intersection+1 if even else nth_intersection

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


def rect_lines2(paths: list[Path], canvas_dimensions: tuple, n_lines=100, diagonals=False):
    """
    this algorithm will fill in shapes with rectangular zigzag paths
    it first groups paths by parent and direct children (paths contained by other path)
    this will make the paths less interrupted than in rect_lines since the number of collisions
    should change less frequently. Although it still does happen for drawings that have many paths inside a single one.
    """
    canvas_width, canvas_height = canvas_dimensions
    line_step = canvas_height / n_lines

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
                            height_intersections[height].append((complex(path_segment.point(T1).real, height), path.d()))
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


def rect_lines3(paths: list[Path], canvas_dimensions: tuple, n_lines=100):
    """
    this algorithm will fill in shapes with rectangular zigzag paths
    it first groups paths by parent and direct children (paths contained by other path)
    then it generates all the paths in only one loop
    keeping track of which are currently still being generated and detects when new ones should be started
    this avoids any possibly unnecessary path interruption
    """
    canvas_width, canvas_height = canvas_dimensions
    line_step = canvas_height / n_lines

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
            except Exception as e:
                print("exc:", e)

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
    ongoing_paths = []
    for group in collision_groups:
        height_intersections = {height: [] for height in heights}

        # get all intersections
        for height, line in lines.items():
            for path_str in group:
                if paths_collided[path_str]:
                    continue

                # index 0 is always is the same path
                _, path = hierarchical_paths[path_str][0]
                try:
                    path_intersections = path.intersect(line, tol=1e-12)
                    for (T1, _, _), (_, _, _) in path_intersections:
                        height_intersections[height].append((complex(path.point(T1).real, height), T1, path))
                except AssertionError:
                    pass

            height_intersections[height] = sorted(height_intersections[height], key=lambda x: x[0].real)

            finished_paths = set()
            ongoing_paths_next_points = {}
            # continue ongoing paths
            for i in range(len(ongoing_paths)):
                path, last_point_in_path, last_collision_path, going_right = ongoing_paths[i]
                left = None
                right = None

                # find connection point along same path
                for j in range(len(height_intersections[height])):
                    point, point_in_path, collision_path = height_intersections[height][j]
                    if collision_path != last_collision_path:
                        continue

                    right_distance = point_in_path-last_point_in_path
                    if right_distance < 0:
                        right_distance = 1 + right_distance

                    left_distance = last_point_in_path-point_in_path
                    if left_distance < 0:
                        left_distance = 1 + left_distance

                    if right is None or left is None:
                        right = *height_intersections[height][j], right_distance, j
                        left = *height_intersections[height][j], left_distance, j
                        continue

                    # check if this point is closer than the previously found [-2] is the distance
                    if right_distance < right[-2]:
                        right = *height_intersections[height][j], right_distance, j

                    if left_distance < left[-2]:
                        left = *height_intersections[height][j], left_distance, j

                # if no more intersections left for this path then it is finished
                if (left is None and not going_right) or (right is None and going_right):
                    yield path
                    finished_paths.add(i)
                    continue

                # the point that the end of the last line will connect to
                connection_point = right if going_right else left
                # the continuation point on the other side will be be +1 or -1 on the height_intersections array
                connection_point_index = connection_point[-1]
                j = (connection_point_index + (1 if going_right else -1))
                if j < 0 or j >= len(height_intersections[height]):
                    continuation_point = None
                else:
                    point, point_in_path, collision_path = height_intersections[height][j]
                    distance = point_in_path-last_point_in_path if not going_right else last_point_in_path-point_in_path
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
                    if other_connection_point is None or ongoing_paths_idx == i:
                        continue

                    # compare points
                    if connection_point[0] == other_connection_point[0] or \
                       connection_point[0] == other_continuation_point[0]:
                        found = True

                    # dispute which path gets the intersection point, loser is set to finish
                    if connection_point[0] == other_connection_point[0]:
                        if connection_point[-2] < other_connection_point[-2]:
                            ongoing_paths_next_points[ongoing_paths_idx] = (None, None)
                            ongoing_paths_next_points[i] = (connection_point, continuation_point)
                        else:
                            ongoing_paths_next_points[i] = (None, None)
                        break
                    elif connection_point[0] == other_continuation_point[0]:
                        print(2)
                        if connection_point[-2] < other_connection_point[-2]:
                            print(2)
                            ongoing_paths_next_points[ongoing_paths_idx] = (None, None)
                            ongoing_paths_next_points[i] = (connection_point, continuation_point)
                        else:
                            ongoing_paths_next_points[i] = (None, None)
                        break

                if not found:
                    ongoing_paths_next_points[i] = (connection_point, continuation_point)

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
                    # quit if only one point remaining because it hit an
                    # edge intersection resulting in odd number of intersections
                    if i+1 >= len(height_intersections[height]):
                        break

                    point1, point_in_path1, collision_path1 = height_intersections[height][i]
                    point2, point_in_path2, collision_path2 = height_intersections[height][i+1]
                    print("points:", point1, point2)
                    ongoing_paths.append((Path(Line(point1, point2)), point_in_path2, collision_path2, False))
            except Exception as e:
                print("ERROR", e)
                print(len(height_intersections[height]))
                print(height_intersections[height])
                raise e


        for path_str in group:
            paths_collided[path_str] = True

    for path, _ in ongoing_paths:
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


def print_hashed(d):
    from pprint import pprint
    out = {}
    for k, v in d.items():
        out[hash(k)] = list(map(lambda x: [hash(x[0]), hash(x[1].d())], v))
    pprint(out)