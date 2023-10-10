import cv2
import argparse
import numpy as np
from typing import List
from svgpathtools import Path, Line, CubicBezier, QuadraticBezier, wsvg
from math import sin, pi
from functools import lru_cache

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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert a bitmap image to an SVG representation made of sine waves.')
    parser.add_argument('input_path', type=str, help='Path to the input image')
    parser.add_argument('--output-path', type=str, default="out.svg",  help='Path to save the resized image')
    parser.add_argument('--height', type=int, default=160,  help='Target height for the resized image')
    parser.add_argument('--pixel-width', type=float, default=4, help='Width of a pixel')
    parser.add_argument('--resolution', type=float, default=.2, help='Resolution of the sin graph function')
    parser.add_argument('--max-amplitude', type=float, default=2, help='Max amplitude of individual sin waves')
    parser.add_argument('--max-frequency', type=float, default=3, help='Max frequency of individual sin waves')
    args = parser.parse_args()
    
    image = cv2.imread(args.input_path)
    image = resize_image(image, args.height)  # adjust height
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # make it grayscale

    all_lines: List[Path] = []
    for row in range(image.shape[0]):
        sin_line = Path()
        current_x = 0
        current_sin_amplitude = 0
        current_sin_frequency = 1
        current_sin_phase = 0
        line_start_height = (row * args.pixel_width) + (args.pixel_width/2)
        start_point = complex(current_x, line_start_height)

        for col in range(image.shape[1]):
            pixel = image[row, col]

            # 255 is max value of grayscale pixel
            target_sin_amplitude = get_range_val(0, args.max_amplitude,
                                                 args.max_amplitude/255,
                                                 pixel)
            target_sin_frequency = get_range_val(0, args.max_frequency,
                                                 args.max_frequency/255,
                                                 pixel)
            

            for _ in frange(0, args.pixel_width, args.resolution):
                sin_amplitude_diff = target_sin_amplitude - current_sin_amplitude
                current_sin_amplitude += sin_amplitude_diff * args.resolution

                sin_frequency_diff = target_sin_frequency - current_sin_frequency
                current_sin_frequency += sin_frequency_diff * args.resolution

                # keep track of phase
                # y = amp * sin((frequency * x) + phase)
                # phase_shift = phase/frequency -> phase is args.resolution
                # phase = frequency * phase_shift
                phase_diff = current_sin_frequency * args.resolution
                current_sin_phase += phase_diff

                current_y = (current_sin_amplitude * sin(current_sin_phase)) + line_start_height
                end_point = complex(current_x, current_y)
                line = Line(start_point, end_point)
                sin_line.append(line)

                current_x += args.resolution
                start_point = end_point            

        all_lines.append(sin_line)

    wsvg(paths=all_lines, filename=args.output_path)

    




