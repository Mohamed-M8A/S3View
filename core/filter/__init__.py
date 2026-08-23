from .units import UnitParsers
from .processor import LogicProcessor

class FilterEngine:
    @staticmethod
    def parse_size(size_string):
        return UnitParsers.parse_size(size_string)

    @staticmethod
    def parse_age(age_string):
        return UnitParsers.parse_age(age_string)

    @staticmethod
    def compile_logic(logic_expression):
        return LogicProcessor.compile_logic(logic_expression)

    @classmethod
    def should_process(cls, logic_string, object_metadata, is_inverted=False, total_size=0, total_count=0):
        return LogicProcessor.should_process(
            logic_string, 
            object_metadata, 
            is_inverted, 
            total_size, 
            total_count
        )

    @classmethod
    def should_process_compiled(cls, compiled_logic, object_metadata, is_inverted=False, total_size=0, total_count=0):
        return LogicProcessor.evaluate(
            compiled_logic,
            object_metadata,
            is_inverted,
            total_size,
            total_count
        )
