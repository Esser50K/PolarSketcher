import serial
import time


class PolarSketcherConnector:
    def __init__(self, port='/dev/cu.usbserial-A50285BI', baud_rate=500000):
        self.port = port
        self.arduino = serial.Serial(port, baud_rate)
        time.sleep(2)

    def write(self, content, verbose=False):
        self.arduino.write(content)
        msg = self.arduino.read_until(b'DONE')
        if verbose:
            print(msg.decode("utf-8"))
        return msg
