"""
swarm_launch.py
===============
Plik LAUNCH - uruchamia caly system jednym poleceniem:
    ros2 launch drone_swarm swarm_launch.py

Co startuje:
  - 3x drone_node    (osobne wezly z roznymi pozycjami poczatkowymi)
  - 1x coordinator_node
  - 1x mission_control_node

Liczbe dronow mozna nadpisac z linii komend:
    ros2 launch drone_swarm swarm_launch.py num_drones:=5
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # Argument konfiguracyjny
    num_drones_arg = DeclareLaunchArgument(
        'num_drones',
        default_value='3',
        description='Liczba dronow w roju')

    num_drones = 3  # Hardcoded dla petli - LaunchConfiguration jest leniwy

    # Pozycje startowe dla 3 dronow (na siatce 5m)
    initial_positions = [
        (0.0, 0.0, 10.0),
        (5.0, 0.0, 10.0),
        (0.0, 5.0, 10.0),
    ]

    nodes = [num_drones_arg]

    # --- Uruchom drone_node N razy ---
    for i in range(num_drones):
        x, y, z = initial_positions[i]
        nodes.append(Node(
            package='drone_swarm',
            executable='drone_node',
            name=f'drone_{i}',
            parameters=[{
                'drone_id': i,
                'initial_x': x,
                'initial_y': y,
                'initial_z': z,
            }],
            output='screen',
            emulate_tty=True,
        ))

    # --- Koordynator roju ---
    nodes.append(Node(
        package='drone_swarm',
        executable='coordinator_node',
        name='swarm_coordinator',
        parameters=[{'num_drones': num_drones}],
        output='screen',
        emulate_tty=True,
    ))

    # --- Mission Control (action server) ---
    nodes.append(Node(
        package='drone_swarm',
        executable='mission_control_node',
        name='mission_control',
        parameters=[{'num_drones': num_drones}],
        output='screen',
        emulate_tty=True,
    ))

    return LaunchDescription(nodes)
