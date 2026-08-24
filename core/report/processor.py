from datetime import datetime
from core.loader import PluginLoader


class ReportingProcessor:
    @staticmethod
    def process_execution_results(all_results):
        standardized_entries = []
        plugin_loader = PluginLoader()
        plugin_loader.discover_plugins()

        for step_key, step_data in all_results.items():
            if not isinstance(step_data, dict):
                continue

            action_name = ReportingProcessor._extract_action_name(step_key)
            action_color = plugin_loader.get_color_by_action(action_name)

            if "error" in step_data:
                standardized_entries.append(
                    ReportingProcessor._create_error_entry(
                        action_name,
                        str(step_data["error"]),
                        action_color
                    )
                )
                continue

            for category in ["files", "skipped"]:
                items = step_data.get(category, [])
                for item in items:
                    error_value = "-" if category == "files" else "SKIPPED"
                    standardized_entries.append(
                        ReportingProcessor._normalize_item(
                            item,
                            action_name,
                            action_color,
                            error_value
                        )
                    )

            if "errors" in step_data and isinstance(step_data["errors"], list):
                for error_msg in step_data["errors"]:
                    standardized_entries.append(
                        ReportingProcessor._create_error_entry(
                            action_name,
                            str(error_msg),
                            action_color
                        )
                    )

        return standardized_entries

    @staticmethod
    def _extract_action_name(step_key):
        key_parts = step_key.split("_")
        if len(key_parts) > 2:
            return "_".join(key_parts[2:]).lower()
        return step_key.lower()

    @staticmethod
    def _normalize_item(item, action, color, default_error):
        src = "-"
        dst = "-"
        size = 0
        date = "N/A"
        tier = "N/A"
        error = default_error

        if hasattr(item, "status"):
            src = item.src or "-"
            dst = item.dst or "-"
            size = item.size if isinstance(item.size, (int, float)) else 0
            date = item.date
            tier = item.tier
            error = item.error or default_error
        elif isinstance(item, dict):
            src = item.get("src", item.get("key", "-"))
            dst = item.get("dst", "-")
            size = item.get("size", item.get("bytes", 0))
            date = item.get("date", item.get("last_mod", "N/A"))
            tier = item.get("tier", "N/A")
            error = item.get("error", default_error)

        return {
            "action": action.upper(),
            "src": src,
            "dst": dst,
            "size": size,
            "date": ReportingProcessor._format_date(date),
            "tier": tier,
            "error": error,
            "color": color
        }

    @staticmethod
    def _create_error_entry(action, error_message, color):
        return {
            "action": action.upper(),
            "src": "-",
            "dst": "-",
            "size": 0,
            "date": ReportingProcessor._format_date(datetime.now()),
            "tier": "N/A",
            "error": error_message,
            "color": color
        }

    @staticmethod
    def _format_date(date_input):
        if isinstance(date_input, datetime):
            return date_input.strftime("%Y-%m-%d %H:%M:%S")
        if hasattr(date_input, "strftime"):
            return date_input.strftime("%Y-%m-%d %H:%M:%S")

        date_string = str(date_input)
        if len(date_string) <= 8 and ":" in date_string:
            prefix = datetime.now().strftime("%Y-%m-%d")
            return f"{prefix} {date_string}"

        return date_string

    @staticmethod
    def summarize(standardized_list):
        total_size = 0
        total_count = 0
        error_count = 0
        skipped_count = 0

        for entry in standardized_list:
            total_count += 1
            total_size += entry["size"]
            if entry["error"] == "SKIPPED":
                skipped_count += 1
            elif entry["error"] != "-":
                error_count += 1

        return {
            "total_items": total_count,
            "total_volume_bytes": total_size,
            "total_errors": error_count,
            "total_skipped": skipped_count,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
