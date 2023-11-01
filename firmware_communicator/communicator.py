import os
import time
import serial
import struct
from enum import Enum
from threading import Thread, Event

CMD_PROCESSED_SUCCESSFULLY_MSG = "OK"
CMD_PROCESSING_FAILURE_MSG = "FAIL"
SETUP_DONE_MSG = "SETUP DONE"
STATUS_START_MSG = "STATUS START"
UNRECOGNIZED_CMD_MSG = "DID NOT RECOGNIZE COMMAND TYPE"
CHECKSUM_MISMATCH = "CHECKSUM MISMATCH"
CMD_PROCESSED_EVENT = Event()


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
        self.minAmplitudeButtonPressed = 0
        self.maxAmplitudeButtonPressed = 0
        self.minAngleButtonPressed = 0
        self.maxAngleButtonPressed = 0

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

        self.minAmplitudeButtonPressed = int(serial_conn.readline())
        self.maxAmplitudeButtonPressed = int(serial_conn.readline())
        self.minAngleButtonPressed = int(serial_conn.readline())
        self.maxAngleButtonPressed = int(serial_conn.readline())

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

        return out_str


def get_calib_msg():
    msg = b''
    # travelable distance steps
    msg += encode_int(37713)
    # serial_conn.write(encode_int(37729))

    # steps per mm
    msg += encode_float(79.23)
    # serial_conn.write(encode_float(80.96))

    # minAmplitudePos
    msg += encode_int(2923)
    # serial_conn.write(encode_int(2960))

    # maxAmplituePos
    msg += encode_int(40637)
    # serial_conn.write(encode_int(40689))

    # maxAnglePos
    msg += encode_int(14650)
    # serial_conn.write(encode_int(14499))

    # maxEncoderCount
    msg += encode_int(2433)
    # serial_conn.write(encode_int(1236))

    for i, c in enumerate(msg):
        print(i + 4, ":", c)
    print(msg, len(msg))
    return msg


def read_from_serial(connection: serial.Serial):
    received = b''
    while True:
        try:
            connection.timeout = 1
            received += connection.read()
            if not received.endswith(b'\n'):
                continue

            line = received.split(b'\n')[0]
            received = b''

            try:
                line = line.decode("utf-8")
            except Exception as e:
                pass

            if line == CMD_PROCESSED_SUCCESSFULLY_MSG:
                CMD_PROCESSED_EVENT.set()
            elif line == CMD_PROCESSING_FAILURE_MSG:
                CMD_PROCESSED_EVENT.set()
            elif line == STATUS_START_MSG:
                status = Status()
                status.update_status(connection)
                print(status)
            elif line == SETUP_DONE_MSG:
                print("SETUP DONE")
            elif line == UNRECOGNIZED_CMD_MSG:
                # TODO implement resyncing if necessary
                print("NEEDS RESYNC")
                pass
            else:
                print("serial:", line)
        except Exception as e:
            print("stopped reading from serial because:", e)
            time.sleep(1)
            continue


def encode_int(val: int):
    return val.to_bytes(4, 'little', signed=True)


def encode_float(val: float):
    return struct.pack("<f", val)


def write_command(serial: serial.Serial, cmd: bytes):
    serial.write(b'<<<' + cmd + b'>>>')


def find_serial_port():
    default = '/dev/cu.usbserial-0001'
    devices = os.listdir('/dev/')
    for device in devices:
        if device.startswith(('ttyACM', 'ttyUSB', 'ttyS', 'cu.usbserial')):
            return '/dev/' + device
    return default


def main():
    serial_conn = None
    read_thread = None
    try:
        port = find_serial_port()
        serial_conn = serial.Serial(port, 115200)
        serial_conn.setDTR(False)
        time.sleep(.1)
        serial_conn.setDTR(True)
        read_thread = Thread(target=read_from_serial, args=(serial_conn,))
        read_thread.start()

        while True:
            try:
                command = Command(int(input()))
                msg = encode_int(command.value)
                print(str(command))
                if command == Command.SET_MODE:
                    mode = Mode(int(input()))
                    msg += encode_int(mode.value)
                elif command == Command.CALIBRATE:
                    msg += get_calib_msg()
                elif command == Command.ADD_POSITION:
                    # serial_conn.write(encode_int(0))
                    # serial_conn.write(encode_int(0))
                    # serial_conn.write(encode_int(1))
                    # serial_conn.write(encode_int(2500))
                    # serial_conn.write(encode_int(1000))

                    amplitude = 5000
                    angle = 5000
                    pen = 1
                    amplitude_velocity = 2500
                    angle_velocity = 1000

                    msg += encode_int(amplitude)
                    msg += encode_int(angle)
                    msg += encode_int(pen)
                    msg += encode_int(amplitude_velocity)
                    msg += encode_int(angle_velocity)

                    checksum = (amplitude % 123) + \
                        (angle % 123) + \
                        (pen % 123) + \
                        (amplitude_velocity % 123) + \
                        (angle_velocity % 123)

                    msg += encode_int(checksum)
                elif command == Command.GET_STATUS:
                    # status = Status()
                    # status.update_status(serial_conn)
                    # print(status)
                    pass

                write_command(serial_conn, msg)
                while not CMD_PROCESSED_EVENT.wait(timeout=1):
                    print("waiting for command completion")
                    pass

                CMD_PROCESSED_EVENT.clear()
            except Exception as e:
                print("failed parsing user input:", e)
    except (KeyboardInterrupt, Exception) as e:
        print("EXTRA ERROR:", e)
    finally:
        serial_conn.cancel_read()
        serial_conn.close()
        if read_thread is not None:
            read_thread.join()


if __name__ == "__main__":
    main()
