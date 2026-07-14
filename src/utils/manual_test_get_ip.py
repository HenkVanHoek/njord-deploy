import socket

# Current method
hostname = socket.gethostname()
local_ip = socket.gethostbyname(hostname)
print(f"Hostname method: {hostname} -> {local_ip}")

# Improved method
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.connect(("8.8.8.8", 80))
    better_ip = s.getsockname()[0]
print(f"Socket method: {better_ip}")
