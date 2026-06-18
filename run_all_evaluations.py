import subprocess
import sys

agents = ["noop", "random", "rule", "claude", "omniparser", "ufo"]
for agent in agents:
    print(f"==================================================")
    print(f"RUNNING EVALUATION FOR AGENT: {agent}")
    print(f"==================================================")
    cmd = [sys.executable, "bench.py", "run", "--agent", f"builtin:{agent}", "--split", "dev", "-n", "1"]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(e.stdout)
        print(f"ERROR: Agent '{agent}' evaluation failed with exit code {e.returncode}.", file=sys.stderr)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        sys.exit(e.returncode if e.returncode != 0 else 1)
print("ALL AGENTS EVALUATED SUCCESSFULLY!")
