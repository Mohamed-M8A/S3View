import os
from core.paths import Paths

class MacroOps:
    @staticmethod
    def get_macros_path():
        return Paths.resource_path("WORKSPACE/Macros.vmacro")

    @staticmethod
    def load_all():
        physical_path = MacroOps.get_macros_path()
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
        physical_path = MacroOps.get_macros_path()
        try:
            with open(physical_path, "w", encoding="utf-8-sig") as macro_file:
                for macro_name, macro_code in macros_dictionary.items():
                    macro_file.write(f"# macro: {macro_name}\n{macro_code}\n\n")
            return True
        except Exception:
            return False

    @staticmethod
    def is_recursion_safe(macro_alias, expansion_history, max_nesting_depth):
        if macro_alias in expansion_history: 
            return False, "CIRCULAR_LOOP_DETECTED"
            
        if len(expansion_history) >= max_nesting_depth: 
            return False, "MAX_RECURSION_DEPTH_REACHED"
            
        return True, "SAFE"