import time
import serial  # is actually pyserial
import struct
from cmath import polar, pi
from enum import Enum
from typing import Tuple


class Mode(Enum):
    IDLE = 0
    HOME = 1
    AUTO_CALIBRATE = 2
    DRAW = 3


class Command(Enum):
    NONE = 0
    GET_STATUS = 1
    SET_MODE = 2
    CALIBRATE = 3
    ADD_POSITION = 4


class Status:
    def __init__(self):
        self.currentMode = Mode.IDLE
        self.calibrated = False
        self.calibrating = False
        self.amplitudeStepperPos = 0
        self.amplitudeStepperTargetPos = 0
        self.amplitudeStepperSpeed = 0
        self.angleStepperPos = 0
        self.angleStepperTargetPos = 0
        self.angleStepperSpeed = 0
        self.travelableDistanceSteps = 0
        self.stepsPerMm = 0
        self.minAmplitudePos = 0
        self.maxAmplituePos = 0
        self.maxAnglePos = 0
        self.maxEncoderCount = 0
        self.nextPosToPlaceIdx = 0
        self.nextPosToGoIdx = 0

    def update_status(self, serial_conn: serial.Serial):
        self.currentMode = Mode(int(serial_conn.readline()))
        self.calibrated = False if int(serial_conn.readline()) == 0 else True
        self.calibrating = False if int(serial_conn.readline()) == 0 else True
        self.amplitudeStepperPos = int(serial_conn.readline())
        self.amplitudeStepperTargetPos = int(serial_conn.readline())
        self.amplitudeStepperSpeed = int(serial_conn.readline())
        self.angleStepperPos = int(serial_conn.readline())
        self.angleStepperTargetPos = int(serial_conn.readline())
        self.angleStepperSpeed = int(serial_conn.readline())
        self.travelableDistanceSteps = int(serial_conn.readline())
        self.stepsPerMm = float(serial_conn.readline())
        self.minAmplitudePos = int(serial_conn.readline())
        self.maxAmplituePos = int(serial_conn.readline())
        self.maxAnglePos = int(serial_conn.readline())
        self.encoderCount = int(serial_conn.readline())
        self.maxEncoderCount = int(serial_conn.readline())
        self.nextPosToPlaceIdx = int(serial_conn.readline())
        self.nextPosToGoIdx = int(serial_conn.readline())

    def __str__(self) -> str:
        out_str = ""
        out_str += "Current Mode: %s\n" % self.currentMode
        out_str += "Calibrated: %s\n" % self.calibrated
        out_str += "Calibrating: %s\n" % self.calibrating
        out_str += "Amplitude Pos: %s\n" % self.amplitudeStepperPos
        out_str += "Amplitude Target Pos: %s\n" % self.amplitudeStepperTargetPos
        out_str += "Amplitude Speed: %s\n" % self.amplitudeStepperTargetPos
        out_str += "Angle Pos: %s\n" % self.angleStepperPos
        out_str += "Angle Target Pos: %s\n" % self.angleStepperPos
        out_str += "Angle Speed: %s\n" % self.angleStepperPos
        out_str += "Travelable Distance Steps: %s\n" % self.travelableDistanceSteps
        out_str += "Steps per mm: %s\n" % self.stepsPerMm
        out_str += "Min amplitude Pos: %s\n" % self.minAmplitudePos
        out_str += "Max amplitude Pos: %s\n" % self.maxAmplituePos
        out_str += "Max angle Pos: %s\n" % self.maxAnglePos
        out_str += "Encoder Count: %s\n" % self.encoderCount
        out_str += "Max Encoder Count: %s\n" % self.maxEncoderCount
        out_str += "Next Pos To Place Idx: %s\n" % self.nextPosToPlaceIdx
        out_str += "Next Pos To Go Idx: %s\n" % self.nextPosToGoIdx

        return out_str


class PolarSketcherInterface:
    def __init__(self, port='/dev/cu.usbserial-0001', baud_rate=115200):
        self.port = port
        self.baud_rate = baud_rate
        self.serial = serial.Serial(port, baud_rate)
        self.status = Status()
        time.sleep(2)
        

    def __encode_int(self, val: int):
        return val.to_bytes(4, 'little', signed=True)

    def __encode_float(self, val: float):
        return struct.pack("<f", val)

    def set_mode(self, mode: Mode):
        self.serial.write(self.__encode_int(Command.SET_MODE.value))
        self.serial.write(self.__encode_int(mode.value))

    def calibrate(self) -> Status:
        self.serial.write(self.__encode_int(Command.CALIBRATE.value))
        # self.serial.write(self.__encode_int(self.status.travelableDistanceSteps))
        # self.serial.write(self.__encode_float(self.status.stepsPerMm))
        # self.serial.write(self.__encode_int(self.status.minAmplitudePos))
        # self.serial.write(self.__encode_int(self.status.maxAmplituePos))
        # self.serial.write(self.__encode_int(self.status.maxAnglePos))
        # self.serial.write(self.__encode_int(self.status.maxEncoderCount))

        # TODO read calibration from a file or something
        self.serial.write(self.__encode_int(38471))
        self.serial.write(self.__encode_float(78.51))
        self.serial.write(self.__encode_int(2886))
        self.serial.write(self.__encode_int(41357))
        self.serial.write(self.__encode_int(14844))
        self.serial.write(self.__encode_int(1220))
        return self.update_status()

    def add_position(self, amplitude, angle, pen, amplitude_velocity, angle_velocity):
        self.serial.write(self.__encode_int(Command.ADD_POSITION.value))
        self.serial.write(self.__encode_int(amplitude))
        self.serial.write(self.__encode_int(angle))
        self.serial.write(self.__encode_int(pen))
        self.serial.write(self.__encode_int(amplitude_velocity))
        self.serial.write(self.__encode_int(angle_velocity))

    def update_status(self) -> Status:
        self.serial.write(self.__encode_int(Command.GET_STATUS.value))
        self.status.update_status(self.serial)
        return self.status

    def wait_for_idle(self):
        while self.update_status().currentMode != Mode.IDLE:
            time.sleep(.1)

    def convert_to_stepper_positions(self, canvas_size: Tuple[float, float], position: Tuple[float, float]) -> Tuple[int, int]:
        polar_coords = polar(complex(position[0], position[1]))
        amplitude = polar_coords[0]
        angle = polar_coords[1] * (180 / pi)

        polar_canvas: complex = polar(complex(canvas_size[0], canvas_size[1]))
        canvas_amplitude = polar_canvas[0]

        amplitudeSteps = mapMinMax(amplitude, 0, canvas_amplitude, 0, self.status.maxAmplituePos)
        angleSteps = mapMinMax(angle, 0, 90, 0, self.status.maxAnglePos)
        return int(amplitudeSteps), int(angleSteps)


def mapMinMax(srcVal, srcMin, srcMax, targetMin, targetMax):
    return srcVal * ((targetMax - targetMin) / (srcMax - srcMin))