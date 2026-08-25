from .matchers import FilterMatchers

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

        is_dict = isinstance(resource_metadata, dict)
        normalized_meta = {
            "size": (resource_metadata.get("size", 0) if is_dict else getattr(resource_metadata, "size", 0)) or 0,
            "last_mod": resource_metadata.get("last_mod") if is_dict else getattr(resource_metadata, "last_mod", None),
            "content_type": str((resource_metadata.get("content_type") if is_dict else getattr(resource_metadata, "content_type", None)) or ""),
            "key": str(resource_metadata.get("key", "") if is_dict else getattr(resource_metadata, "key", "")),
            "tier": str(resource_metadata.get("tier", "STANDARD") if is_dict else getattr(resource_metadata, "tier", "STANDARD")),
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

    @staticmethod
    def should_process(logic_expression, resource_metadata, is_inverted=False, total_size=0, total_count=0):
        compiled_groups = LogicProcessor.compile_logic(logic_expression)
        return LogicProcessor.evaluate(compiled_groups, resource_metadata, is_inverted, total_size, total_count)
