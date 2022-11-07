import time

import serial

UP = True
DOWN = False


class PolarSketcherConnector:
    def __init__(self, port='/dev/cu.usbmodem141301', baud_rate=115200):
        self.port = port
        self.arduino = serial.Serial(port, baud_rate)
        self.pen_state = UP
        self.previous_point = None
        time.sleep(2)
        # msg = arduino.read(arduino.inWaiting())  # read everything in the input buffer
        # print(msg)

    def write(self, content, verbose=True):
        self.arduino.write(content)
        msg = self.arduino.read_until(b'DONE')
        if verbose:
            print(msg.decode("utf-8"))
        return msg

    def auto_home(self):
        self.write(b'RESET\n')

    def write_point(self, point):
        self.write(('%f:%f\n' % point).encode())

    def move_pen(self, up):
        self.pen_state = up
        self.write(b'UP\n' if up else b'DOWN\n')

    def draw_point(self, point):
        if point is None:
            self.move_pen(UP)
            return

        # if pen is up it is moving to start of new path
        # first move it to initial position then put pen down
        self.write_point(point)
        if self.pen_state == UP:
            self.move_pen(DOWN)

    def shutdown(self):
        self.move_pen(UP)
        self.auto_home()
        self.arduino.flush()
        self.arduino.close()
