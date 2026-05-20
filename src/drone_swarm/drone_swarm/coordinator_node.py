#!/usr/bin/env python3
"""
coordinator_node.py
===================
Wezel "Swarm Coordinator" - centrum dowodzenia rojem.

Co robi (z punktu widzenia ROS2):
  - SUBSKRYBUJE telemetrie od wszystkich dronow:
      /drone_0/telemetry, /drone_1/telemetry, /drone_2/telemetry ...
  - PUBLIKUJE zbiorczy stan roju na /swarm/status (custom msg SwarmStatus)
  - UDOSTEPNIA SERVICE /swarm/get_status (custom srv GetSwarmStatus)
    -> klient moze "zapytac" i dostac natychmiastowa odpowiedz

Dlaczego topic + service razem?
  - Topic   = "puszczam to w eter, kto chce niech sie podlaczy" (broadcast)
  - Service = "konkretne pytanie -> konkretna odpowiedz" (request/response)
W realnej operacji morskiej koordynator publikowalby ciagly stan
(pokazywany na ekranie dyzurnego), a serwis bylby uzywany przez systemy
trzecie do zapytania "Czy roj jest gotowy do misji TERAZ?".
"""

import rclpy
from rclpy.node import Node

from drone_interfaces.msg import DroneTelemetry, SwarmStatus
from drone_interfaces.srv import GetSwarmStatus


class SwarmCoordinator(Node):
    def __init__(self):
        super().__init__('swarm_coordinator')

        self.declare_parameter('num_drones', 3)
        self.num_drones = self.get_parameter('num_drones').get_parameter_value().integer_value

        # Trzymamy ostatnia telemetrie kazdego drona
        self.drone_telemetry = {}  # drone_id -> DroneTelemetry

        # --- Subskrypcje wszystkich dronow ---
        for i in range(self.num_drones):
            topic = f'/drone_{i}/telemetry'
            # default argument w lambdzie zamraza i (uwaga na pulapke Pythona)
            self.create_subscription(
                DroneTelemetry,
                topic,
                lambda msg, did=i: self.telemetry_callback(msg, did),
                10)

        # --- Publisher zbiorczego statusu ---
        self.swarm_pub = self.create_publisher(SwarmStatus, '/swarm/status', 10)

        # --- SERVICE ---
        self.srv = self.create_service(
            GetSwarmStatus,
            '/swarm/get_status',
            self.get_status_callback)

        # Publikuj zbiorczy status co sekunde
        self.timer = self.create_timer(1.0, self.publish_swarm_status)

        self.get_logger().info(
            f'Swarm Coordinator nasluchuje {self.num_drones} dronow. '
            f'Service /swarm/get_status dostepny.')

    def telemetry_callback(self, msg: DroneTelemetry, drone_id: int):
        self.drone_telemetry[drone_id] = msg

    def publish_swarm_status(self):
        msg = SwarmStatus()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'swarm'
        msg.total_drones = self.num_drones
        msg.active_drones = len(self.drone_telemetry)
        if self.drone_telemetry:
            msg.average_battery = float(
                sum(t.battery_level for t in self.drone_telemetry.values())
                / len(self.drone_telemetry))
        else:
            msg.average_battery = 0.0
        msg.drones = list(self.drone_telemetry.values())
        self.swarm_pub.publish(msg)

    def get_status_callback(self, request, response):
        """Callback SERVICE - klient pyta, my odpowiadamy synchronicznie."""
        response.total_drones = self.num_drones
        response.active_drones = len(self.drone_telemetry)

        if self.drone_telemetry:
            response.average_battery = float(
                sum(t.battery_level for t in self.drone_telemetry.values())
                / len(self.drone_telemetry))
            ready = sum(1 for t in self.drone_telemetry.values()
                        if t.battery_level > 30.0)
            response.mission_readiness = float(ready / self.num_drones * 100.0)
        else:
            response.average_battery = 0.0
            response.mission_readiness = 0.0

        response.status_message = (
            f'Roj operacyjny: {response.active_drones}/{self.num_drones} dronow online, '
            f'gotowosc misyjna {response.mission_readiness:.0f}%')

        self.get_logger().info(f'[SERVICE] Odpowiadam: {response.status_message}')

        if request.include_detailed_telemetry:
            self.get_logger().info('[SERVICE] Klient prosil o pelna telemetrie')

        return response


def main(args=None):
    rclpy.init(args=args)
    node = SwarmCoordinator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
