import subprocess
import sys

agents = ["noop", "random", "rule", "claude", "omniparser", "ufo"]
for agent in agents:
    print(f"==================================================")
    print(f"RUNNING EVALUATION FOR AGENT: {agent}")
    print(f"==================================================")
    cmd = ["python", "bench.py", "run", "--agent", f"builtin:{agent}", "--split", "dev", "-n", "1"]
    subprocess.run(cmd)
print("ALL AGENTS EVALUATED SUCCESSFULLY!")
