from core.services.macro import MacroService

class MacroHandler:
    @staticmethod
    def load_all():
        return MacroService.load_all()

    @staticmethod
    def save(name, code):
        try:
            data = MacroService.load_all()
            data[name] = code
            if MacroService.save_all_to_disk(data):
                return {"status": "success"}
            return {"status": "error", "message": "Failed to write macros to disk."}
        except Exception as error:
            return {"status": "error", "message": str(error)}

    @staticmethod
    def delete(name):
        try:
            data = MacroService.load_all()
            if name in data:
                del data[name]
                if MacroService.save_all_to_disk(data):
                    return {"status": "success"}
                return {"status": "error", "message": "Failed to update macros file."}
            return {"status": "success"}
        except Exception as error:
            return {"status": "error", "message": str(error)}