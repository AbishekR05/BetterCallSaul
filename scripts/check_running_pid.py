import psutil

for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent']):
    if proc.info['name'] and 'python' in proc.info['name'].lower():
        cmd = " ".join(proc.info['cmdline']) if proc.info['cmdline'] else ""
        print(f"PID: {proc.info['pid']} | CMD: {cmd[:80]}")
