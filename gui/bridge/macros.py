from plugins.macro.engine import MacroStore

class MacroHandler:
    @staticmethod
    def load_all():
        return MacroStore.load_all()

    @staticmethod
    def save(name, code):
        try:
            data = MacroStore.load_all()
            data[name] = code
            if MacroStore.save_all_to_disk(data):
                return {"status": "success"}
            return {"status": "error", "message": "IO_ERROR: Failed to write macros to disk."}
        except Exception as error:
            return {"status": "error", "message": str(error)}

    @staticmethod
    def delete(name):
        try:
            data = MacroStore.load_all()
            if name in data:
                del data[name]
                if MacroStore.save_all_to_disk(data):
                    return {"status": "success"}
                return {"status": "error", "message": "IO_ERROR: Failed to update macros file."}
            return {"status": "success"}
        except Exception as error:
            return {"status": "error", "message": str(error)}