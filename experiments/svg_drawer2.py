import sys
import time
import math
import serial
import pygame
from xml.dom import minidom
from svg.path import Path, Line, Arc, CubicBezier, QuadraticBezier, Close, parse_path

scale = 1
offset = 250

# variables also on the arduino
# microstepping mode
stepperMode = 32
# fancy variable to give space for the pen when platform is turning around the edge
platformOffsetBuffer = 50 * stepperMode
# offset of the stepper motor platform in full steps
platformOffset = 255 * stepperMode
# max amplitude in full steps (times microstepping mode)
maxAmplitude = (2000 * stepperMode) + platformOffset
# max angle (which is 90º) in full steps (times microstepping mode)
maxAngle = 880 * stepperMode

port = '/dev/cu.usbmodem145301'
port = '/dev/cu.usbserial-A50285BI'
arduino = serial.Serial(port, 500000)
# time.sleep(2)
# arduino.write(b"600:600\n")
# time.sleep(2)
# msg = arduino.read(arduino.inWaiting())  # read everything in the input buffer
# print(msg)

doc = minidom.parse("../Downloads/bullet_bill.svg")
path_strings = [path.getAttribute('d')
                for path in doc.getElementsByTagName('path')]
rects = [path.getAttribute('d')
         for path in doc.getElementsByTagName('rect')]
circle = [path.getAttribute('d')
          for path in doc.getElementsByTagName('circle')]
dimensions = doc.getElementsByTagName(
    'svg')[0].getAttribute("viewBox").split(" ")
doc.unlink()

print(dimensions)
width = int(float(dimensions[2]) - float(dimensions[0]))
height = int(float(dimensions[3]) - float(dimensions[1]))
# maxCanvasWidth = 55624
# maxCanvasHeight = 55624
canvasWidth = 15000
canvasHeight = 15000


def parse_rect(rect):
    print(rect.attrib)
    start_x = float(rect.getAttribute["x"])
    start_y = float(rect.getAttribute["y"])
    width = float(rect.getAttribute["width"])
    height = float(rect.getAttribute["height"])
    print(start_x, start_y, width, height)
    return Path(Line(complex(start_x, start_y), complex(start_x, start_y+height)),
                Line(complex(start_x, start_y+height),
                     complex(start_x+width, start_y+height)),
                Line(complex(start_x+width, start_y+height),
                     complex(start_x+width, start_y)),
                Line(complex(start_x+width, start_y),
                     complex(start_x, start_y)))


def parse_circle(circle, precision):
    cx = float(circle.getAttribute["cx"])
    cy = float(circle.getAttribute["cy"])
    r = float(circle.getAttribute["r"])
    current_point = (cx + r, cy)  # start point
    for i in range(0, 2*math.pi, precision):
        yield current_point
        current_point = (cx + math.cos(i), cy + math.sin(i))

    yield (cx + r, cy)


def mapFloat(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


def cartesianToAmplitude(x, y):
    return math.sqrt((x**2) + (y**2))


def cartesianToAngle(x, y):
    return math.atan(y / x) * (180.0 / math.pi)


def toPolar(point):
    angle = cartesianToAngle(point[0], point[1])
    angle_steps = mapFloat(angle, 0, 90, 0, maxAngle)
    return (cartesianToAmplitude(point[0], point[1]), angle_steps)


def translated_point(point, invert_x=True, invert_y=False):
    x = point[0]
    y = point[1]

    if invert_x:
        distance_to_middle = x - (width/2)
        x = x - (distance_to_middle*2)

    if invert_y:
        distance_to_middle = y - (height/2)
        y = y - (distance_to_middle*2)

    # first offset in original canvas
    x += offset
    y += offset

    # find equivalent point in real canvas
    proportional_multiplier = canvasWidth / width
    x *= proportional_multiplier
    y *= proportional_multiplier

    return ((x*scale)+platformOffset, (y*scale)+platformOffset)


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

# for rect in rects:
#    split_paths.append(parse_rect(rect))

#split_paths = [split_paths[-1]]

pygame.init()                                  # init pygame
surface = pygame.display.set_mode((int(width*scale), int(height*scale)))
surface.fill(pygame.Color('white'))            # set background to white


def arduino_write(content):
    arduino.write(content)
    msg = arduino.read_until(b'DONE')
    print(msg.decode("utf-8"))
    return msg


time.sleep(2)
try:

    for path in split_paths:
        points_per_1000 = 250
        total_points = int((path.length() / 1000.0) * points_per_1000)
        if total_points == 0:
            continue

        points = [(p.real, p.imag)
                  for p in (path.point(i/total_points) for i in range(0, total_points+1))]

        for point in points:
            pygame.draw.circle(surface,
                               pygame.Color('blue'), point, 2)

        # go to initial position first
        print("Starting at:", points[0], toPolar(translated_point(points[0])))

        arduino_write(
            ('%f:%f\n' % (toPolar(translated_point(points[0])))).encode())
        arduino_write(b'DOWN\n')
        for point in points[1:]:
            # print("Drawing point:")
            # print(('%s:%s\n' % (translated_point(point))).encode())
            msg = arduino_write(
                ('%f:%f\n' % (toPolar(translated_point(point)))).encode())
            print("Added move:", point, toPolar(
                translated_point(point)))

            # print(msg)
        arduino_write(
            ('%f:%f\n' % (toPolar(translated_point(points[0])))).encode())
        arduino_write(b'UP\n')
        arduino_write(
            ('%f:%f\n' % (toPolar(translated_point(points[0])))).encode())
        print("Finished at:", translated_point(point))

    arduino_write(
        ('%f:%f\n' % (toPolar((platformOffset, 0)))).encode())


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
