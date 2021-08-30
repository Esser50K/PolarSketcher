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


def main():
    parser = argparse.ArgumentParser(description='Sketcher Simulator')
    parser.add_argument("canvas_size", type=tuple_type, default=(600, 600), help="size of canvas in mm")
    parser.add_argument("canvas_scale", type=float, default=1.0, help="scale factor for display")
    parser.add_argument("points_per_mm", type=float, default=.5, help="how many points to draw per mm")
    parser.add_argument("scale_to_fit", type=bool, default=True, help="automatically scale the image to fit the canvas")
    parser.add_argument("center", type=bool, default=False, help="if the image should be centered in the canvas")
    parser.add_argument("fps", type=int, default=60, help="the rate at which to simulate the drawing")
    parser.add_argument("use_viewbox_canvas", type=bool, default=False,
                        help="use the size of the viewbox of the SVG instead of the given canvas_size")

    args = parser.parse_args()

    # parse SVG
    svg = SVG.parse("/Users/esser420/Downloads/bullet_bill.svg")

    bbox_width = svg.bbox()[2] - svg.bbox()[0]
    bbox_height = svg.bbox()[3] - svg.bbox()[1]
    width = int(args.canvas_size[0].amount * args.canvas_scale)
    height = int(args.canvas_size[1].amount * args.canvas_scale)

    render_translate = [0, 0]
    render_scale = 1
    if args.scale_to_fit:
        width_scale = width / svg.viewbox.width
        height_scale = height / svg.viewbox.height
        render_scale = max(width_scale, height_scale)  # meant to preserve aspect ratio
    elif args.use_viewbox_canvas:
        width = int(svg.viewbox.width)
        height = int(svg.viewbox.height)

    if args.center:
        scaled_bbox_width = bbox_width * render_scale
        scaled_bbox_height = bbox_height * render_scale
        scaled_bbox = list(map(lambda x: x * render_scale, svg.bbox()))
        scaled_offset = scaled_bbox[:2]
        render_translate[0] = -scaled_offset[0] + (width - scaled_bbox_width)/2
        render_translate[1] = -scaled_offset[1] + (height - scaled_bbox_height) / 2

    # init canvas
    pygame.init()
    surface = pygame.display.set_mode((width, height))
    surface.fill(pygame.Color('white'))  # set background to white

    # get all paths
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
                elements.append(element)
        elif isinstance(element, Shape):
            e = Path(element)
            e.reify()  # In some cases the shape could not have reified, the path must.
            if len(e) != 0:
                elements.append(e)
        elif isinstance(element, SVGImage):
            try:
                element.load()  # os.path.dirname(pathname))
                if element.image is not None:
                    elements.append(element)
            except OSError:
                pass

    all_paths = []
    for element in elements:
        all_paths.extend(split_path(element))

    clock = pygame.time.Clock()
    for path in all_paths:
        for point in get_points(path, render_translate, render_scale, args.points_per_mm):
            pygame.draw.circle(surface,
                               pygame.Color('blue'), point, 2)
            pygame.display.update()
            pygame.event.pump()
            clock.tick(args.fps)

    while True:  # loop to wait till window close
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()


if __name__ == '__main__':
    main()
