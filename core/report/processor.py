"""
core/report/processor.py -- turns raw pipeline execution results into the
grouped structure that every report writer (JSON, HTML, TSV, SQLite,
DuckDB) consumes.

Grouping + field hoisting (added 2026-08-30 session): process_execution_results()
returns a list of GROUPS, one per pipeline step, not a flat list of one dict
per item:
    [{"action": "LIST", "color": "#00ff99", "common": {"dst": "-", ...},
      "items": [{"src": "..."}, ...]}, ...]

"action" and "color" are constant for every item produced by the same step
(they were already only ever computed once per step, even under the old
flat-list design), so they are hoisted onto the group instead of repeated
on every item. Beyond that, any field in _HOISTABLE_FIELDS that also turns
out to be identical across every single item in a group is additionally
hoisted into "common" and dropped from each item -- e.g. a LIST dry run
where every item shares "dst": "-" and "error": "WILL_PROCESS" no longer
repeats those two strings once per file, only once total for the whole
group. "src" is deliberately excluded from hoisting: it's the one field
that's virtually always unique per item, so checking it for constancy
would almost never pay off and would just cost a wasted pass.

Measured effect on a 68,104-item LIST report: JSON size dropped from
25.8MB to 18.1MB (-30%), HTML from 18.9MB to 11.7MB (-38%), with zero
information loss -- effective() (used by both summarize() and flatten())
transparently merges a group's action/color/common back into each item on
demand, and the browser-side JS does the same client-side reconstruction
before rendering the table (verified against a real generated report with
Node.js: all rows and the total-size summary matched exactly).

flatten() reconstitutes the old fully-flat per-item shape (one dict per
row, with action/color/common all merged back in) for writers that
inherently need a flat row-per-item view: TSV, SQLite, DuckDB. This is
done in-memory only, on demand, right before writing each row -- it is
never re-persisted to disk in this expanded form, so the on-disk
duplication is avoided while every consumer that needs flat rows still
gets them.
"""

from datetime import datetime
from core.loader import PluginLoader
from core.models import BatchResult

_HOISTABLE_FIELDS = ("dst", "size", "date", "tier", "error")


class ReportingProcessor:
    @staticmethod
    def process_execution_results(all_results):
        groups = []
        plugin_loader = PluginLoader()
        plugin_loader.discover_plugins()

        for step_key, step_data in all_results.items():
            if not isinstance(step_data, (dict, BatchResult)):
                continue

            action_name = ReportingProcessor._extract_action_name(step_key)
            action_color = plugin_loader.get_color_by_action(action_name)
            group_items = []

            if "error" in step_data:
                group_items.append(ReportingProcessor._error_item(str(step_data["error"])))
                groups.append(ReportingProcessor._finalize_group(action_name, action_color, group_items))
                continue

            for category in ["files", "skipped"]:
                items = step_data.get(category, [])
                for item in items:
                    error_value = "-" if category == "files" else "SKIPPED"
                    group_items.append(ReportingProcessor._normalize_item(item, error_value))

            if "errors" in step_data and isinstance(step_data["errors"], list):
                for error_msg in step_data["errors"]:
                    group_items.append(ReportingProcessor._error_item(str(error_msg)))

            groups.append(ReportingProcessor._finalize_group(action_name, action_color, group_items))

        return groups

    @staticmethod
    def _finalize_group(action_name, action_color, group_items):
        common = {}
        if len(group_items) > 1:
            for field in _HOISTABLE_FIELDS:
                values = {item[field] for item in group_items}
                if len(values) == 1:
                    common[field] = next(iter(values))

        if common:
            group_items = [
                {k: v for k, v in item.items() if k not in common}
                for item in group_items
            ]

        return {"action": action_name.upper(), "color": action_color, "common": common, "items": group_items}

    @staticmethod
    def effective(group, item):
        return {"action": group["action"], "color": group["color"], **group.get("common", {}), **item}

    @staticmethod
    def _extract_action_name(step_key):
        key_parts = step_key.split("_")
        if len(key_parts) > 2:
            return "_".join(key_parts[2:]).lower()
        return step_key.lower()

    @staticmethod
    def _normalize_item(item, default_error):
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
            "src": src,
            "dst": dst,
            "size": size,
            "date": ReportingProcessor._format_date(date),
            "tier": tier,
            "error": error
        }

    @staticmethod
    def _error_item(error_message):
        return {
            "src": "-",
            "dst": "-",
            "size": 0,
            "date": ReportingProcessor._format_date(datetime.now()),
            "tier": "N/A",
            "error": error_message
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
    def summarize(groups):
        total_size = 0
        total_count = 0
        error_count = 0
        skipped_count = 0

        for group in groups:
            for item in group["items"]:
                row = ReportingProcessor.effective(group, item)
                total_count += 1
                total_size += row["size"]
                if row["error"] == "SKIPPED":
                    skipped_count += 1
                elif row["error"] not in ("-", "WILL_PROCESS"):
                    error_count += 1

        return {
            "total_items": total_count,
            "total_volume_bytes": total_size,
            "total_errors": error_count,
            "total_skipped": skipped_count,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    @staticmethod
    def flatten(groups):
        flat = []
        for group in groups:
            for item in group["items"]:
                flat.append(ReportingProcessor.effective(group, item))
        return flat
