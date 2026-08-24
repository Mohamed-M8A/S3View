from .builder import Builder, BuildError
from .parsers import ActionParsers

class CommandsParser:
    @classmethod
    def get_pipeline_commands(cls, script_content):
        if not isinstance(script_content, str):
            raise BuildError("COMMANDS_PARSER_ERROR: Script content must be a string.")
        return Builder.build(script_content)

class Actions:
    @staticmethod
    def parse_unary(line, meta):
        return ActionParsers.parse_unary(line, meta)

    @staticmethod
    def parse_binary(line, meta):
        return ActionParsers.parse_binary(line, meta)

    @staticmethod
    def parse_reflective(line, meta):
        return ActionParsers.parse_reflective(line, meta)

    @staticmethod
    def parse_flexible(line, meta):
        return ActionParsers.parse_flexible(line, meta)
