#!/usr/bin/env python3
"""
mission_control_node.py
=======================
Wezel "Mission Control" - hostuje ACTION SERVER.

Dlaczego AKCJA, a nie service ani topic?
  - Topic   = ciagly strumien (telemetria)
  - Service = szybkie pytanie/odpowiedz (snapshot)
  - Action  = dlugotrwale zadanie z postepem i mozliwoscia anulowania
              (np. "lec do punktu" - to trwa wiele sekund!)

Architektura:
  Klient akcji ----[Goal]----> mission_control
                              |
                              | publikuje cel na /drone_<id>/cmd_goto
                              v
                          drone_<id> rusza w kierunku celu
                              |
                              | publikuje telemetrie na /drone_<id>/telemetry
                              v
  Klient akcji <--[Feedback]-- mission_control (postep co 0.2 s)
  Klient akcji <--[Result]---- mission_control (gdy dolecial / timeout / cancel)
"""

import math
import time

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from geometry_msgs.msg import Point

from drone_interfaces.action import ExecuteMission
from drone_interfaces.msg import DroneTelemetry


class MissionControl(Node):
    def __init__(self):
        super().__init__('mission_control')

        self.declare_parameter('num_drones', 3)
        self.num_drones = self.get_parameter('num_drones').get_parameter_value().integer_value

        # Wspolne grupy callbackow - pozwalaja na rownolegle wykonywanie
        self.cb_group = ReentrantCallbackGroup()

        # Aktualne pozycje dronow (odczytywane z telemetrii)
        self.drone_positions = {}

        # --- Subskrypcje telemetrii (do monitorowania misji) ---
        for i in range(self.num_drones):
            self.create_subscription(
                DroneTelemetry,
                f'/drone_{i}/telemetry',
                lambda msg, did=i: self.telemetry_callback(msg, did),
                10,
                callback_group=self.cb_group)

        # --- Publishery komend dla dronow ---
        self.cmd_publishers = {}
        for i in range(self.num_drones):
            self.cmd_publishers[i] = self.create_publisher(
                Point, f'/drone_{i}/cmd_goto', 10)

        # --- ACTION SERVER ---
        self.action_server = ActionServer(
            self,
            ExecuteMission,
            '/execute_mission',
            execute_callback=self.execute_mission_callback,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
            callback_group=self.cb_group)

        self.get_logger().info(
            f'Mission Control gotowy. Action server /execute_mission aktywny. '
            f'Obsluguje {self.num_drones} dronow.')

    def telemetry_callback(self, msg: DroneTelemetry, drone_id: int):
        self.drone_positions[drone_id] = msg.position

    def goal_callback(self, goal_request):
        """Czy akceptujemy zadanie?"""
        self.get_logger().info(
            f'[ACTION] Otrzymano cel: dron {goal_request.drone_id} -> '
            f'({goal_request.target_position.x:.1f}, '
            f'{goal_request.target_position.y:.1f}, '
            f'{goal_request.target_position.z:.1f})')
        if goal_request.drone_id < 0 or goal_request.drone_id >= self.num_drones:
            self.get_logger().warn(f'Odrzucam: nieznany dron {goal_request.drone_id}')
            return GoalResponse.REJECT
        return GoalResponse.ACCEPT

    def cancel_callback(self, goal_handle):
        """Klient prosi o anulowanie misji."""
        self.get_logger().info('[ACTION] Otrzymano zadanie anulowania')
        return CancelResponse.ACCEPT

    def execute_mission_callback(self, goal_handle):
        """Wlasciwa egzekucja misji."""
        goal = goal_handle.request
        drone_id = goal.drone_id
        target = goal.target_position

        # Wyslij komende do drona
        self.cmd_publishers[drone_id].publish(target)

        feedback_msg = ExecuteMission.Feedback()
        start_time = time.time()
        timeout = 60.0

        # Poczatkowa odleglosc - do liczenia procentu postepu
        initial_dist = 100.0
        if drone_id in self.drone_positions:
            initial_dist = max(0.1, self._distance(self.drone_positions[drone_id], target))

        while True:
            # Anulowanie?
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                result = ExecuteMission.Result()
                result.success = False
                result.result_message = 'Misja anulowana przez operatora'
                if drone_id in self.drone_positions:
                    result.final_position = self.drone_positions[drone_id]
                result.duration_seconds = float(time.time() - start_time)
                self.get_logger().info(f'[ACTION] {result.result_message}')
                return result

            # Timeout?
            if time.time() - start_time > timeout:
                goal_handle.abort()
                result = ExecuteMission.Result()
                result.success = False
                result.result_message = 'Misja przekroczyla limit czasu (timeout)'
                if drone_id in self.drone_positions:
                    result.final_position = self.drone_positions[drone_id]
                result.duration_seconds = float(time.time() - start_time)
                self.get_logger().warn(f'[ACTION] {result.result_message}')
                return result

            # Sprawdz postep
            if drone_id in self.drone_positions:
                current = self.drone_positions[drone_id]
                dist = self._distance(current, target)
                progress = max(0.0, min(100.0, (1.0 - dist / initial_dist) * 100.0))

                # Wyslij FEEDBACK
                feedback_msg.progress_percent = float(progress)
                feedback_msg.current_position = current
                feedback_msg.distance_remaining = float(dist)
                goal_handle.publish_feedback(feedback_msg)

                # Cel osiagniety?
                if dist < 0.6:
                    goal_handle.succeed()
                    result = ExecuteMission.Result()
                    result.success = True
                    result.final_position = current
                    result.duration_seconds = float(time.time() - start_time)
                    result.result_message = (
                        f'Dron {drone_id} dotarl do celu w '
                        f'{result.duration_seconds:.1f} s')
                    self.get_logger().info(f'[ACTION] {result.result_message}')
                    return result

            time.sleep(0.2)

    @staticmethod
    def _distance(p1: Point, p2: Point) -> float:
        return math.sqrt(
            (p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2 + (p1.z - p2.z) ** 2)


def main(args=None):
    rclpy.init(args=args)
    node = MissionControl()
    # MultiThreadedExecutor jest niezbedny dla action server z blokujacym callbackiem
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
