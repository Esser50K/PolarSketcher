import sys
import time
import numpy as np
import cv2
import matplotlib.pyplot as plt
from potrace import Bitmap, Path
from PIL import Image

camera = cv2.VideoCapture(0)
time.sleep(1)
_, rgb_img = camera.read()
cv2.imwrite("out.png", rgb_img)
# rgb_img = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
gray = cv2.cvtColor(rgb_img.copy(), cv2.COLOR_BGR2GRAY)
ret, thresh = cv2.threshold(gray, 80, 255, 0)
contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
copy_img = np.zeros((rgb_img.shape[0], rgb_img.shape[1], rgb_img.shape[2]))
cv2.drawContours(copy_img, contours,-1,(0,0,255),2)


### Potrace Experiment

def backend_svg(output, image, path: Path):
    with open(output, "w") as fp:
        fp.write(
            '<svg version="1.1"' +
            ' xmlns="http://www.w3.org/2000/svg"' +
            ' xmlns:xlink="http://www.w3.org/1999/xlink"' +
            ' width="%d" height="%d"' % (image.width, image.height) +
            ' viewBox="0 0 %d %d">' % (image.width, image.height)
        )
        parts = []
        for curve in path:
            fs = curve.start_point
            parts.append("M%f,%f" % (fs.x, fs.y))
            for segment in curve.segments:
                if segment.is_corner:
                    a = segment.c
                    parts.append("L%f,%f" % (a.x, a.y))
                    b = segment.end_point
                    parts.append("L%f,%f" % (b.x, b.y))
                else:
                    a = segment.c1
                    b = segment.c2
                    c = segment.end_point
                    parts.append("C%f,%f %f,%f %f,%f" % (a.x, a.y, b.x, b.y, c.x, c.y))
            parts.append("z")
        fp.write(
            '<path stroke="none" fill="%s" fill-rule="evenodd" d="%s"/>'
            % ('black', "".join(parts))
        )
        fp.write("</svg>")


img = Image.open(sys.argv[1])
bm = Bitmap(img, blacklevel=0.35)
plist = bm.trace(
    turdsize=1,
    turnpolicy='minority',
    alphamax=1,
    opticurve=True,
    opttolerance=0.2,
)

backend_svg("out.svg", img, plist)

# c = max(contours, key=cv2.contourArea) #max contour
# f = open('path.svg', 'w+')
# f.write('<svg width="'+str(rgb_img.shape[1])+'" height="'+str(rgb_img.shape[0])+'" xmlns="http://www.w3.org/2000/svg">')

# min_length = 100
# for c in contours:
#     if len(c) < min_length:
#         continue

#     f.write('<path d="M')
#     for i in range(len(c)):
#         #print(c[i][0])
#         x, y = c[i][0]
#         print(x)
#         f.write(str(x)+  ' ' + str(y)+' ')
#     f.write('"/>')

# f.write('</svg>')
# f.close()


# titles = ['original','contours']
# imgs = [rgb_img, copy_img]
# for i in range (2):
#     plt.subplot(1,2,i+1)
#     plt.xticks([])
#     plt.yticks([])
#     plt.title(titles[i])
#     plt.imshow(imgs[i])
# plt.show()
