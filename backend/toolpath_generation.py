from svgpathtools import Path, Line

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
                path_intersections = path.intersect(line)
                for (T1, _, _), (_, _, _) in path_intersections:
                    height_intersections[height].append(complex(path.point(T1).real, height))
            except AssertionError as e:
                print("failed to find intersection:", e)
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
                print("failed to find intersection:", e)
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


def rect_lines(paths: list[Path], canvas_dimensions: tuple, n_lines=100):
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
                print("failed to find intersection:", e)
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