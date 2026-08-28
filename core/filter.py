import re
from datetime import datetime, timezone


class UnitParsers:
    SIZE_MAP = {
        'b': 1, 'B': 1,
        'kb': 1024, 'KB': 1024,
        'mb': 1048576, 'MB': 1048576,
        'gb': 1073741824, 'GB': 1073741824,
        'tb': 1099511627776, 'TB': 1099511627776,
        'pb': 1125899906842624, 'PB': 1125899906842624
    }

    AGE_MAP = {
        's': 1, 'S': 1,
        'm': 60, 'M': 60,
        'h': 3600, 'H': 3600,
        'd': 86400, 'D': 86400,
        'w': 604800, 'W': 604800,
        'mo': 2592000, 'MO': 2592000,
        'y': 31536000, 'Y': 31536000
    }

    @staticmethod
    def _execute_strict_parse(input_string, mapping, category_name):
        if not input_string:
            return 0.0
            
        cleaned = input_string.strip()
        match = re.match(r"^(\d*\.?\d+)\s*([a-zA-Z]+)$", cleaned)
        
        if not match:
            raise ValueError(f"STRICT_UNIT_ERROR: Invalid {category_name} format -> '{cleaned}'")
            
        numeric_value, unit_string = match.groups()
        
        if unit_string in mapping:
            return float(numeric_value) * mapping[unit_string]
            
        raise ValueError(f"STRICT_UNIT_ERROR: Unit '{unit_string}' is unsupported for {category_name}.")

    @staticmethod
    def parse_size(size_string):
        return UnitParsers._execute_strict_parse(size_string, UnitParsers.SIZE_MAP, "SIZE")

    @staticmethod
    def parse_age(age_string):
        return UnitParsers._execute_strict_parse(age_string, UnitParsers.AGE_MAP, "AGE")


class FilterMatchers:
    @staticmethod
    def _compare_values(current_value, operator, target_threshold):
        if operator == ">=": return current_value >= target_threshold
        if operator == "<=": return current_value <= target_threshold
        if operator == ">": return current_value > target_threshold
        if operator == "<": return current_value < target_threshold
        if operator == "=": return current_value == target_threshold
        return False

    @staticmethod
    def compile_rule(rule_string):
        numeric_pattern = r"(>=|<=|>|<|=)"
        separator = ":"
        
        if rule_string.startswith("regex:"):
            pattern = rule_string.split(separator, 1)[1].strip()
            return {"type": "regex", "value": re.compile(pattern)}
            
        if re.search(r"^size" + numeric_pattern, rule_string):
            match = re.search(r"^size" + numeric_pattern + r"\s*(.+)", rule_string)
            op, val = match.groups()
            return {"type": "size", "operator": op, "value": UnitParsers._execute_strict_parse(val.strip(), UnitParsers.SIZE_MAP, "SIZE")}
            
        if re.search(r"^sum" + numeric_pattern, rule_string):
            match = re.search(r"^sum" + numeric_pattern + r"\s*(.+)", rule_string)
            op, val = match.groups()
            return {"type": "sum", "operator": op, "value": UnitParsers._execute_strict_parse(val.strip(), UnitParsers.SIZE_MAP, "SIZE")}
            
        if re.search(r"^count" + numeric_pattern, rule_string):
            match = re.search(r"^count" + numeric_pattern + r"\s*(.+)", rule_string)
            op, val = match.groups()
            return {"type": "count", "operator": op, "value": float(val.strip())}
            
        if re.search(r"^age" + numeric_pattern, rule_string):
            match = re.search(r"^age" + numeric_pattern + r"\s*(.+)", rule_string)
            op, val = match.groups()
            return {"type": "age", "operator": op, "value": UnitParsers._execute_strict_parse(val.strip(), UnitParsers.AGE_MAP, "AGE")}
            
        if re.search(r"^date" + separator, rule_string):
            date_data = rule_string.split(separator, 1)[1].strip()
            if ".." in date_data:
                start_str, end_str = date_data.split("..", 1)
                start_dt = datetime.strptime(start_str.strip(), "%Y-%m-%d").replace(tzinfo=timezone.utc)
                end_dt = datetime.strptime(end_str.strip(), "%Y-%m-%d").replace(tzinfo=timezone.utc)
                return {"type": "date_range", "start": start_dt, "end": end_dt}
            else:
                exact_dt = datetime.strptime(date_data.strip(), "%Y-%m-%d").date()
                return {"type": "date_exact", "value": exact_dt}
                
        for category in ["type", "tier", "sname", "ename"]:
            if rule_string.startswith(category + separator):
                values = [v.strip() for v in rule_string.split(separator, 1)[1].split(",") if v.strip()]
                return {"type": category, "value": values}
                
        return None

    @staticmethod
    def match_compiled(rule, metadata, stats):
        rtype = rule["type"]
        
        if rtype == "regex":
            return bool(rule["value"].search(metadata['key']))
            
        if rtype == "size":
            return FilterMatchers._compare_values(metadata['size'], rule["operator"], rule["value"])
            
        if rtype == "sum":
            return FilterMatchers._compare_values(stats['total_size'], rule["operator"], rule["value"])
            
        if rtype == "count":
            return FilterMatchers._compare_values(stats['total_count'], rule["operator"], rule["value"])
            
        if rtype == "age":
            if not metadata['last_mod']: return False
            diff = (datetime.now(timezone.utc) - metadata['last_mod']).total_seconds()
            return FilterMatchers._compare_values(diff, rule["operator"], rule["value"])
            
        if rtype == "date_range":
            return rule["start"] <= metadata['last_mod'] <= rule["end"]
            
        if rtype == "date_exact":
            return metadata['last_mod'].date() == rule["value"]
            
        if rtype == "type":
            if metadata['key'].endswith('/'): return False
            return any(target in metadata['content_type'] for target in rule["value"])
            
        if rtype == "tier":
            return any(target in metadata['tier'] for target in rule["value"])
            
        if rtype == "sname":
            return any(metadata['key'].split("/")[-1].startswith(target) for target in rule["value"])
            
        if rtype == "ename":
            return any(metadata['key'].split("/")[-1].endswith(target) for target in rule["value"])
            
        return False


class LogicProcessor:
    @staticmethod
    def compile_logic(logic_expression):
        if not logic_expression or not logic_expression.strip():
            return None
            
        rule_body = logic_expression.strip()
        or_groups = [group.strip() for group in rule_body.split("|") if group.strip()]
        compiled_package = []
        
        for group_string in or_groups:
            and_rules = [rule.strip() for rule in group_string.split("&") if rule.strip()]
            group_list = []
            
            for raw_rule in and_rules:
                is_rule_inverted = False
                actual_rule_text = raw_rule
                
                if raw_rule.startswith("!"):
                    is_rule_inverted = True
                    actual_rule_text = raw_rule[1:].strip()
                    
                compiled_rule = FilterMatchers.compile_rule(actual_rule_text)
                if compiled_rule:
                    compiled_rule["rule_inv"] = is_rule_inverted
                    group_list.append(compiled_rule)
                    
            if group_list:
                compiled_package.append(group_list)
                
        return compiled_package

    @staticmethod
    def evaluate(compiled_groups, resource_metadata, is_inverted=False, total_size=0, total_count=0):
        if not compiled_groups:
            return not is_inverted
        
        normalized_meta = {
            "size": resource_metadata.size,
            "last_mod": resource_metadata.last_mod,
            "content_type": str(resource_metadata.content_type),
            "key": str(resource_metadata.key),
            "tier": str(resource_metadata.tier),
        }
        
        pipeline_stats = {"total_size": total_size, "total_count": total_count}
        match_result = False
        
        for group in compiled_groups:
            all_rules_passed = True
            
            for rule in group:
                is_match = FilterMatchers.match_compiled(rule, normalized_meta, pipeline_stats)
                
                if rule.get("rule_inv"): 
                    is_match = not is_match
                    
                if not is_match:
                    all_rules_passed = False
                    break
                    
            if all_rules_passed:
                match_result = True
                break
                
        return (not match_result) if is_inverted else match_result


class FilterEngine:
    @staticmethod
    def compile_logic(logic_expression):
        return LogicProcessor.compile_logic(logic_expression)

    @classmethod
    def should_process_compiled(cls, compiled_logic, object_metadata, is_inverted=False, total_size=0, total_count=0):
        return LogicProcessor.evaluate(compiled_logic, object_metadata, is_inverted, total_size, total_count)