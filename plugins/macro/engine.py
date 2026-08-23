import os
from core.paths import Paths
from core.interpreter import CommandsParser


class MacroStore:

    @staticmethod
    def get_macros_path():
        return Paths.resource_path("WORKSPACE/Macros.vmacro")

    @staticmethod
    def load_all():
        physical_path = MacroStore.get_macros_path()
        if not os.path.exists(physical_path):
            return {}

        registered_macros = {}
        current_macro_name = None
        current_macro_buffer = []

        try:
            with open(physical_path, "r", encoding="utf-8-sig") as macro_file:
                for line in macro_file:
                    stripped_line = line.strip()

                    if stripped_line.startswith("# macro:"):
                        if current_macro_name:
                            registered_macros[current_macro_name] = "\n".join(current_macro_buffer).strip()

                        current_macro_name = stripped_line.split(":", 1)[1].strip()
                        current_macro_buffer = []
                    else:
                        if current_macro_name is not None:
                            current_macro_buffer.append(line.rstrip())

                if current_macro_name:
                    registered_macros[current_macro_name] = "\n".join(current_macro_buffer).strip()
        except Exception:
            pass

        return registered_macros

    @staticmethod
    def save_all_to_disk(macros_dictionary):
        physical_path = MacroStore.get_macros_path()
        temporary_path = f"{physical_path}.tmp"

        try:
            with open(temporary_path, "w", encoding="utf-8-sig") as macro_file:
                for macro_name, macro_code in macros_dictionary.items():
                    macro_file.write(f"# macro: {macro_name}\n{macro_code}\n\n")
            os.replace(temporary_path, physical_path)
            return True
        except Exception:
            if os.path.exists(temporary_path):
                os.remove(temporary_path)
            return False

    @staticmethod
    def is_recursion_safe(macro_alias, expansion_history, max_nesting_depth):
        if macro_alias in expansion_history:
            return False, "CIRCULAR_LOOP_DETECTED"

        if len(expansion_history) >= max_nesting_depth:
            return False, "MAX_RECURSION_DEPTH_REACHED"

        return True, "SAFE"


def worker(connection_manager, execution_context, command_model):
    from core.pipeline import Dispatcher

    macro_alias = command_model.src.payload
    macro_history = command_model.extra_metadata.get("__macro_history__", [])
    max_depth = execution_context.get("max_recursion_depth", 15)
    is_simulation = execution_context.get("is_simulation", False)

    available_macros = MacroStore.load_all()
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
            is_safe, error_message = MacroStore.is_recursion_safe(sub_alias, updated_history, max_depth)
            if not is_safe:
                continue
            sub_command_data.extra_metadata["__macro_history__"] = updated_history

        Dispatcher.dispatch_action(action_name, sub_command_data, connection_manager, is_simulation)

    return True