"""
Script to run the full benchmark evaluation matrix sequentially for all 3 agents.
"""

from __future__ import annotations

import subprocess
import sys
import time

def run_command(cmd: list[str]) -> str:
    print(f"Running command: {' '.join(cmd)}")
    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - start
    print(f"Finished in {elapsed:.2f}s")
    if result.returncode != 0:
        print(f"Error executing command: {result.stderr}")
    return result.stdout

def main():
    print("=== STARTING FULL BENCHMARK MATRIX RUN ===")
    
    agents = ["noop", "random", "rule", "ufo", "claude", "omniparser"]
    for agent in agents:
        print(f"\n--- Running {agent.upper()} Agent Matrix ---")
        run_command([sys.executable, "bench.py", "run", "--agent", f"builtin:{agent}", "--repetitions", "1"])
        
    print("\n=== FULL BENCHMARK MATRIX RUN COMPLETE ===")

if __name__ == "__main__":
    main()
