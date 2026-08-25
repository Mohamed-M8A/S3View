from abc import ABC, abstractmethod
from typing import Any, Dict
from .structures import CommandModel, TaskResponse

class BasePlugin(ABC):
    def __init__(self, manifest: Dict[str, Any], folder_path: str):
        self.manifest = manifest
        self.folder_path = folder_path

    @property
    def action_name(self) -> str:
        behavior_settings = self.manifest.get("behavior", {})
        return behavior_settings.get("action_name", "unknown")

    @property
    def supports_simulation(self) -> bool:
        behavior_settings = self.manifest.get("behavior", {})
        return behavior_settings.get("supports_simulation", True)

    def execute(self, connection_manager: Any, command_model: CommandModel):
        from core.execution import ExecutionEngine
        return ExecutionEngine.run_smart_task(
            connection_manager,
            command_model,
            self.worker,
            self,
            is_simulation=False
        )

    def simulate(self, connection_manager: Any, command_model: CommandModel):
        from core.execution import ExecutionEngine
        return ExecutionEngine.run_smart_task(
            connection_manager,
            command_model,
            None,
            self,
            is_simulation=True
        )

    @abstractmethod
    def worker(self, connection_manager: Any, context: Dict[str, Any], command_model: CommandModel) -> TaskResponse:
        pass