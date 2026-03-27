import psutil
import sys
import os
import subprocess
import time

print("Testing psutil functions...")

try:
    cpu = psutil.cpu_percent(interval=None)
    print(f"CPU: {cpu}")
except Exception as e:
    print(f"CPU error: {e}")

try:
    mem = psutil.virtual_memory().percent
    print(f"Memory: {mem}")
except Exception as e:
    print(f"Memory error: {e}")

try:
    load = os.getloadavg()[0]
    print(f"Load: {load}")
except Exception as e:
    print(f"Load error: {e}")

try:
    net = psutil.net_io_counters()
    print(f"Net: {net}")
except Exception as e:
    print(f"Net error: {e}")

try:
    disk = psutil.disk_io_counters()
    print(f"Disk: {disk}")
except Exception as e:
    print(f"Disk error: {e}")

try:
    processes = list(psutil.process_iter())
    print(f"Processes: {len(processes)}")
except Exception as e:
    print(f"Process error: {e}")

print("All tests done.")