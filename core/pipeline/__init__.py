# ==================================================================================
# PIPELINE SUBSYSTEM INTERFACE
# ------------------------------------------------------------------------------
# FUNCTIONALITY:
# 1. Public API: Exposes primary pipeline operations (Initialization, Execution, 
#    and Cleanup) to the system bootstrap and CLI layers.
# 2. Dispatcher Gateway: Provides a standardized entry point for executing 
#    individual actions through the PipelineEngine.
# 3. Lifecycle Abstraction: Simplifies environment setup and vault maintenance 
#    by wrapping complex engine calls into atomic functions.
# ==================================================================================

from .engine import PipelineEngine

def init_environment():
    return PipelineEngine.init_environment()

def cleanup_vault():
    return PipelineEngine.cleanup_vault()

def execute_pipeline(pipeline_tasks, connection_manager, is_dry_run, is_cli_mode):
    return PipelineEngine.execute_pipeline(
        pipeline_tasks, 
        connection_manager, 
        is_dry_run, 
        is_cli_mode
    )

class Dispatcher:
    @staticmethod
    def dispatch_action(action_name, command_model, connection_manager, is_dry_run):
        return PipelineEngine._dispatch_task(
            action_name, 
            command_model, 
            connection_manager, 
            is_dry_run
        )