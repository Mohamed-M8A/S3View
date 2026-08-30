from .builder import Builder, BuildError

class CommandsParser:
    @classmethod
    def get_pipeline_commands(cls, script_content):
        if not isinstance(script_content, str):
            raise BuildError("COMMANDS_PARSER_ERROR: Script content must be a string.")
        return Builder.build(script_content)