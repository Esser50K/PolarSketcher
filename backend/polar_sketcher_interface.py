import os
import time
import serial  # is actually pyserial
import struct
from cmath import polar, pi
from enum import Enum
from typing import Tuple
from threading import Thread, Event

CMD_PROCESSED_SUCCESSFULLY_MSG = "OK"
CMD_PROCESSING_FAILURE_MSG = "FAIL"
SETUP_DONE_MSG = "SETUP DONE"
STATUS_START_MSG = "STATUS START"
UNRECOGNIZED_CMD_MSG = "DID NOT RECOGNIZE COMMAND TYPE"
CHECKSUM_MISMATCH = "CHECKSUM MISMATCH"


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
    SET_ANGLE_CORRECTION = 5


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
        self.encoderCount = 0
        self.maxEncoderCount = 0
        self.nextPosToPlaceIdx = 0
        self.nextPosToGoIdx = 0
        self.minAmplitudeButtonPressed = 0
        self.maxAmplitudeButtonPressed = 0
        self.minAngleButtonPressed = 0
        self.maxAngleButtonPressed = 0
        self.angleCorrectionEnabled = False

    def update_status(self, serial_conn: serial.Serial):
        self.currentMode = Mode(int(serial_conn.readline()))
        self.calibrated = bool(int(serial_conn.readline()))
        self.calibrating = bool(int(serial_conn.readline()))

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

        self.minAmplitudeButtonPressed = int(serial_conn.readline())
        self.maxAmplitudeButtonPressed = int(serial_conn.readline())
        self.minAngleButtonPressed = int(serial_conn.readline())
        self.maxAngleButtonPressed = int(serial_conn.readline())

        self.angleCorrectionEnabled = bool(int(serial_conn.readline()))

    def __str__(self) -> str:
        out_str = ""
        out_str += "Current Mode: %s\n" % self.currentMode
        out_str += "Calibrated: %s\n" % self.calibrated
        out_str += "Calibrating: %s\n" % self.calibrating
        out_str += "Amplitude Pos: %s\n" % self.amplitudeStepperPos
        out_str += "Amplitude Target Pos: %s\n" % self.amplitudeStepperTargetPos
        out_str += "Amplitude Speed: %s\n" % self.amplitudeStepperSpeed
        out_str += "Angle Pos: %s\n" % self.angleStepperPos
        out_str += "Angle Target Pos: %s\n" % self.angleStepperTargetPos
        out_str += "Angle Speed: %s\n" % self.angleStepperSpeed
        out_str += "Travelable Distance Steps: %s\n" % self.travelableDistanceSteps
        out_str += "Steps per mm: %s\n" % self.stepsPerMm
        out_str += "Min amplitude Pos: %s\n" % self.minAmplitudePos
        out_str += "Max amplitude Pos: %s\n" % self.maxAmplituePos
        out_str += "Max angle Pos: %s\n" % self.maxAnglePos
        out_str += "Encoder Count: %s\n" % self.encoderCount
        out_str += "Max Encoder Count: %s\n" % self.maxEncoderCount
        out_str += "Next Pos To Place Idx: %s\n" % self.nextPosToPlaceIdx
        out_str += "Next Pos To Go Idx: %s\n" % self.nextPosToGoIdx
        out_str += "Min Amplitude Pressed: %s\n" % self.minAmplitudeButtonPressed
        out_str += "Max Amplitude Pressed: %s\n" % self.maxAmplitudeButtonPressed
        out_str += "Min Angle Pressed: %s\n" % self.minAngleButtonPressed
        out_str += "Max Angle Pressed: %s\n" % self.maxAngleButtonPressed
        out_str += "Angle Correction Enabled: %s\n" % self.angleCorrectionEnabled

        return out_str


class PolarSketcherInterface:
    def __init__(self, baud_rate=115200, port=None, angle_correction=True):
        self.port = port if port is not None else find_serial_port()
        self.baud_rate = baud_rate
        self.status = Status()
        self.__command_processed_event = Event()
        self.__setup_done_event = Event()
        self.__stop = False
        self.__serial_reader = None
        self.__needs_retry = False
        self.__last_sent_msg = b''
        self.__angle_correction_enabled = angle_correction

        self.serial = None
        self.__initilised = False
        time.sleep(2)

    def init(self):
        if self.__initilised:
            self.stop()
            return

        self.__command_processed_event.clear()
        self.__setup_done_event.clear()
        self.status = Status()
        self.__stop = False

        self.serial = serial.Serial(self.port, self.baud_rate)
        # cannot assume that that serial will always reset, so do it here
        self.serial.setDTR(False)
        time.sleep(.1)
        self.serial.setDTR(True)

        self.__serial_reader = Thread(
            target=self.__process_serial, daemon=True)
        self.__serial_reader.start()
        self.__needs_retry = False
        self.__last_sent_msg = b''

        self.__setup_done_event.wait()
        self.set_angle_correction(self.__angle_correction_enabled)
        self.__initilised = True

    def stop(self, wait=True):
        self.__stop = True
        if wait:
            self.__serial_reader.join()

        self.__initilised = False

    def __encode_int(self, val: int):
        return val.to_bytes(4, 'little', signed=True)

    def __encode_float(self, val: float):
        return struct.pack("<f", val)

    def __process_serial(self):
        received = b''
        while not self.__stop:
            try:
                start_time = time.time()
                serial._timeout = 1
                self.serial.timeout = 1
                received += self.serial.read()
                if not received.endswith(b'\n'):
                    if time.time() - start_time > 1:
                        # this means a timeout occurred, let's see whats in the buffer
                        print("TIMOUT, CURRENT BUFFER:", str(received))
                        print("LAST SENT MSG:", str(self.__last_sent_msg))
                    continue

                line = received.split(b'\n')[0]
                received = b''

                try:
                    line = line.decode("utf-8")
                except Exception as e:
                    pass

                if line == CMD_PROCESSED_SUCCESSFULLY_MSG:
                    self.__command_processed_event.set()
                elif line == CMD_PROCESSING_FAILURE_MSG:
                    self.__needs_retry = True
                    self.__command_processed_event.set()
                elif line == STATUS_START_MSG:
                    self.status.update_status(self.serial)
                elif line == SETUP_DONE_MSG:
                    self.__setup_done_event.set()
                elif line == UNRECOGNIZED_CMD_MSG:
                    # TODO implement resyncing if necessary
                    print("NEEDS RESYNC")
                    pass
                else:
                    print("serial:", line)
            except Exception as e:
                print("stopped reading from serial because:", e)
                return

    def __wait_for_command_processing(self, max_wait=1):
        start_time = time.time()
        while not self.__command_processed_event.wait(timeout=.1):
            if time.time() - start_time > max_wait:
                return False

        self.__command_processed_event.clear()
        return True

    def write_message(self, msg: bytes):
        msg = b'<<<' + msg + b'>>>'
        self.serial.write(msg)
        self.__last_sent_msg = msg

    def set_mode(self, mode: Mode) -> Status:
        msg = self.__encode_int(Command.SET_MODE.value)
        msg += self.__encode_int(mode.value)
        self.write_message(msg)
        self.__wait_for_command_processing()
        return self.update_status()

    def calibrate(self) -> Status:
        msg = self.__encode_int(Command.CALIBRATE.value)

        # TODO read calibration from a file or something
        # travelable distance steps
        msg += self.__encode_int(74810)

        # steps per mm
        msg += self.__encode_float(157.16)

        # minAmplitudePos
        msg += self.__encode_int(5809)

        # maxAmplituePos
        msg += self.__encode_int(80619)

        # maxAnglePos
        msg += self.__encode_int(28760)

        # maxEncoderCount
        msg += self.__encode_int(2450)

        self.write_message(msg)
        self.__wait_for_command_processing()
        return self.update_status()

    def add_position(self, amplitude, angle, pen, amplitude_velocity, angle_velocity):
        msg = self.__encode_int(Command.ADD_POSITION.value)
        msg += self.__encode_int(amplitude)
        msg += self.__encode_int(angle)
        msg += self.__encode_int(pen)
        msg += self.__encode_int(amplitude_velocity)
        msg += self.__encode_int(angle_velocity)

        checksum = (amplitude % 123) + \
                   (angle % 123) + \
                   (pen % 123) + \
                   (amplitude_velocity % 123) + \
                   (angle_velocity % 123)

        # print("SENDING POS:", amplitude, angle, pen, amplitude_velocity, angle_velocity)
        # print("SENDING CHECKSUM VAL:", checksum)
        msg += self.__encode_int(checksum)
        self.write_message(msg)

        while not self.__wait_for_command_processing():
            print("position not processed yet")
            self.write_message(msg)

        # this is un expected retry when the buffer
        # on the controller side is full,
        # for now just keep trying
        while self.__needs_retry:
            time.sleep(.1)
            print("needs retry")
            print(self.update_status())
            self.write_message(msg)
            self.__needs_retry = False
            # TODO if the command is not being processed at all
            # the controller has to be reset
            while not self.__wait_for_command_processing():
                print("position not processed yet")

    def update_status(self) -> Status:
        msg = self.__encode_int(Command.GET_STATUS.value)
        self.write_message(msg)
        self.__wait_for_command_processing()
        return self.status

    def set_angle_correction(self, value: bool) -> Status:
        msg = self.__encode_int(Command.SET_ANGLE_CORRECTION.value)
        msg += self.__encode_int(int(value))
        self.write_message(msg)
        self.__wait_for_command_processing()
        return self.update_status()

    def wait_for_idle(self) -> Status:
        while self.update_status().currentMode != Mode.IDLE:
            time.sleep(.1)

        return self.status

    def convert_to_stepper_positions(self, canvas_size: Tuple[float, float], position: Tuple[float, float]) -> Tuple[int, int]:
        polar_coords = polar(complex(position[0], position[1]))
        amplitude = polar_coords[0]
        angle = polar_coords[1] * (180 / pi)
        canvas_amplitude = canvas_size[0]

        amplitudeSteps = mapMinMax(
            amplitude,
            0, canvas_amplitude,
            0, self.status.maxAmplituePos)
        angleSteps = mapMinMax(angle, 0, 90, 0, self.status.maxAnglePos)
        return int(amplitudeSteps), int(angleSteps)


def mapMinMax(srcVal, srcMin, srcMax, targetMin, targetMax):
    return srcVal * ((targetMax - targetMin) / (srcMax - srcMin))


def find_serial_port():
    default = '/dev/cu.usbserial-0001'
    devices = os.listdir('/dev/')
    for device in devices:
        if device.startswith(('serial', 'ttyACM', 'ttyUSB', 'ttyS', 'cu.usbserial')):
            return '/dev/' + device
    return default
