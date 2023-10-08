import cv2
import argparse
import numpy as np
from svgpathtools import Path, Line, wsvg
from math import sin, pi
from functools import lru_cache

@lru_cache
def frange(start, stop, increment=1.0):
    if increment == 0:
        raise ValueError("Increment must not be zero.")
    
    approx_eq = lambda a, b: abs(a - b) < 1e-9  # to handle floating point precision issues

    current = start
    while (increment > 0 and current < stop) or (increment < 0 and current > stop) or approx_eq(current, stop):
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
    parser = argparse.ArgumentParser(description='Resize an image to the specified height while preserving the aspect ratio.')
    parser.add_argument('--output-path', type=str, default="out.svg",  help='Path to save the resized image')
    parser.add_argument('--height', type=int, default=80,  help='Target height for the resized image')
    parser.add_argument('--pixel-width', type=int, default=10, help='Width of a pixel')
    parser.add_argument('--resolution', type=float, default=.1, help='Resolution of the sin graph function')
    parser.add_argument('--amplitude-acceleration', type=float, default=5, help='Acceleration factor of amplitude  change')
    parser.add_argument('--frequency-acceleration', type=float, default=1.0005, help='Acceleration factor of frequency change')
    parser.add_argument('--max-amplitude', type=float, default=5, help='Max amplitude of individual sin waves')
    parser.add_argument('--max-frequency', type=float, default=2, help='Max frequency of individual sin waves')
    args = parser.parse_args()
    
    path = Path()

    start_point = complex(0, 0)
    a = 0.1
    f = 1  # starting frequency
    phase = 0.0  # starting phase

    # Increasing loop
    for x in frange(.01, 10, .01):
        y = a * sin(phase)
        a += 0.005
        f += .001
        phase += f * args.resolution  # Update the phase
        print("up", a, f, x, y)

        end_point = complex(x, y)
        line = Line(start_point, end_point)
        start_point = end_point
        path.append(line)

    # Decreasing loop
    for x in frange(10, 20, .01):
        y = a * sin(phase)
        a -= 0.005
        f -= .001
        phase += f * args.resolution  # Continue updating the phase
        print("down", a, f, x, y)

        end_point = complex(x, y)
        line = Line(start_point, end_point)
        start_point = end_point
        path.append(line)


    wsvg(paths=[path], filename=args.output_path)