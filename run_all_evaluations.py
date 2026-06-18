import subprocess
import sys

agents = ["noop", "random", "rule", "claude", "omniparser", "ufo"]
for agent in agents:
    print(f"==================================================")
    print(f"RUNNING EVALUATION FOR AGENT: {agent}")
    print(f"==================================================")
    cmd = ["python", "bench.py", "run", "--agent", f"builtin:{agent}", "--split", "dev", "-n", "1"]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Agent '{agent}' evaluation failed with exit code {e.returncode}.", file=sys.stderr)
        sys.exit(e.returncode if e.returncode != 0 else 1)
print("ALL AGENTS EVALUATED SUCCESSFULLY!")
