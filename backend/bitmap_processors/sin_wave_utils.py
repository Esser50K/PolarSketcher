import cv2
import argparse
import numpy as np
import base64
from typing import List
from svgpathtools import Path, Line, CubicBezier, wsvg
from functools import lru_cache
from dataclasses import dataclass


def frange(start, stop, increment=1.0):
    current = start
    while current < stop:
        yield current
        current += increment


def resize_image(image: np.ndarray, height: int):
    # Compute the aspect ratio
    aspect_ratio = float(image.shape[1]) / float(image.shape[0])

    # Calculate the new width based on the target height and original aspect ratio
    width = int(height * aspect_ratio)

    # Resize the image
    resized_image = cv2.resize(image, (width, height))
    return resized_image


@lru_cache
def get_range_val(start, end, increment, idx):
    return list(frange(start, end, increment))[::-1][idx]


@dataclass
class DrawingParams():
    resolution: float
    pixel_width: float
    max_amplitude: float
    max_frequency: float


class SinState:
    def __init__(self, amplitude=1,
                 frequency=1,
                 phase=0,
                 offset=0):
        self.amplitude = amplitude
        self.frequency = frequency
        self.phase = phase
        self.offset = offset
        self.current_x = 0

        self.target_amplitude = self.amplitude
        self.target_frequency = self.frequency

    def move_by(self, x: float) -> complex:
        self.current_x += x
        self.amplitude += (self.target_amplitude - self.amplitude) * x
        self.frequency += (self.target_frequency - self.frequency) * x
        self.phase += (self.frequency * x)

        return complex(self.current_x, (self.amplitude * np.sin(self.phase)) + self.offset)

    def get_current_point(self) -> complex:
        return complex(self.current_x, (self.amplitude * np.sin(self.phase)) + self.offset)

    def set_target_amplitude(self, target_amplitude):
        self.target_amplitude = target_amplitude

    def set_target_frequency(self, target_frequency):
        self.target_frequency = target_frequency


def generate_horizontal_follow_paths(image: np.ndarray, pixel_width=1):
    path = Path()

    for row in range(image.shape[0]):
        height = (row * pixel_width) + (pixel_width / 2)
        width = image.shape[1] * pixel_width
        point1 = complex(0, height)
        point2 = complex(width, height)

        going_right = (row % 2 == 0)

        if going_right:
            start_point = point1
            end_point = point2
        else:
            start_point = point2
            end_point = point1

        line = Line(start_point, end_point)
        yield Path(line)


def generate_connecting_follow_paths(image: np.ndarray, pixel_width=1):
    path = Path()

    for row in range(image.shape[0]):
        height = (row * pixel_width) + (pixel_width / 2)
        width = image.shape[1] * pixel_width
        point1 = complex(0, height)
        point2 = complex(width, height)

        going_right = (row % 2 == 0)

        if going_right:
            start_point = point1
            end_point = point2
        else:
            start_point = point2
            end_point = point1

        line = Line(start_point, end_point)
        path.append(line)

        connection_start_point = line.point(1)
        connection_end_point = complex(
            width if going_right else 0, connection_start_point.imag + pixel_width)

        control1_offset = complex(pixel_width * (1 if going_right else -1), 0)
        control2_offset = control1_offset + complex(0, pixel_width)
        control1 = connection_start_point + control1_offset
        control2 = connection_start_point + control2_offset

        connection_curve = CubicBezier(line.point(
            1), control1, control2, connection_end_point)
        path.append(connection_curve)

    yield path


def get_target_amplitude_and_frequency(image: np.ndarray, point: complex, pixel_width: float,
                                       max_amplitude, max_frequency):
    try:
        pixel_brightness = image[int(
            point.imag / pixel_width), int(point.real / pixel_width)]
        target_sin_amplitude = get_range_val(0, max_amplitude,
                                             max_amplitude / 255,
                                             pixel_brightness)
        target_sin_frequency = get_range_val(0, max_frequency,
                                             max_frequency / 255,
                                             pixel_brightness)
        return target_sin_amplitude, target_sin_frequency
    except:
        return max_amplitude / 2, max_frequency / 2


def draw_sin_along_path(follow_path: Path, sin_state: SinState, image: np.ndarray, drawing_params: DrawingParams):
    step_size = drawing_params.resolution / follow_path.length()

    offset_path_points = []
    current_t = 0
    while current_t < 1:
        follow_path_start_point = follow_path.point(current_t)
        current_t = min(1, current_t + step_size)
        follow_path_end_point = follow_path.point(current_t)

        line_vec = follow_path_end_point - follow_path_start_point
        vec_len = abs(line_vec)
        vec_angle = np.angle(line_vec)

        target_amplitude, target_frequency = get_target_amplitude_and_frequency(image, follow_path_start_point,
                                                                                drawing_params.pixel_width,
                                                                                drawing_params.max_amplitude,
                                                                                drawing_params.max_frequency)
        sin_state.set_target_amplitude(target_amplitude)
        sin_state.set_target_frequency(target_frequency)

        offset_point = sin_state.move_by(vec_len)
        offset_point = complex(0, offset_point.imag)

        rotated_x = np.cos(vec_angle) * (offset_point.real) - \
            np.sin(vec_angle) * (offset_point.imag)
        rotated_y = np.sin(vec_angle) * (offset_point.real) + \
            np.cos(vec_angle) * (offset_point.imag)
        rotated_point = complex(rotated_x, rotated_y)

        translated_offset_point = follow_path_start_point + rotated_point
        offset_path_points.append(translated_offset_point)

    max_path_len = 100
    offset_path = Path()
    total_length = 0
    for i in range(len(offset_path_points) - 1):
        start_point = offset_path_points[i]
        end_point = offset_path_points[i + 1]
        line = Line(start_point, end_point)
        offset_path.append(line)
        total_length += line.length()
        if total_length > max_path_len:
            yield offset_path
            offset_path = Path()
            total_length = 0

    yield offset_path


@dataclass
class DrawingParams():
    resolution: float
    pixel_width: float
    max_amplitude: float
    max_frequency: float


def image_to_sin_wave(base64_image,
                      canvas_width=513,
                      pixel_width=8,
                      max_frequency=2,
                      resolution=.25):
    img_data = base64.b64decode(base64_image)
    nparr = np.frombuffer(img_data, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    canvas_width_to_img_ratio = canvas_width / image.shape[1]
    n_lines = int(image.shape[0] * canvas_width_to_img_ratio / pixel_width)

    max_amplitude = pixel_width / 2
    for path in _image_to_sin_wave(image, n_lines, pixel_width, max_amplitude, max_frequency, resolution):
        yield path


def _image_to_sin_wave(image: np.ndarray,
                       n_lines,
                       pixel_width,
                       max_amplitude,
                       max_frequency,
                       resolution):
    image = resize_image(image, n_lines)  # adjust height
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # make it grayscale

    drawing_params = DrawingParams(resolution,
                                   pixel_width,
                                   max_amplitude,
                                   max_frequency)

    for path in generate_connecting_follow_paths(image, pixel_width=drawing_params.pixel_width):
        sin_state = SinState(.1, 1, 0, 0)
        for sin_path in draw_sin_along_path(path, sin_state, image, drawing_params):
            yield sin_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Convert a bitmap image to an SVG representation made of sine waves.')
    parser.add_argument('input_path', type=str, help='Path to the input image')
    parser.add_argument('--output-path', type=str,
                        default="out.svg",
                        help='Path to save the resized image')
    parser.add_argument('--height', type=int,
                        default=120,
                        help='Target height for the resized image')
    parser.add_argument('--pixel-width', type=float,
                        default=16,
                        help='Width of a pixel')
    parser.add_argument('--resolution', type=float,
                        default=.25,
                        help='Resolution of the sin graph function')
    parser.add_argument('--max-amplitude', type=float,
                        default=8,
                        help='Max amplitude of individual sin waves')
    parser.add_argument('--max-frequency', type=float,
                        default=2,
                        help='Max frequency of individual sin waves')
    args = parser.parse_args()

    image = cv2.imread(args.input_path)
    image = resize_image(image, args.height)  # adjust height
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # make it grayscale

    all_lines: List[Path] = []
    drawing_params = DrawingParams(args.resolution,
                                   args.pixel_width,
                                   args.max_amplitude,
                                   args.max_frequency)

    all_lines = _image_to_sin_wave(image,
                                   args.height,
                                   args.pixel_width,
                                   args.max_amplitude,
                                   args.max_frequency,
                                   args.resolution)
    wsvg(paths=all_lines, filename=args.output_path)
