# SwarmStatus.msg
# Zbiorczy stan calego roju dronow

std_msgs/Header header
int32 total_drones
int32 active_drones
float32 average_battery
DroneTelemetry[] drones
