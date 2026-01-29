from dataclasses import dataclass
from typing import Callable, Optional

from ..domain.models import SpaceUrl, RunOptions
from ..infrastructure.session_runtime import SessionOrchestrator, SessionRuntime

@dataclass
class StartSessionResult:
    runtime: SessionRuntime

class StartSessionUseCase:
    def __init__(self, orchestrator: SessionOrchestrator):
        self.orchestrator = orchestrator

    def execute(
        self,
        space: SpaceUrl,
        opts: RunOptions,
        on_log: Optional[Callable[[str], None]] = None
    ) -> StartSessionResult:
        rt = self.orchestrator.start(space, opts, on_log)
        return StartSessionResult(runtime=rt)

class StopSessionUseCase:
    def __init__(self, orchestrator: SessionOrchestrator):
        self.orchestrator = orchestrator

    def execute(self, runtime: SessionRuntime):
        self.orchestrator.stop(runtime)
