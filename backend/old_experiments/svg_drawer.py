from xml.dom import minidom
from svg.path import Path, Line, Arc, CubicBezier, QuadraticBezier, Close, parse_path
import pygame
import serial
import time
import sys

scale = 1
offset = 0


port = '/dev/cu.usbmodem1453101'
arduino = serial.Serial(port, 2000000)
# time.sleep(2)
# arduino.write(b"600:600\n")
# time.sleep(2)
# msg = arduino.read(arduino.inWaiting())  # read everything in the input buffer
# print(msg)

doc = minidom.parse("../Downloads/bee_cool.svg")
path_strings = [path.getAttribute('d')
                for path in doc.getElementsByTagName('path')]
dimensions = doc.getElementsByTagName(
    'svg')[0].getAttribute("viewBox").split(" ")
doc.unlink()

print(dimensions)
width = int(float(dimensions[2]) - float(dimensions[0]))
height = int(float(dimensions[3]) - float(dimensions[1]))


def translated_point(point, invert_x=True, invert_y=False):
    x = point[0]
    y = point[1]

    if invert_x:
        distance_to_middle = x - (width/2)
        x = x - (distance_to_middle*2)

    if invert_y:
        distance_to_middle = y - (height/2)
        y = y - (distance_to_middle*2)

    return ((x*scale)+offset, (y*scale)+offset)


split_paths = []
for svgpath in path_strings:
    original_path = parse_path(svgpath)
    new_path = Path()
    for segment in original_path._segments:
        new_path.append(segment)
        if type(segment) is Close:
            split_paths.append(new_path)
            new_path = Path()
    if new_path.length() > 0:
        split_paths.append(new_path)


pygame.init()                                  # init pygame
surface = pygame.display.set_mode((1200, 1200))   # get surface to draw on
surface.fill(pygame.Color('white'))            # set background to white


def arduino_write(content):
    arduino.write(content)
    msg = arduino.read_until(b'DONE')
    return print(msg)


time.sleep(1)
try:

    for path in split_paths:
        points_per_1000 = 800
        total_points = int((path.length() / 1000.0) * points_per_1000)
        if total_points == 0:
            continue

        points = [(p.real, p.imag)
                  for p in (path.point(i/total_points) for i in range(0, total_points+1))]

        for point in points:
            # print("Drawing point:")
            # print(('%s:%s\n' % (point[0]*.05, point[1]*.05)).encode())
            # print("point:", point)
            pygame.draw.circle(surface,
                               pygame.Color('blue'), translated_point(point), 2)

        # go to initial position first
        print("Starting at:", translated_point(points[0]))
        arduino_write(('%f:%f\n' % (translated_point(points[0]))).encode())
        arduino_write(b'DOWN\n')
        for point in points[1:]:
            # print("Drawing point:")
            # print(('%s:%s\n' % (translated_point(point))).encode())
            msg = arduino_write(
                ('%f:%f\n' % (translated_point(point))).encode())
            print(msg)
        arduino_write(('%f:%f\n' % (translated_point(points[0]))).encode())
        arduino_write(b'UP\n')
        print("Finished at:", translated_point(point))


except KeyboardInterrupt:
    while True:
        command = input()
        msg = arduino_write(command.encode())
        print(msg)


# arduino_write(b'END\n')
pygame.display.update()  # copy surface to display


while True:  # loop to wait till window close
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            exit()
