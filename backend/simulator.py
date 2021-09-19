import pygame
import argparse
from svgelements import SVG, SVGText, SVGImage, Path, Shape, Length


def split_path(path: Path) -> list[Path]:
    i = 0
    subpaths = []
    while True:
        try:
            subpath = Path(path.subpath(i))
            subpaths.append(subpath)
            i += 1
        except IndexError:
            break

    return subpaths


def get_points(path: Path, render_translate=(0, 0), render_scale=1, points_per_mm=1.0):
    path_len = Length(path.length()).to_mm()
    total_points = int(path_len.amount * points_per_mm)
    if total_points == 0:
        return

    for point in (path.point(i / total_points) for i in range(0, total_points + 1)):
        yield ((point.real * render_scale) + render_translate[0],
               (point.imag * render_scale) + render_translate[1])


def tuple_type(strings):
    strings = strings.replace("(", "").replace(")", "")
    mapped_int = map(int, strings.split(","))
    return tuple(mapped_int)


def get_paths(svg: SVG) -> list[Path]:
    elements = []
    for element in svg.elements():
        try:
            if element.values['visibility'] == 'hidden':
                continue
        except (KeyError, AttributeError):
            pass
        if isinstance(element, SVGText):
            elements.append(element)
        elif isinstance(element, Path):
            if len(element) != 0:
                print("added path")
                elements.append(element)
        elif isinstance(element, Shape):
            e = Path(element)
            e.reify()  # In some cases the shape could not have reified, the path must.
            if len(e) != 0:
                print("added shape")
                elements.append(e)
        elif isinstance(element, SVGImage):
            try:
                element.load()
                if element.image is not None:
                    elements.append(element)
            except OSError:
                pass

    paths = []
    for element in elements:
        paths.extend(split_path(element))

    return elements


def get_all_points(svg: SVG, canvas_size, paths, canvas_scale=1, render_translate=(0, 0), render_scale=1.0, scale_to_fit=True, center=False, use_viewbox_canvas = False, points_per_mm=2):
    bbox_width = svg.bbox()[2] - svg.bbox()[0]
    bbox_height = svg.bbox()[3] - svg.bbox()[1]
    width = int(canvas_size[0].amount * canvas_scale)
    height = int(canvas_size[1].amount * canvas_scale)

    if scale_to_fit:
        width_scale = width / svg.viewbox.width
        height_scale = height / svg.viewbox.height
        render_scale = max(width_scale, height_scale)  # meant to preserve aspect ratio
    elif use_viewbox_canvas:
        width = int(svg.viewbox.width)
        height = int(svg.viewbox.height)

    if center:
        scaled_bbox_width = bbox_width * render_scale
        scaled_bbox_height = bbox_height * render_scale
        scaled_bbox = list(map(lambda x: x * render_scale, svg.bbox()))
        scaled_offset = scaled_bbox[:2]
        render_translate = list(render_translate)  # convert to list
        render_translate[0] = -scaled_offset[0] + (width - scaled_bbox_width) / 2
        render_translate[1] = -scaled_offset[1] + (height - scaled_bbox_height) / 2

    for path in paths:
        for point in get_points(path, render_translate, render_scale, points_per_mm):
            yield point


def main():
    parser = argparse.ArgumentParser(description='Sketcher Simulator')
    parser.add_argument("path", type=str, help="path to svg file")
    parser.add_argument("--canvas-size", type=tuple_type, default=(600, 600), help="size of canvas in mm")
    parser.add_argument("--canvas-scale", type=float, default=1.0, help="scale factor for display")
    parser.add_argument("--render-scale", type=float, default=1.0, help="scale factor for svg")
    parser.add_argument("--render-size", type=tuple_type, default=(0, 0), help="alternate size for rendering the svg")
    parser.add_argument("--offset", type=tuple_type, default=(0, 0), help="offset from top left corner to render svg")
    parser.add_argument("--points-per-mm", type=float, default=.5, help="how many points to draw per mm")
    parser.add_argument("--scale-to-fit", type=bool, default=True, help="automatically scale the image to fit the canvas")
    parser.add_argument("--center", type=bool, default=False, help="if the image should be centered in the canvas")
    parser.add_argument("--fps", type=int, default=60, help="the rate at which to simulate the drawing")
    parser.add_argument("--use-viewbox-canvas", type=bool, default=False,
                        help="use the size of the viewbox of the SVG instead of the given canvas_size")

    args = parser.parse_args()

    # parse SVG
    svg = SVG.parse(args.path)

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
        width_scale = width / svg.viewbox.width
        height_scale = height / svg.viewbox.height
        render_scale = max(width_scale, height_scale)  # meant to preserve aspect ratio
    elif args.use_viewbox_canvas:
        width = int(svg.viewbox.width)
        height = int(svg.viewbox.height)

    if args.render_size != (0, 0):
        render_scale = args.render_size[0] / bbox_width

    scaled_bbox_width = bbox_width * args.render_scale
    scaled_bbox_height = bbox_height * args.render_scale

    # init canvas
    pygame.init()
    surface = pygame.display.set_mode((width, height))
    surface.fill(pygame.Color('white'))  # set background to white
    clock = pygame.time.Clock()

    all_paths = get_paths(svg)
    points = []
    for point in get_all_points(svg,
                                (Length(width), Length(height)),
                                paths=all_paths,
                                render_translate=render_translate,
                                render_scale=render_scale,
                                scale_to_fit=args.scale_to_fit,
                                points_per_mm=args.points_per_mm,
                                center=args.center):
        points.append(point)
        pygame.draw.circle(surface,
                           pygame.Color('black'), point, 2 * max(.5, args.render_scale))
        pygame.display.update()
        pygame.event.pump()
        clock.tick(args.fps)

        # if there is something in the queue we should quit
        if process_events():
            return

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
