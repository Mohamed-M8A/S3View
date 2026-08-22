from .orchestrator import TaskOrchestrator

class ExecutionEngine:
    @staticmethod
    def run_smart_task(connection_manager, command_model, worker_callback, plugin_instance, is_simulation=False, prebuilt_inventory=None):
        from core.pipeline.scan import UniversalScanner
        
        source_object = command_model.src
        
        if prebuilt_inventory is None:
            execution_stats = {"total_size": 0, "count": 0}
            inventory = UniversalScanner.scan(connection_manager, source_object, command_model, execution_stats)
        else:
            inventory = prebuilt_inventory

        if not inventory:
            return {"files": [], "errors": [], "total_size": 0, "count": 0}

        return TaskOrchestrator.process_batch(
            connection_manager, 
            inventory, 
            command_model, 
            worker_callback, 
            plugin_instance.manifest, 
            is_simulation
        )