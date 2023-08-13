import sys
import pygame
from HersheyFonts import HersheyFonts


### first generate ascii art ###

import os
import cv2
import argparse
from functools import lru_cache

parser = argparse.ArgumentParser(description='ASCII Player')
parser.add_argument("--width", type=int, default=120,
                    help="width of the terminal window")
parser.add_argument("--show", type=bool, default=False,
                    help="show the original image in an opencv window")
parser.add_argument("--inv", type=bool, default=False,
                    help="invert the shades")
parser.add_argument("image", type=str, help="path to image")
args = parser.parse_args()

image_path = args.image
if not os.path.isfile(image_path):
    print("failed to find image at:", image_path)
    exit(1)

width = args.width
characters = [' ', '.', ',', '-', '~', ':', ';', '=', '!', '*', '#', '$', '@']
if args.inv:
    characters = characters[::-1]
char_range = int(255 / len(characters))


@lru_cache
def get_char(val):
    return characters[min(int(val/char_range), len(characters)-1)]


orig_frame = cv2.imread(image_path)
if orig_frame is None:
    print("could not read image")
    exit(1)

ratio = width/orig_frame.shape[1]
# character height is 2 times character width
height = int(orig_frame.shape[0]*ratio) // 2

frame = cv2.resize(orig_frame, (width, height))
frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
if args.show:
    cv2.imshow("frame", orig_frame)
    cv2.waitKey(0)

ascii_art = ""
for y in range(0, frame.shape[0]):
    for x in range(0, frame.shape[1]):
        ascii_art += get_char(frame[y, x])
    ascii_art += "\n"



### then draw it ###

pygame.init()

size = (800, 800)
screen = pygame.display.set_mode(size)

hf = HersheyFonts()
print(hf.load_default_font("rowmans"))
hf.normalize_rendering(10)


# print(ascii_art)
# partial = "".join(ascii_art.split("\n")[20])
# lines = hf.lines_for_text(partial)
# lines = hf.lines_for_text(ascii_art)

# Fill the screen with white
screen.fill((255, 255, 255))

# Draw the lines
offset = 0
for ascii_line in ascii_art.split("\n"):
    hf.render_options.yofs = offset
    print(ascii_line)
    spaces = len(ascii_line)
    try:
        size_of_space = size[1] / spaces
        print("SIZE OF SPACE:", size_of_space)
    except:
        continue

    # now do it character by character
    for i, char in enumerate(ascii_line):
        lines = hf.lines_for_text(char)
        for line in lines:
            # print(line)
            offset_line = (line[0][0]+(i*size_of_space), line[0][1]), (line[1][0]+(i*size_of_space), line[1][1]) 
            # pygame.draw.line(screen, (0, 0, 0), (line[0][0], size[1] - line[0][1]), (line[1][0], size[1] - line[1][1]), 1)
            # pygame.draw.line(screen, (0, 0, 0), line[0], line[1], 1)
            pygame.draw.line(screen, (0, 0, 0), offset_line[0], offset_line[1], 1)
            # pygame.draw.circle(screen, pygame.Color("black"), line[0], 2, 2)
            # pygame.draw.circle(screen, pygame.Color("black"), line[1], 2, 2)
    offset += size_of_space*2

# Update the display
pygame.display.update()

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()


# for path in paths:
#     start, end = path
#     print(start, end)
