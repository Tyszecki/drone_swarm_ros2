import os
from glob import glob
from setuptools import setup, find_packages

package_name = 'drone_swarm'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Student',
    maintainer_email='student@example.com',
    description='Symulator roju dronow - demonstracja Topics, Services, Actions w ROS2',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'drone_node = drone_swarm.drone_node:main',
            'coordinator_node = drone_swarm.coordinator_node:main',
            'mission_control_node = drone_swarm.mission_control_node:main',
            'demo_mission_client = drone_swarm.demo_mission_client:main',
        ],
    },
)
