from .engine import PipelineEngine

def init_environment():
    return PipelineEngine.init_environment()

def cleanup_vault():
    return PipelineEngine.cleanup_vault()

def execute_pipeline(pipeline_tasks, is_dry_run, is_cli_mode):
    return PipelineEngine.execute_pipeline(
        pipeline_tasks, 
        is_dry_run, 
        is_cli_mode
    )