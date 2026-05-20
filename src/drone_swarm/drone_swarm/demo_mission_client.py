#!/usr/bin/env python3
"""
demo_mission_client.py
======================
Klient demonstracyjny - pokazuje uzycie SERVICE i ACTION z poziomu Pythona.

Sklada sie z dwoch czesci:
  1. Najpierw wywoluje SERVICE /swarm/get_status (pyta o stan roju)
  2. Potem wysyla ACTION /execute_mission (zleca dronowi 0 lot do (20, 20, 15))
     i nasluchuje feedbacku na zywo

Mozna oczywiscie robic to samo z linii komend (ros2 service call /
ros2 action send_goal) - ten klient jest dla zilustrowania PROGRAMOWEGO
uzycia, co przyda sie w przyszlej rozbudowie systemu.
"""

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from geometry_msgs.msg import Point

from drone_interfaces.action import ExecuteMission
from drone_interfaces.srv import GetSwarmStatus


class DemoMissionClient(Node):
    def __init__(self):
        super().__init__('demo_mission_client')

        # Klient serwisu
        self.status_client = self.create_client(GetSwarmStatus, '/swarm/get_status')
        # Klient akcji
        self.action_client = ActionClient(self, ExecuteMission, '/execute_mission')

    def call_status_service(self):
        self.get_logger().info('Czekam na serwis /swarm/get_status ...')
        if not self.status_client.wait_for_service(timeout_sec=10.0):
            self.get_logger().error('Serwis niedostepny!')
            return None

        req = GetSwarmStatus.Request()
        req.include_detailed_telemetry = True
        future = self.status_client.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        resp = future.result()
        self.get_logger().info(
            f'\n=== ODPOWIEDZ Z SERWISU ===\n'
            f'  Dronow:           {resp.active_drones}/{resp.total_drones}\n'
            f'  Srednia bateria:  {resp.average_battery:.1f}%\n'
            f'  Gotowosc misyjna: {resp.mission_readiness:.0f}%\n'
            f'  Status:           {resp.status_message}\n')
        return resp

    def send_mission_goal(self, drone_id: int, x: float, y: float, z: float):
        self.get_logger().info('Czekam na action server /execute_mission ...')
        if not self.action_client.wait_for_server(timeout_sec=10.0):
            self.get_logger().error('Action server niedostepny!')
            return

        goal = ExecuteMission.Goal()
        goal.drone_id = drone_id
        goal.target_position = Point(x=x, y=y, z=z)
        goal.max_speed = 5.0

        self.get_logger().info(
            f'>>> Wysylam misje: dron {drone_id} -> ({x}, {y}, {z})')

        send_goal_future = self.action_client.send_goal_async(
            goal, feedback_callback=self.feedback_callback)
        rclpy.spin_until_future_complete(self, send_goal_future)

        goal_handle = send_goal_future.result()
        if not goal_handle.accepted:
            self.get_logger().error('Cel odrzucony przez serwer akcji')
            return

        self.get_logger().info('Cel zaakceptowany, czekam na wynik...')
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        result = result_future.result().result

        self.get_logger().info(
            f'\n=== WYNIK MISJI ===\n'
            f'  Sukces:   {result.success}\n'
            f'  Pozycja:  ({result.final_position.x:.1f}, '
            f'{result.final_position.y:.1f}, {result.final_position.z:.1f})\n'
            f'  Czas:     {result.duration_seconds:.1f} s\n'
            f'  Wiadomosc: {result.result_message}\n')

    def feedback_callback(self, feedback_msg):
        fb = feedback_msg.feedback
        self.get_logger().info(
            f'[FEEDBACK] Postep: {fb.progress_percent:5.1f}% | '
            f'Pozycja: ({fb.current_position.x:5.1f}, '
            f'{fb.current_position.y:5.1f}, {fb.current_position.z:5.1f}) | '
            f'Pozostalo: {fb.distance_remaining:.1f} m')


def main(args=None):
    rclpy.init(args=args)
    client = DemoMissionClient()
    try:
        # 1. Najpierw zapytaj o stan roju (SERVICE)
        client.call_status_service()
        # 2. Wyslij dlugotrwala misje (ACTION) i obserwuj feedback
        client.send_mission_goal(drone_id=0, x=20.0, y=20.0, z=15.0)
    except KeyboardInterrupt:
        pass
    finally:
        client.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
