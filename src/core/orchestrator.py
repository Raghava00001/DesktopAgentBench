"""
Main evaluation orchestrator for DesktopAgentBench.

Implements the core evaluation loop:
    for each task → for each variant → for each repetition:
        setup → inject chaos → run agent → evaluate → record → restore
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.core.config import BenchmarkConfig, load_chaos_profiles_from_dir, ChaosProfileConfig
from src.core.evaluator import Evaluator, TaskResult
from src.core.recorder import Recorder
from src.tasks.schema import Task
from src.tasks.loader import TaskLoader
from src.tasks.split_manager import SplitManager
from src.tasks.variant_generator import VariantGenerator, TaskVariant
from src.chaos.injector import ChaosInjector
from src.agents.adapter import AgentAdapter
from src.agents.registry import get_agent_registry
from src.metrics.calculator import MetricCalculator, BenchmarkMetrics
from src.metrics.reporter import Reporter
from src.platform.process_manager import ProcessManager
from src.platform.window_manager import WindowManager

logger = logging.getLogger(__name__)


@dataclass
class RunContext:
    """Context for a single task-variant-repetition execution."""
    task: Task
    variant: TaskVariant
    repetition: int
    run_id: str
    start_time: float = 0.0


class Orchestrator:
    """
    Main benchmark orchestrator.

    Coordinates the full evaluation pipeline: task loading, variant generation,
    chaos injection, agent execution, evaluation, and reporting.
    """

    def __init__(self, config: BenchmarkConfig) -> None:
        self._config = config
        self._evaluator = Evaluator()
        self._chaos = ChaosInjector()
        self._process_mgr = ProcessManager()
        self._window_mgr = WindowManager()
        self._metric_calc = MetricCalculator(config.confidence_level)
        self._reporter = Reporter(config.results_dir)
        self._all_results: list[TaskResult] = []

    def run(self) -> BenchmarkMetrics:
        """
        Execute the full benchmark and return aggregate metrics.
        """
        run_session_id = f"session_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        logger.info(f"Starting benchmark session: {run_session_id}")
        logger.info(f"Config: split={self._config.split}, reps={self._config.repetitions}")

        # 1. Load tasks
        task_loader = TaskLoader(self._config.tasks_dir)
        split_mgr = SplitManager()

        all_tasks = task_loader.load_all()
        tasks = split_mgr.filter_by_split(all_tasks, self._config.split.value)

        if self._config.task_filter:
            tasks = [t for t in tasks if t.task_id in self._config.task_filter]

        if self._config.category_filter:
            tasks = [t for t in tasks if t.category in self._config.category_filter]

        logger.info(f"Loaded {len(tasks)} tasks")

        if not tasks:
            logger.warning("No tasks to run!")
            return BenchmarkMetrics(
                agent_name="unknown", total_runs=0, total_tasks=0, total_variants=0
            )

        # 2. Load chaos profiles
        chaos_profiles = self._load_chaos_profiles()

        # 3. Generate variants
        variant_gen = VariantGenerator(
            profiles_dir=self._config.chaos_profiles_dir,
            combined_profiles=list(chaos_profiles.values()),
            generate_isolated=self._config.generate_isolated_variants,
        )

        # 4. Load agent
        agent = self._load_agent()
        logger.info(f"Agent: {agent.name()} v{agent.version()}")

        # 5. Execute
        self._all_results = []
        global_start = time.time()
        global_deadline = global_start + (self._config.global_timeout_minutes * 60)

        for task_idx, task in enumerate(tasks):
            logger.info(f"Task [{task_idx+1}/{len(tasks)}]: {task.task_id} — {task.title}")

            variants = variant_gen.generate(task)
            logger.info(f"  Generated {len(variants)} variants")

            for variant in variants:
                for rep in range(self._config.repetitions):
                    if time.time() > global_deadline:
                        logger.warning("Global timeout reached — stopping benchmark")
                        break

                    run_id = f"{run_session_id}/{task.task_id}_{variant.variant_name}_rep{rep}"
                    ctx = RunContext(
                        task=task,
                        variant=variant,
                        repetition=rep,
                        run_id=run_id,
                    )

                    result = self._execute_single_run(ctx, agent)
                    self._all_results.append(result)

                    status = "OK" if result.all_criteria_met else "FAIL"
                    logger.info(
                        f"  [{status}] {variant.variant_name} rep{rep}: "
                        f"steps={result.total_steps}, "
                        f"time={result.elapsed_seconds:.1f}s, "
                        f"partial={result.partial_credit:.2f}"
                    )

        # 6. Compute metrics
        metrics = self._metric_calc.compute_all(self._all_results)

        # 7. Generate reports
        self._reporter.generate_json(metrics, run_session_id)
        report_path = self._reporter.generate_markdown(metrics, run_session_id)
        logger.info(f"Report generated: {report_path}")

        return metrics

    def _execute_single_run(
        self,
        ctx: RunContext,
        agent: AgentAdapter,
    ) -> TaskResult:
        """Execute a single task-variant-repetition."""
        task = ctx.task
        variant = ctx.variant
        recorder = Recorder(self._config.results_dir, ctx.run_id)

        try:
            # --- Setup ---
            pre_state = self._process_mgr.capture_state()

            # Launch required app
            if task.preconditions.apps_required:
                for app in task.preconditions.apps_required:
                    try:
                        self._process_mgr.launch(app, app, wait_seconds=2.0)
                    except Exception as e:
                        logger.warning(f"Failed to launch {app}: {e}")

            # Find target window
            target_window = None
            if task.app:
                target_window = self._window_mgr.wait_for_window(
                    task.app, timeout_seconds=10.0
                )

            # Configure chaos
            self._chaos.configure(
                profile=variant.chaos_profile,
                target_hwnd=target_window.hwnd if target_window else None,
                target_title=target_window.title if target_window else "",
                target_process=task.app,
            )

            # Initialize agent
            agent.setup(
                task_instruction=task.natural_language_instruction,
                app_info={
                    "app": task.app,
                    "category": task.category,
                    "preconditions": task.preconditions.model_dump(),
                },
            )

            # --- Execute ---
            recorder.start(metadata={
                "task_id": task.task_id,
                "variant": variant.variant_name,
                "repetition": ctx.repetition,
                "agent": agent.name(),
                "chaos_profile": variant.chaos_profile.profile_name,
            })

            self._chaos.start()
            ctx.start_time = time.time()
            task_deadline = ctx.start_time + task.timeout_seconds

            step = 0
            timed_out = False
            agent_done = False

            while step < task.max_steps:
                if time.time() > task_deadline:
                    timed_out = True
                    break

                try:
                    screenshot = agent.get_screenshot()
                    a11y_tree = None  # TODO: integrate accessibility tree

                    action = agent.decide(screenshot, a11y_tree, task.natural_language_instruction)

                    success = agent.execute_action(action)

                    # Record step
                    recorder.log_step(
                        action_type=action.action_type,
                        action_parameters=action.parameters,
                        screenshot=screenshot,
                        action_reasoning=action.reasoning,
                        chaos_events_active=self._chaos.get_active_module_names(),
                        agent_state=agent.get_state(),
                        error=None if success else "Action execution failed",
                    )

                    step += 1

                    if agent.signals_done():
                        agent_done = True
                        break

                except Exception as e:
                    recorder.log_step(
                        action_type="error",
                        action_parameters={},
                        error=str(e),
                    )
                    step += 1

            # --- Teardown ---
            self._chaos.stop()
            self._chaos.cleanup()
            recorder.stop()
            agent.teardown()

            post_state = self._process_mgr.capture_state()

            # --- Evaluate ---
            actions = recorder.get_actions()
            chaos_events = self._chaos.get_event_log()

            result = self._evaluator.evaluate(
                task=task,
                variant=variant.variant_name,
                repetition=ctx.repetition,
                run_id=ctx.run_id,
                actions=actions,
                chaos_events=chaos_events,
                agent_name=agent.name(),
                agent_signaled_done=agent_done,
                timed_out=timed_out,
                pre_state=pre_state,
                post_state=post_state,
            )

            return result

        except Exception as e:
            logger.error(f"Run failed: {ctx.run_id}: {e}")
            recorder.stop()

            return TaskResult(
                task_id=task.task_id,
                variant=variant.variant_name,
                repetition=ctx.repetition,
                run_id=ctx.run_id,
                agent_name=agent.name(),
                agent_error=str(e),
                is_unrecoverable=True,
            )

        finally:
            # Cleanup launched processes
            for app in task.preconditions.apps_required:
                self._process_mgr.terminate(app, timeout=3.0)

    def _load_agent(self) -> AgentAdapter:
        """Load the configured agent."""
        registry = get_agent_registry()
        registry.discover_builtins()
        agent_class = registry.load_from_spec(self._config.agent)
        return agent_class()

    def _load_chaos_profiles(self) -> dict[str, ChaosProfileConfig]:
        """Load chaos profiles from config."""
        profiles: dict[str, ChaosProfileConfig] = {}
        profiles_dir = self._config.chaos_profiles_dir

        for name in self._config.chaos_profiles:
            profile_path = profiles_dir / f"{name}.yaml"
            if profile_path.exists():
                from src.core.config import load_chaos_profile
                profiles[name] = load_chaos_profile(profile_path)
            else:
                logger.warning(f"Chaos profile not found: {profile_path}")

        return profiles
