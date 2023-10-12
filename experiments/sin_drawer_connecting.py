import cv2
import argparse
import numpy as np
from typing import List, Tuple
from svgpathtools import Path, Line, wsvg
from math import sin, pi
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
class SinState():
    amplitude: float
    frequency: float
    phase: float
    offset: float
    current_x: float
    current_y: float

@dataclass
class DrawingParams():
    resolution: float
    pixel_width: float
    max_amplitude: float
    max_frequency: float

def draw_row(row_idx: int, previous_sin_line: Path, current_increment: float, image: np.ndarray,
             sin_state: SinState, drawing_params: DrawingParams
             ) -> Tuple[Path, float, SinState]:
    sin_line = Path()
    start_point = previous_sin_line.point(1) if previous_sin_line.length() > 0 else complex(sin_state.current_x, sin_state.current_y)

    ordered_range = range(image.shape[1]) if row_idx%2==0 else range(image.shape[1]-1, -1, -1)
    for col_idx in ordered_range:
        pixel = image[row_idx, col_idx]

        # 255 is max value of grayscale pixel
        target_sin_amplitude = get_range_val(0, drawing_params.max_amplitude,
                                                drawing_params.max_amplitude/255,
                                                pixel)
        target_sin_frequency = get_range_val(0, drawing_params.max_frequency,
                                                drawing_params.max_frequency/255,
                                                pixel)
        

        for _ in frange(0, drawing_params.pixel_width, drawing_params.resolution):
            sin_amplitude_diff = target_sin_amplitude - sin_state.amplitude
            sin_state.amplitude += sin_amplitude_diff*drawing_params.resolution

            sin_frequency_diff = target_sin_frequency - sin_state.frequency
            sin_state.frequency += sin_frequency_diff*drawing_params.resolution

            # keep track of phase
            # y = amp * sin((frequency * x) + phase)
            # phase_shift = phase/frequency -> phase is args.resolution
            # phase = frequency * phase_shift
            phase_diff = sin_state.frequency * (current_increment * drawing_params.resolution)
            sin_state.phase += phase_diff

            sin_state.current_y = (sin_state.amplitude * sin(sin_state.phase)) + sin_state.offset
            end_point = complex(sin_state.current_x, sin_state.current_y)
            line = Line(start_point, end_point)
            sin_line.append(line)

            sin_state.current_x += (current_increment * drawing_params.resolution)
            start_point = end_point
    
    return sin_line, sin_state


def draw_connection(previous_sin_line: Path, target_height: float, current_increment: float, sin_state: SinState, drawing_params: DrawingParams) -> Tuple[Path, float, SinState]:
    sin_line = Path()
    current_height = sin_state.offset
    target_height = ((row_idx+1) * drawing_params.pixel_width) + (drawing_params.pixel_width/2)
    target_increment = -current_increment

    increment_ranges = np.linspace(current_increment, target_increment, drawing_params.pixel_width*10)
    height_ranges = np.linspace(current_height, target_height, drawing_params.pixel_width*10)

    start_point = previous_sin_line.point(1)
    for i in range(drawing_params.pixel_width*10):
        current_increment = increment_ranges[i]
        sin_state.offset = height_ranges[i]

        phase_diff = sin_state.frequency * (current_increment * drawing_params.resolution)
        sin_state.phase += phase_diff

        sin_state.current_y = (sin_state.amplitude * sin(sin_state.phase)) + sin_state.offset
        end_point = complex(sin_state.current_x, sin_state.current_y)
        line = Line(start_point, end_point)
        sin_line.append(line)

        sin_state.current_x += (current_increment * drawing_params.resolution)
        start_point = end_point

    return sin_line, sin_state

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert a bitmap image to an SVG representation made of sine waves.')
    parser.add_argument('input_path', type=str, help='Path to the input image')
    parser.add_argument('--output-path', type=str, default="out.svg",  help='Path to save the resized image')
    parser.add_argument('--height', type=int, default=120,  help='Target height for the resized image')
    parser.add_argument('--pixel-width', type=float, default=4, help='Width of a pixel')
    parser.add_argument('--resolution', type=float, default=.1, help='Resolution of the sin graph function')
    parser.add_argument('--max-amplitude', type=float, default=2, help='Max amplitude of individual sin waves')
    parser.add_argument('--max-frequency', type=float, default=3, help='Max frequency of individual sin waves')
    args = parser.parse_args()
    
    image = cv2.imread(args.input_path)
    image = resize_image(image, args.height)  # adjust height
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # make it grayscale

    all_lines: List[Path] = []
    drawing_params = DrawingParams(args.resolution,
                                   args.pixel_width,
                                   args.max_amplitude,
                                   args.max_frequency)
    sin_state = SinState(0, 1, 0, drawing_params.pixel_width/2, 0, 0)

    previous_sin_line = Path()
    for row_idx in range(image.shape[0]):
        current_increment = 1 if row_idx%2==0 else -1

        sin_line, sin_state = draw_row(row_idx, previous_sin_line, current_increment, image, sin_state, drawing_params)
        all_lines.append(sin_line)

        # draw connection to bottom line
        target_height = ((row_idx+1) * drawing_params.pixel_width) + (drawing_params.pixel_width/2)
        sin_line, sin_state = draw_connection(sin_line, target_height, current_increment,
                                                      sin_state, drawing_params)
        all_lines.append(sin_line)
        previous_sin_line = sin_line

    wsvg(paths=all_lines, filename=args.output_path)