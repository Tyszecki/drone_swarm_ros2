# DroneTelemetry.msg
# Telemetria pojedynczego drona w roju
# Wzorowana na rzeczywistych systemach PX4/MAVROS

std_msgs/Header header
int32 drone_id
geometry_msgs/Point position    # x, y, z w metrach (lokalny układ ENU)
float32 battery_level            # 0.0 - 100.0 (procent)
float32 speed                    # m/s
string status                    # "IDLE" | "MOVING" | "RETURNING" | "CHARGING"
