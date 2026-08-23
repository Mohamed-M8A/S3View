from core.services.macro import MacroService
from core.interpreter import CommandsParser

def worker(connection_manager, execution_context, command_model):
    from core.pipeline import Dispatcher
    
    macro_alias = command_model.src.payload
    macro_history = command_model.extra_metadata.get("__macro_history__", [])
    max_depth = execution_context.get("max_recursion_depth", 15)
    is_simulation = execution_context.get("is_simulation", False)
    
    available_macros = MacroService.load_all()
    target_script = available_macros.get(macro_alias)
    
    if not target_script:
        raise Exception(f"Macro '{macro_alias}' not found.")

    updated_history = macro_history + [macro_alias]
    executable_pipeline = CommandsParser.get_pipeline_commands(target_script)
    
    for task in executable_pipeline:
        action_name = task["action"]
        sub_command_data = task["data"]
        
        if action_name == "macro":
            sub_alias = sub_command_data.src.payload
            is_safe, error_message = MacroService.is_recursion_safe(sub_alias, updated_history, max_depth)
            if not is_safe:
                continue
            sub_command_data.extra_metadata["__macro_history__"] = updated_history

        Dispatcher.dispatch_action(action_name, sub_command_data, connection_manager, is_simulation)
            
    return True