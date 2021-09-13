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


# optimized function to get intersection points of a path and a horizontal line
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

        #print("adding point", intersection)
        intersections.append(complex(intersection.real, line_height))
        previous_point = path_point

        """
        # calculate slope
        slope = (path_point[1] - previous_point[1]) / (path_point[0] - previous_point[0])

        if slope == 0:
            # lines are parallel and don't overlap
            previous_point = path_point
            print("SLOPE 0")
            continue

        # calculate intersection with line formula: (y - y1) = slope*(x - x1)
        b = -(slope*path_point[0])+path_point[1]
        x = (line_height - b) / slope
        # point is out of canvas
        if not (0 < x < line.length()):
            print("out of canvas")
            continue
        print("adding point", complex(x, line_height), b)
        intersections.append(complex(x, line_height))
        previous_point = path_point
        """

    return intersections


def get_all_horizontal_intersections(lines: list[Line], path: Path, step=.02) -> dict[int, list[complex]]:
    intersections = {}
    n_steps = int((path.length() / step) + .5)
    previous_point = path.point(0)
    for step_idx in range(1, n_steps):
        path_point = path.point(step_idx * step)
        print("at step %d of %d, %d lines" % (step_idx, n_steps, len(lines)))
        for line in lines:
            print("line calc")
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

            # print("adding point", intersection)
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
    entire_svg_path = Path(*paths)
    entire_bbox = entire_svg_path.bbox()
    bbox_width, bbox_height = entire_bbox[2] - entire_bbox[0], entire_bbox[3] - entire_bbox[1]
    canvas_width, canvas_height = canvas_dimensions
    print("bbox", entire_bbox)
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
                    height_intersections[height].append(complex(path.point(T1).real, height))
            except AssertionError as e:
                print("failed to find intersection:", e)
                pass

    for height, intersections in height_intersections.items():
        height_intersections[height] = sorted(height_intersections[height], key=lambda x: x.real)
        #print("height intersection:", height, height_intersections[height])
        if len(height_intersections[height]) > max_intersections:
            max_intersections = len(height_intersections[height])

    print("HEIGHTS", heights)
    for nth_intersection in range(0, max_intersections-1, 2):
        path = Path()
        last_point = None
        last_line_n_intersections = 0
        for height in sorted(height_intersections.keys()):
            curr_intersections = height_intersections[height]
            # TODO: this doesn't work in case the number of intersections is
            # the same but the intersections are actually with a new shape
            if len(curr_intersections) != last_line_n_intersections:
                print("splitting path", last_line_n_intersections, len(curr_intersections))
                if len(path._segments) > 0:
                    yield path
                path = Path()
                last_point = None
            last_line_n_intersections = len(curr_intersections)

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

    """
    heights = sorted(heights)
    for nth_intersection in range(0, max_intersections-1, 2):
        path = Path()
        last_point = None
        print("generating paths for interstection",nth_intersection, "and", nth_intersection+1)
        for i in range(len(heights)):
            height = heights[i]
            current_height_intersections = height_intersections[height]

            # if there are no more intersections with this line skip it
            if nth_intersection >= len(current_height_intersections):
                continue

            # if it doesn't have an interception pair
            # just create a zero length line to draw a dot
            if nth_intersection+1 >= len(current_height_intersections):
                new_point1 = current_height_intersections[nth_intersection]
                if last_point is not None:
                    if abs(new_point1.imag - last_point.imag) > line_step * 1.1:
                        print("finished", new_point1.imag, last_point.imag)
                        yield path
                        path = Path()
                    else:
                        path.append(Line(last_point, new_point1))
                        print("APPENDING LINE:", Line(last_point, new_point1))

                # print("APPENDING DOT:", Line(new_point1, new_point1))
                # path.append(Line(new_point1, new_point1))
                last_point = new_point1
                continue

            print("getting intersection indexes", nth_intersection, nth_intersection+1)
            new_point1 = current_height_intersections[nth_intersection]
            new_point2 = current_height_intersections[nth_intersection+1]
            # connect the last point with the first new one
            if last_point is not None:
                if abs(new_point1.imag - last_point.imag) > line_step*1.1:
                    print("finished", new_point1.imag, last_point.imag)
                    yield path
                    path = Path()
                else:
                    path.append(Line(last_point, new_point1))
                    print("APPENDING LINE:", Line(last_point, new_point1))
            # create new line between the 2 intersections
            path.append(Line(new_point1, new_point2))
            print("APPENDING NEW LINE:", Line(new_point1, new_point2))
            last_point = new_point2

        #print("PATH", path)
        if path.length() > 0:
            yield path
    """


def frange(start, stop=None, step=None):
    # if set start=0.0 and step = 1.0 if not specified
    start = float(start)
    if stop == None:
        stop = start + 0.0
        start = 0.0
    if step == None:
        step = 1.0

    print("start = ", start, "stop = ", stop, "step = ", step)

    count = 0
    while True:
        temp = float(start + count * step)
        if step > 0 and temp >= stop:
            break
        elif step < 0 and temp <= stop:
            break
        yield temp
        count += 1