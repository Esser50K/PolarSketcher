from typing import Set, List

from svgpathtools import Path


class PathSegment(Path):
    def __init__(self, segment, original_path, **kw):
        super().__init__(segment, **kw)
        self.original_segment = segment
        self.original_path: Path = original_path


class SegmentIntersection:
    def __init__(self,
                 intersection_point: complex,
                 segment: PathSegment,
                 point_in_path: float,
                 point_in_original_path: float):
        self.intersection_point = intersection_point
        self.segment = segment
        self.point_in_path = point_in_path
        self.point_in_original_path = point_in_original_path


class Point:
    def __init__(self, point: complex):
        self.x = point.real
        self.y = point.imag

    def translated(self, translation: complex):
        return Point(complex(self.x + translation.real,
                             self.y + translation.imag))

    def to_tuple(self):
        return self.x, self.y


class Rect:
    def __init__(self, origin: Point, width: float, height: float):
        self.origin = origin
        self.width = width
        self.height = height

    def in_bounds(self, p: Point):
        return self.origin.x <= p.x < self.origin.x + self.width and self.origin.y <= p.y < self.origin.y + self.height

    def overlaps(self, other):
        if other.origin.x > self.origin.x + self.width or \
                other.origin.y > self.origin.y + self.height or \
                other.origin.x + other.width < self.origin.x or \
                other.origin.y + other.height < self.origin.y:
            return False
        return True

    def to_tuple(self):
        return self.origin.x, self.origin.y, self.width, self.height


class QuadTree:
    def __init__(self, boundary: Rect, capacity: int):
        self.boundary = boundary
        self.capacity = capacity
        self.segments = set()
        self.is_split = False
        self.subtreeNE = None
        self.subtreeNW = None
        self.subtreeSE = None
        self.subtreeSW = None

    def split(self):
        self.subtreeNE = QuadTree(
            Rect(self.boundary.origin,
                 int(self.boundary.width / 2), int(self.boundary.height / 2)),
            self.capacity
        )
        self.subtreeNW = QuadTree(
            Rect(self.boundary.origin.translated(complex(self.boundary.width / 2, 0)),
                 int(self.boundary.width / 2), int(self.boundary.height / 2)),
            self.capacity
        )
        self.subtreeSE = QuadTree(
            Rect(self.boundary.origin.translated(complex(0, self.boundary.height / 2)),
                 int(self.boundary.width / 2), int(self.boundary.height / 2)),
            self.capacity
        )
        self.subtreeSW = QuadTree(
            Rect(self.boundary.origin.translated(complex(self.boundary.width / 2, self.boundary.height / 2)),
                 int(self.boundary.width / 2), int(self.boundary.height / 2)),
            self.capacity
        )
        self.is_split = True

    def get_all_unique_segments(self, unique_segments=None) -> set:
        if unique_segments is None:
            unique_segments = set()

        unique_segments = unique_segments.union(self.segments)
        if not self.is_split:
            return unique_segments

        unique_segments = unique_segments.union(self.subtreeNE.get_all_unique_segments(unique_segments))
        unique_segments = unique_segments.union(self.subtreeNW.get_all_unique_segments(unique_segments))
        unique_segments = unique_segments.union(self.subtreeSE.get_all_unique_segments(unique_segments))
        unique_segments = unique_segments.union(self.subtreeSW.get_all_unique_segments(unique_segments))

        return unique_segments

    def insert_segment(self, segment: Path):
        if not self.boundary.overlaps(bbox_to_rect(*segment.bbox())):
            return

        if len(self.segments) < self.capacity:
            self.segments.add(segment)
        else:
            if not self.is_split:
                self.split()

            self.subtreeNE.insert_segment(segment)
            self.subtreeNW.insert_segment(segment)
            self.subtreeSE.insert_segment(segment)
            self.subtreeSW.insert_segment(segment)

    def insert_path(self, path: Path):
        for segment in path:
            self.insert_segment(PathSegment(segment, original_path=path))

    def get_segments_in_area(self, area: Rect, out=None):
        if out is None:
            out = set()

        if not self.boundary.overlaps(area):
            return out

        out = out.union(self.segments)
        if self.is_split:
            out = out.union(self.subtreeNE.get_segments_in_area(area, out))
            out = out.union(self.subtreeNW.get_segments_in_area(area, out))
            out = out.union(self.subtreeSE.get_segments_in_area(area, out))
            out = out.union(self.subtreeSW.get_segments_in_area(area, out))

        return out

    def get_intersections(self,
                          collision_path: Path,
                          found_segments: Set[PathSegment] = None) -> List[SegmentIntersection]:
        if found_segments is None:
            found_segments = set()

        for segment in collision_path:
            segment = Path(segment)
            segments_in_area = self.get_segments_in_area(bbox_to_rect(*segment.bbox()))
            found_segments = found_segments.union(segments_in_area)

        found_intersections = []
        for segment in found_segments:
            try:
                path_intersections = segment.intersect(collision_path, tol=1e-12)
                for (T1, _seg1, _t1), (_T2, _seg2, _t2) in path_intersections:
                    point = segment.point(T1)
                    point_in_path = T1
                    point_in_original_path = segment.original_path.t2T(segment.original_segment, T1)
                    found_intersections.append(
                        SegmentIntersection(point, segment, point_in_path, point_in_original_path))
            except Exception as e:
                print("An error occurred trying to get an intersection:", e)
                print("Segment D:", segment.d())
                print("Collision Path D:", collision_path.d())

        return found_intersections


def bbox_to_rect(xmin: float, xmax: float, ymin: float, ymax: float, expansion=5) -> Rect:
    origin = Point(complex(xmin - expansion, ymin - expansion))
    width = (xmax - xmin) + expansion
    height = (ymax - ymin) + expansion
    return Rect(origin, width, height)
