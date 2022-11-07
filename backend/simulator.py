import argparse
from typing import List

import pygame
from svgelements import *
from svgpathtools import Path as ToolsPath, Line as ToolsLine

import svg_parse_utils

PIXELS_BETWEEN_POINTS = 5
CANVAS_WIDTH = 600
CANVAS_HEIGHT = 600


def bbox_to_pygame_rect(xmin, xmax, ymin, ymax):
    # left, top, width, height
    return xmin, ymax, xmax - xmin, ymin - ymax


def linearize_paths(paths: List[ToolsPath]) -> List[ToolsPath]:
    out_paths = []
    for path in paths:
        subpath = ToolsPath()

        number_of_steps = int((path.length() / PIXELS_BETWEEN_POINTS) + .5)
        real_end = start = path.point(0)
        for i in range(1, number_of_steps):
            end = path.point(min(1.0, i / number_of_steps))
            subpath.append(ToolsLine(start, end))
            start = end

        subpath.append(ToolsLine(start, real_end))
        out_paths.append(subpath)

    return out_paths


def split_svgpaths(paths: List[ToolsPath]) -> List[ToolsPath]:
    all_subpaths = []
    for path in paths:
        subpaths = path.continuous_subpaths()
        all_subpaths.extend(subpaths)

    return all_subpaths


def tuple_type(strings):
    strings = strings.replace("(", "").replace(")", "")
    mapped_int = map(int, strings.split(","))
    return tuple(mapped_int)


def draw_lines(paths: List[ToolsPath],
               surface,
               canvas_size,
               render_translate=(0, 0),
               render_scale=1.0,
               points_per_mm=.5,
               color=pygame.Color("black"),
               stroke=2):
    prev = start = None
    for point in svg_parse_utils.get_all_points(paths=paths,
                                                canvas_size=canvas_size,
                                                render_translate=render_translate,
                                                render_scale=render_scale,
                                                points_per_mm=points_per_mm):
        # indicating new path so close up the last one
        if point is None and prev is not None:
            pygame.draw.line(surface, color,
                             (prev[0], prev[1]), (start[0], start[1]),
                             stroke)
            prev = start = None

        if start is None:
            prev = start = point
            continue

        current = point
        pygame.draw.line(surface, color,
                         (current[0], current[1]), (prev[0], prev[1]),
                         stroke)
        prev = current
        yield point


def draw_points(paths: List[ToolsPath],
                surface,
                canvas_size,
                render_translate=(0, 0),
                render_scale=1.0,
                points_per_mm=.5,
                color=pygame.Color("black"),
                stroke=2):
    for point in svg_parse_utils.get_all_points(paths=paths,
                                                canvas_size=canvas_size,
                                                render_translate=render_translate,
                                                render_scale=render_scale,
                                                points_per_mm=points_per_mm):
        if point is None:
            continue

        pygame.draw.circle(surface, color, point, stroke)
        yield point


def draw_paths(paths: List[ToolsPath], surface, lines=False, color=pygame.Color("blue"), fps=60):
    if lines:
        draw_lines(paths, surface, color, fps)
    else:
        draw_points(paths, surface, color, fps)


def _draw_bboxes(paths: List[ToolsPath], surface, color):
    for path in paths:
        pygame.draw.rect(surface,
                         color,
                         bbox_to_pygame_rect(*path.bbox()),
                         2)


def draw_bboxes(paths: List[ToolsPath], surface, segments=False, color=pygame.Color('black')):
    if segments:
        new_paths = []
        for path in paths:
            for segment in path:
                new_paths.append(ToolsPath(segment))
        paths = new_paths

    _draw_bboxes(paths, surface, color)


def main():
    parser = argparse.ArgumentParser(description='Sketcher Simulator')
    parser.add_argument("path", type=str, help="path to svg file")
    parser.add_argument("--canvas-size", type=tuple_type, default=(600, 600), help="size of canvas in mm")
    parser.add_argument("--canvas-scale", type=float, default=1.0, help="scale factor for display")
    parser.add_argument("--render-scale", type=float, default=1.0, help="scale factor for svg")
    parser.add_argument("--render-size", type=tuple_type, default=(0, 0), help="alternate size for rendering the svg")
    parser.add_argument("--offset", type=tuple_type, default=(0, 0), help="offset from top left corner to render svg")
    parser.add_argument("--points-per-mm", type=float, default=.1, help="how many points to draw per mm")
    parser.add_argument("--scale-to-fit", type=bool, default=True,
                        help="automatically scale the image to fit the canvas")
    parser.add_argument("--center", type=bool, default=False, help="if the image should be centered in the canvas")
    parser.add_argument("--fps", type=int, default=0, help="the rate at which to simulate the drawing")
    parser.add_argument("--animate", type=bool, default=False,
                        help="if it should animate or just draw everything at once")
    parser.add_argument("--use-viewbox-canvas", type=bool, default=False,
                        help="use the size of the viewbox of the SVG instead of the given canvas_size")
    parser.add_argument("--draw-bbox", type=str, default=None,
                        help="draw bounding boxes around paths with color")
    parser.add_argument("--draw-bbox-segments", type=str, default=None,
                        help="draw bounding boxes around path segments with color")
    parser.add_argument("--draw-lines", type=bool, default=True,
                        help="draw bounding boxes around path segments")

    args = parser.parse_args()

    # parse SVG
    svg, all_paths = svg_parse_utils.parse(args.path, args.canvas_size)

    canvas_size = (Length("%dmm" % args.canvas_size[0]), Length("%dmm" % args.canvas_size[1]))
    bbox_width = svg.bbox()[2] - svg.bbox()[0]
    bbox_height = svg.bbox()[3] - svg.bbox()[1]
    if bbox_width > svg.viewbox.width or bbox_height > svg.viewbox.height:
        # This fixes the bbox size in case it happens
        # to be bigger than the viewbox for some reason
        width_scale = bbox_width / svg.viewbox.width
        height_scale = bbox_height / svg.viewbox.height
        fix_render_scale = max(width_scale, height_scale)  # meant to preserve aspect ratio
        bbox_width = bbox_width * fix_render_scale
        bbox_height = bbox_height * fix_render_scale

    width = int(canvas_size[0].amount * args.canvas_scale)
    height = int(canvas_size[1].amount * args.canvas_scale)

    print(bbox_width, bbox_height, svg.bbox(), svg.viewbox)
    render_translate = args.offset
    render_scale = args.render_scale
    if args.scale_to_fit:
        width_scale = width / bbox_width
        height_scale = height / bbox_height
        render_scale = max(width_scale, height_scale)  # meant to preserve aspect ratio
    elif args.use_viewbox_canvas:
        width = int(svg.viewbox.width)
        height = int(svg.viewbox.height)

    if args.render_size != (0, 0):
        render_scale = args.render_size[0] / bbox_width

    # init canvas
    pygame.init()
    surface = pygame.display.set_mode((width, height))
    surface.fill(pygame.Color('white'))  # set background to white
    clock = pygame.time.Clock()

    points = []
    drawing_func = draw_points
    if args.draw_lines:
        drawing_func = draw_lines

    if args.draw_bbox:
        draw_bboxes(all_paths, surface, segments=False, color=pygame.Color(args.draw_bbox))

    if args.draw_bbox_segments is not None:
        draw_bboxes(all_paths, surface, segments=True, color=pygame.Color(args.draw_bbox_segments))

    for point in drawing_func(paths=all_paths,
                              surface=surface,
                              canvas_size=(width, height),
                              render_translate=render_translate,
                              render_scale=render_scale,
                              points_per_mm=args.points_per_mm):
        if point is None:
            continue

        points.append(point)
        if args.animate:
            pygame.display.update()
            clock.tick(args.fps)
        pygame.event.pump()

        # if there is something in the queue we should quit
        if process_events():
            return

    pygame.display.update()

    while True:
        if process_events():
            return


def process_events():
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            return True
    return False


if __name__ == '__main__':
    main()
