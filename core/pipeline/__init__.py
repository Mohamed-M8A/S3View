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