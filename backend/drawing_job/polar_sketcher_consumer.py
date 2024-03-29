import time
from polar_sketcher_interface import PolarSketcherInterface, Mode
from drawing_job.consumer_models import Consumer, ConsumerPoint
from path_generator import CLOSE_PATH_COMMAND, PATH_END_COMMAND
from typing import Tuple, Optional, Generator


class PolarSketcherConsumer(Consumer):
    def __init__(self, polar_sketcher: PolarSketcherInterface):
        self.polar_sketcher = polar_sketcher
        self.first_point = None
        self.last_point = None

    def init(self):
        self.polar_sketcher.init()
        self.polar_sketcher.set_mode(Mode.HOME)
        status = self.polar_sketcher.wait_for_idle()
        status = self.polar_sketcher.calibrate()
        print(status)
        status = self.polar_sketcher.set_mode(Mode.DRAW)
        print("DRAW MODE?:", status)

    def shutdown(self):
        while True:
            status = self.polar_sketcher.update_status()
            if status.nextPosToGoIdx != status.nextPosToPlaceIdx - 1:
                time.sleep(.1)
                continue
            break
        self.polar_sketcher.set_mode(Mode.HOME)
        self.polar_sketcher.wait_for_idle()
        self.polar_sketcher.stop()

    def consume(self, consumer_point: ConsumerPoint):
        point = consumer_point.point
        if type(point) is tuple:
            self._consume_point(
                consumer_point, pen_position=30)
        elif point == CLOSE_PATH_COMMAND:
            self._consume_point(
                ConsumerPoint(self.first_point, consumer_point.canvas_size), pen_position=30)
        elif point == PATH_END_COMMAND:
            self.first_point = None

    def _consume_point(self, point: ConsumerPoint, pen_position: int):
        if self.first_point is None:
            self._move_to_new_path(point)

        polar_point = self._convert_to_sketcher_position(
            point.point, point.canvas_size)
        self._add_point_to_sketcher(
            polar_point, point.canvas_size, pen_position)

    def _move_to_new_path(self, new_path_start: ConsumerPoint):
        amplitude_pos, angle_pos = self._convert_to_sketcher_position(
            new_path_start.point,
            new_path_start.canvas_size)

        current_pos = self.last_point
        if current_pos is None:
            # update status is an expensive operation
            status = self.polar_sketcher.update_status()
            current_pos = (status.amplitudeStepperPos, status.angleStepperPos)

        for point in gen_intermediate_points(current_pos,
                                             (amplitude_pos, angle_pos)):
            self._add_point_to_sketcher(
                point, new_path_start.canvas_size, pen_position=0)

    def _convert_to_sketcher_position(self, point: Tuple, canvas_size: Tuple):
        point = (
            canvas_size[0] - point[0],
            point[1]
        )
        return self.polar_sketcher.convert_to_stepper_positions(
            canvas_size,
            point)

    def _add_point_to_sketcher(self, polar_point: Tuple, canvas_size: Tuple, pen_position: int):
        amp_vel, angle_vel = self.calculate_velocities(
            self.last_point, polar_point)
        self.polar_sketcher.add_position(
            polar_point[0],  # amplitude
            polar_point[1],  # angle
            pen=pen_position,
            amplitude_velocity=amp_vel,
            angle_velocity=angle_vel
        )

        self.last_point = polar_point
        if self.first_point is None:
            self.first_point = polar_point

    def calculate_velocities(self,
                             start_pos: Optional[Tuple],
                             end_pos: Tuple,
                             max_stepper_vel=1500):
        if start_pos is None:
            status = self.polar_sketcher.update_status()
            start_pos = (status.amplitudeStepperPos, status.angleStepperPos)

        amp_diff = abs(end_pos[0] - start_pos[0])
        angle_diff = abs(end_pos[1] - start_pos[1])

        diff_ratio = amp_diff / angle_diff if angle_diff != 0 else 1
        if diff_ratio < 1:
            amp_velocity = max_stepper_vel * diff_ratio
            angle_velocity = max_stepper_vel
        else:
            angle_velocity = max_stepper_vel * diff_ratio
            amp_velocity = max_stepper_vel

        return int(amp_velocity), int(angle_velocity)


def gen_intermediate_points(start_point: Tuple, end_point: Tuple, points_per_unit=.1) -> Generator[Tuple, None, None]:
    start_amp, start_angle = start_point
    end_amp, end_angle = end_point

    # Calculate the distance between the start and end points
    distance = abs(complex(*end_point) - complex(*start_point))
    if distance == 0:
        return

    # Calculate the number of points to generate
    num_points = int(distance * points_per_unit)

    if num_points == 0:
        return

    # Generate intermediate points with uniform spacing
    for i in range(num_points + 1):
        ratio = i / num_points
        amp = start_amp + (end_amp - start_amp) * ratio
        angle = start_angle + (end_angle - start_angle) * ratio
        yield int(amp), int(angle)
