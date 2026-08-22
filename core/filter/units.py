import re
import json
import os

class UnitParsers:
    _SCHEMA_CACHE = None

    @staticmethod
    def _get_schema():
        if UnitParsers._SCHEMA_CACHE is None:
            current_directory = os.path.dirname(os.path.abspath(__file__))
            schema_path = os.path.join(current_directory, "units.json")
            
            if os.path.exists(schema_path):
                try:
                    with open(schema_path, "r", encoding="utf-8") as schema_file:
                        UnitParsers._SCHEMA_CACHE = json.load(schema_file)
                except Exception:
                    UnitParsers._SCHEMA_CACHE = {}
            else:
                UnitParsers._SCHEMA_CACHE = {}
                
        return UnitParsers._SCHEMA_CACHE

    @staticmethod
    def _execute_normalized_parse(input_string, unit_category):
        if not input_string:
            return 0.0
            
        cleaned_input = input_string.strip()
        match = re.match(r"^(\d*\.?\d+)\s*([a-zA-Z]+)$", cleaned_input)
        
        if not match:
            raise ValueError(f"UNIT_PARSER_ERROR: Invalid {unit_category} format -> '{input_string}'")

        numeric_value, unit_string = match.groups()
        schema = UnitParsers._get_schema()
        
        category_aliases = schema.get("ALIASES", {}).get(unit_category, {})
        category_multipliers = schema.get("MULTIPLIERS", {}).get(unit_category, {})

        for standard_key, synonyms in category_aliases.items():
            if unit_string in synonyms:
                multiplier = category_multipliers.get(standard_key, 1)
                return float(numeric_value) * multiplier

        raise ValueError(f"UNIT_PARSER_ERROR: Unit '{unit_string}' is not recognized in {unit_category} schema.")

    @staticmethod
    def parse_size(size_string):
        return UnitParsers._execute_normalized_parse(size_string, "SIZE")

    @staticmethod
    def parse_age(age_string):
        return UnitParsers._execute_normalized_parse(age_string, "AGE")