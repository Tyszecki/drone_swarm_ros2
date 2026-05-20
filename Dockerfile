# Dockerfile - obraz z gotowym workspace ROS2 Jazzy
# Bazujemy na oficjalnym obrazie ROS2 Jazzy (Ubuntu 24.04 w srodku)
FROM ros:jazzy-ros-base

# Etykiety
LABEL maintainer="student@example.com"
LABEL description="Drone Swarm ROS2 simulator - Topics, Services, Actions"

# Instalacja narzedzi do budowania
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-colcon-common-extensions \
    python3-pip \
    python3-rosdep \
    && rm -rf /var/lib/apt/lists/*

# Workspace
WORKDIR /ros2_ws
COPY src /ros2_ws/src

# Budowanie pakietow
RUN /bin/bash -c "source /opt/ros/jazzy/setup.bash && \
    colcon build --symlink-install"

# Automatyczne sourcowanie w kazdym terminalu
RUN echo "source /opt/ros/jazzy/setup.bash" >> /root/.bashrc && \
    echo "source /ros2_ws/install/setup.bash" >> /root/.bashrc

# Skrypt entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
