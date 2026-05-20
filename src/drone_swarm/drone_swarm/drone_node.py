#!/usr/bin/env python3
"""
drone_node.py
=============
Wezel reprezentujacy POJEDYNCZEGO drona w roju.

Co robi (z punktu widzenia ROS2):
  - PUBLIKUJE na topiku /drone_<id>/telemetry typu DroneTelemetry  (2 Hz)
  - SUBSKRYBUJE topik /drone_<id>/cmd_goto typu geometry_msgs/Point
    (komendy "lec do tego punktu" przychodza od mission_control)

W rzeczywistej architekturze ten wezel mialby polaczenie z PX4/MAVROS
zamiast wewnetrznej symulacji ruchu. Tu symulujemy fizyke prosto:
  - dron lecy prosto do celu ze stala predkoscia
  - bateria stopniowo sie wyladowuje
"""

import math
import random

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Point

from drone_interfaces.msg import DroneTelemetry


class DroneNode(Node):
    def __init__(self):
        super().__init__('drone_node')

        # --- Parametry (ustawiane z launch lub CLI) ---
        self.declare_parameter('drone_id', 0)
        self.declare_parameter('initial_x', 0.0)
        self.declare_parameter('initial_y', 0.0)
        self.declare_parameter('initial_z', 10.0)

        self.drone_id = self.get_parameter('drone_id').get_parameter_value().integer_value
        self.position = Point()
        self.position.x = float(self.get_parameter('initial_x').value)
        self.position.y = float(self.get_parameter('initial_y').value)
        self.position.z = float(self.get_parameter('initial_z').value)

        self.target = None
        self.battery_level = 100.0
        self.speed = 0.0
        self.status = "IDLE"

        # --- PUBLISHER telemetrii ---
        telemetry_topic = f'/drone_{self.drone_id}/telemetry'
        self.telemetry_pub = self.create_publisher(DroneTelemetry, telemetry_topic, 10)

        # --- SUBSCRIBER komend ruchu ---
        cmd_topic = f'/drone_{self.drone_id}/cmd_goto'
        self.cmd_sub = self.create_subscription(
            Point, cmd_topic, self.cmd_callback, 10)

        # --- Timery ---
        # Aktualizacja fizyki 10 Hz
        self.update_timer = self.create_timer(0.1, self.update_physics)
        # Publikacja telemetrii 2 Hz (tak jak prawdziwe systemy)
        self.publish_timer = self.create_timer(0.5, self.publish_telemetry)

        self.get_logger().info(
            f'Dron {self.drone_id} uruchomiony w pozycji '
            f'({self.position.x:.1f}, {self.position.y:.1f}, {self.position.z:.1f})')

    def cmd_callback(self, msg: Point):
        """Otrzymano komende przelotu do nowego punktu."""
        self.target = Point(x=msg.x, y=msg.y, z=msg.z)
        self.status = "MOVING"
        self.get_logger().info(
            f'Dron {self.drone_id}: nowy cel ({msg.x:.1f}, {msg.y:.1f}, {msg.z:.1f})')

    def update_physics(self):
        """Symulacja ruchu i baterii - wywolywane 10 Hz."""
        # Bateria powoli sie rozladowuje
        self.battery_level = max(0.0, self.battery_level - 0.01)

        if self.target is not None:
            dx = self.target.x - self.position.x
            dy = self.target.y - self.position.y
            dz = self.target.z - self.position.z
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)

            if dist < 0.5:
                # Dolecial
                self.position = self.target
                self.target = None
                self.status = "IDLE"
                self.speed = 0.0
                self.get_logger().info(f'Dron {self.drone_id}: dotarl do celu')
            else:
                # Krok max 0.5 m w czasie 0.1 s -> 5 m/s
                step = min(0.5, dist)
                self.position.x += (dx / dist) * step
                self.position.y += (dy / dist) * step
                self.position.z += (dz / dist) * step
                self.speed = step / 0.1
        else:
            # Niewielki drift symulujacy wiatr
            self.position.x += random.uniform(-0.01, 0.01)
            self.position.y += random.uniform(-0.01, 0.01)
            self.speed = 0.0

    def publish_telemetry(self):
        """Publikuje aktualna telemetrie na topiku."""
        msg = DroneTelemetry()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = f'drone_{self.drone_id}'
        msg.drone_id = self.drone_id
        msg.position = self.position
        msg.battery_level = float(self.battery_level)
        msg.speed = float(self.speed)
        msg.status = self.status
        self.telemetry_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = DroneNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
