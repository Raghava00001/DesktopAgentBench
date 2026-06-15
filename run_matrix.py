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
    
    # 1. Run No-op agent
    print("\n--- Running No-op Agent Matrix ---")
    run_command([sys.executable, "bench.py", "run", "--agent", "builtin:noop", "--repetitions", "1"])
    
    # 2. Run Random agent
    print("\n--- Running Random Agent Matrix ---")
    run_command([sys.executable, "bench.py", "run", "--agent", "builtin:random", "--repetitions", "1"])
    
    # 3. Run Rule agent
    print("\n--- Running Rule Agent Matrix ---")
    run_command([sys.executable, "bench.py", "run", "--agent", "builtin:rule", "--repetitions", "1"])
    
    print("\n=== FULL BENCHMARK MATRIX RUN COMPLETE ===")

if __name__ == "__main__":
    main()
