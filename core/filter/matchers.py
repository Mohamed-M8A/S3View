import re
from datetime import datetime, timezone
from .units import UnitParsers

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
            return {"type": "size", "operator": op, "value": UnitParsers.parse_size(val.strip())}

        if re.search(r"^sum" + numeric_pattern, rule_string):
            match = re.search(r"^sum" + numeric_pattern + r"\s*(.+)", rule_string)
            op, val = match.groups()
            return {"type": "sum", "operator": op, "value": UnitParsers.parse_size(val.strip())}

        if re.search(r"^count" + numeric_pattern, rule_string):
            match = re.search(r"^count" + numeric_pattern + r"\s*(.+)", rule_string)
            op, val = match.groups()
            return {"type": "count", "operator": op, "value": float(val.strip())}

        if re.search(r"^age" + numeric_pattern, rule_string):
            match = re.search(r"^age" + numeric_pattern + r"\s*(.+)", rule_string)
            op, val = match.groups()
            return {"type": "age", "operator": op, "value": UnitParsers.parse_age(val.strip())}

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