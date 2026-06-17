"""
Process manager for DesktopAgentBench.

Handles launching, monitoring, and terminating applications
required by benchmark tasks.
"""

from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ManagedProcess:
    """A process launched and managed by the benchmark."""
    name: str
    process: subprocess.Popen
    pid: int
    launched_at: float
    command: list[str]


class ProcessManager:
    """Launches and manages application processes for benchmark tasks."""

    def __init__(self) -> None:
        self._processes: dict[str, ManagedProcess] = {}

    def launch(
        self,
        name: str,
        command: str | list[str],
        wait_seconds: float = 2.0,
        cwd: str | Path | None = None,
    ) -> ManagedProcess:
        """
        Launch an application process.

        Args:
            name: Friendly name for the process.
            command: Command to execute (string or list).
            wait_seconds: Time to wait for the process to start.
            cwd: Working directory for the process.

        Returns:
            ManagedProcess record.
        """
        if isinstance(command, str):
            command_list = command.split()
        else:
            command_list = list(command)

        logger.info(f"Launching process '{name}': {command_list}")

        try:
            proc = subprocess.Popen(
                command_list,
                cwd=cwd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )

            time.sleep(wait_seconds)

            managed = ManagedProcess(
                name=name,
                process=proc,
                pid=proc.pid,
                launched_at=time.time(),
                command=command_list,
            )
            self._processes[name] = managed
            logger.info(f"Process '{name}' launched with PID {proc.pid}")
            return managed

        except Exception as e:
            logger.error(f"Failed to launch '{name}': {e}")
            raise

    def terminate(self, name: str, timeout: float = 5.0) -> bool:
        """
        Gracefully terminate a managed process.

        Falls back to force-kill after timeout.
        """
        managed = self._processes.get(name)
        if not managed:
            logger.warning(f"Process '{name}' not found in managed processes")
            return False

        proc = managed.process

        try:
            proc.terminate()
            try:
                proc.wait(timeout=timeout)
                logger.info(f"Process '{name}' terminated gracefully")
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=0.2)
                logger.warning(f"Process '{name}' force-killed after timeout")

            del self._processes[name]
            return True

        except Exception as e:
            logger.error(f"Failed to terminate '{name}': {e}")
            return False

    def terminate_all(self) -> None:
        """Terminate all managed processes."""
        names = list(self._processes.keys())
        for name in names:
            self.terminate(name)

    def is_running(self, name: str) -> bool:
        """Check if a managed process is still running."""
        managed = self._processes.get(name)
        if not managed:
            return False
        return managed.process.poll() is None

    def get_pid(self, name: str) -> int | None:
        """Get the PID of a managed process."""
        managed = self._processes.get(name)
        return managed.pid if managed else None

    def kill_by_name(self, process_name: str) -> bool:
        """Kill a process by its executable name using taskkill."""
        try:
            result = subprocess.run(
                ["taskkill", "/IM", process_name, "/F"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"taskkill failed for {process_name}: {e}")
            return False

    def capture_state(self) -> dict[str, Any]:
        """Capture current process state for evaluation diffing."""
        try:
            import psutil
            processes = []
            for proc in psutil.process_iter(['name']):
                try:
                    name = proc.info['name']
                    if name:
                        processes.append(name)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            return {"processes": sorted(set(processes))}
        except Exception:
            return {"processes": []}
