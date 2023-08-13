import cv2
import numpy as np
import base64
import svgwrite
from HersheyFonts import HersheyFonts
from svgpathtools import Path, Line
from functools import lru_cache
from scour.scour import scourString, parse_args

def image_to_ascii_svg(base64_image, ascii_width=80, svg_width=520, inv=True):
    characters = [' ', '.', ',', '-', '~', ':', ';', '=', '!', '*', '#', '$', '@']
    if inv:
        characters = characters[::-1]
    char_range = int(255 / len(characters))

    @lru_cache
    def get_char(val):
        return characters[min(int(val/char_range), len(characters)-1)]

    # Convert the base64 image to a numpy array
    img_data = base64.b64decode(base64_image)
    nparr = np.frombuffer(img_data, np.uint8)
    orig_frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    ratio = ascii_width/orig_frame.shape[1]
    height = int(orig_frame.shape[0]*ratio) // 2

    frame = cv2.resize(orig_frame, (ascii_width, height))
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    ascii_art = ""
    for y in range(0, frame.shape[0]):
        for x in range(0, frame.shape[1]):
            ascii_art += get_char(frame[y, x])
        ascii_art += "\n"

    hf = HersheyFonts()
    hf.load_default_font("rowmans")


    size_of_space = svg_width / ascii_width
    hf.normalize_rendering(size_of_space*2)

    svg_chars = []
    offset = 0
    for ascii_line in ascii_art.split("\n"):
        print(ascii_line)
        hf.render_options.yofs = offset
        spaces = len(ascii_line)

        for i, char in enumerate(ascii_line):
            char_path = Path()
            lines = hf.lines_for_text(char)
            for line in lines:
                offset_line = (line[0][0]+(i*size_of_space), line[0][1]), (line[1][0]+(i*size_of_space), line[1][1])
                char_path.append(Line(start=complex(offset_line[0][0], offset_line[0][1]),
                                      end=complex(offset_line[1][0], offset_line[1][1])))
            svg_chars.append(char_path)
        offset += size_of_space*2

    dwg = svgwrite.Drawing()
    dwg.attribs['style'] = "width: 100%; height: 100%;"
    for char in svg_chars:
        path_str = char.d()
        if path_str == "":
            continue

        dwg.add(dwg.path(d=path_str, fill='none', stroke='black'))
    
    svg_string = dwg.tostring()
    compressed_svg = scourString(svg_string, parse_args(None))
    return compressed_svg

if __name__ == '__main__':
    import base64

    with open("/Users/esser50k/_desktop/YouTubing/Generic/images/logos/twitter_logo.png", "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

    svg = image_to_ascii_svg(encoded_string, ascii_width=120, inv=True)
    with open("out.svg", "w") as f:
        f.write(svg)

