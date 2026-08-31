import os
import json
import csv
import sqlite3
from datetime import datetime
from core import config
from core.paths import Paths
from core.report.template.css_assets import CSS
from core.report.template.js_assets import JS
from core.report.template.scaffold import HTML
from core.report.processor import ReportingProcessor

class ReportingWriters:
    @staticmethod
    def ensure_directories():
        base = Paths.resource_path("reports")
        dirs = {
            "html": os.path.join(base, "html"),
            "tsv": os.path.join(base, "tsv"),
            "json": os.path.join(base, "json"),
            "sqlite": os.path.join(base, "sqlite"),
            "duckdb": os.path.join(base, "duckdb"),
            "network": os.path.join(base, "network"),
            "logs": os.path.join(base, "logs")
        }
        for path in dirs.values():
            os.makedirs(path, exist_ok=True)
        return dirs

    @staticmethod
    def write_all(standardized_groups, summary, is_simulation=False):
        settings = config.load_config()
        if not settings.get("ENABLE_REPORTS", True):
            return

        dirs = ReportingWriters.ensure_directories()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        mode_prefix = "sim_report" if is_simulation else "report"

        report_payload = {
            "summary": summary,
            "groups": standardized_groups
        }

        if settings.get("REPORT_JSON", True):
            ReportingWriters._safe_write(
                ReportingWriters._write_json, "json",
                report_payload, dirs["json"], f"{mode_prefix}_{timestamp}.json"
            )

        if settings.get("REPORT_TSV", True):
            ReportingWriters._safe_write(
                ReportingWriters._write_tsv, "tsv",
                ReportingProcessor.flatten(standardized_groups), dirs["tsv"], f"{mode_prefix}_{timestamp}.tsv"
            )

        if settings.get("REPORT_HTML", True):
            ReportingWriters._safe_write(
                ReportingWriters._write_html, "html",
                report_payload, dirs["html"], f"{mode_prefix}_{timestamp}.html"
            )

        if settings.get("REPORT_SQLITE", False):
            ReportingWriters._safe_write(
                ReportingWriters._write_sqlite, "sqlite",
                ReportingProcessor.flatten(standardized_groups), dirs["sqlite"], "history.sqlite"
            )

        if settings.get("REPORT_DUCKDB", False):
            ReportingWriters._safe_write(
                ReportingWriters._write_duckdb, "duckdb",
                ReportingProcessor.flatten(standardized_groups), dirs["duckdb"], "analytics.duckdb"
            )

    @staticmethod
    def _safe_write(writer_function, format_name, *args):
        try:
            writer_function(*args)
        except Exception as exc:
            ReportingWriters.save_error_log(str(exc), f"report_write_{format_name}")

    @staticmethod
    def _write_json(data, folder, filename):
        path = os.path.join(folder, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    @staticmethod
    def _write_tsv(entries, folder, filename):
        if not entries:
            return
        path = os.path.join(folder, filename)
        headers = entries[0].keys()
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=headers, delimiter="\t")
            writer.writeheader()
            writer.writerows(entries)

    @staticmethod
    def _write_html(payload, folder, filename):
        path = os.path.join(folder, filename)
        serialized_data = json.dumps(payload, default=str)
        safe_serialized_data = serialized_data.replace("</", "<\\/")
        final_js = JS.replace("JSON_DATA", safe_serialized_data)

        mode = payload["summary"].get("execution_mode", "Execution")

        html_content = HTML.format(
            title=f"S3View {mode}",
            timestamp=payload["summary"]["timestamp"],
            count=payload["summary"]["total_items"],
            status="SUCCESS" if payload["summary"]["total_errors"] == 0 else "COMPLETED_WITH_ERRORS",
            css=CSS,
            js=final_js
        )
        with open(path, "w", encoding="utf-8") as f:
            f.write(html_content)

    @staticmethod
    def _write_sqlite(entries, folder, db_name):
        if not entries:
            return
        path = os.path.join(folder, db_name)
        conn = sqlite3.connect(path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transfers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT,
                    src TEXT,
                    dst TEXT,
                    size INTEGER,
                    date TEXT,
                    tier TEXT,
                    error TEXT,
                    color TEXT,
                    report_timestamp TEXT
                )
            """)

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            batch = [
                (e["action"], e["src"], e["dst"], e["size"], e["date"], e["tier"], e["error"], e["color"], now)
                for e in entries
            ]

            cursor.executemany("""
                INSERT INTO transfers (action, src, dst, size, date, tier, error, color, report_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)

            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _write_duckdb(entries, folder, db_name):
        if not entries:
            return
        try:
            import duckdb
        except ImportError:
            return

        path = os.path.join(folder, db_name)
        conn = duckdb.connect(path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transfers (
                    action VARCHAR,
                    src VARCHAR,
                    dst VARCHAR,
                    size BIGINT,
                    date VARCHAR,
                    tier VARCHAR,
                    error VARCHAR,
                    color VARCHAR,
                    report_timestamp TIMESTAMP
                )
            """)

            now = datetime.now()
            batch = [
                (e["action"], e["src"], e["dst"], e["size"], e["date"], e["tier"], e["error"], e["color"], now)
                for e in entries
            ]

            conn.executemany("""
                INSERT INTO transfers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)
            
        finally:
            conn.close()

    @staticmethod
    def save_network_report(logs):
        if not logs:
            return
        dirs = ReportingWriters.ensure_directories()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(dirs["network"], f"traffic_{timestamp}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=4, default=str)

    @staticmethod
    def save_error_log(message, context="General"):
        dirs = ReportingWriters.ensure_directories()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(dirs["logs"], f"error_{timestamp}.log")
        log_entry = f"[{datetime.now()}] context: {context}\nerror: {message}\n{'-'*40}\n"
        with open(path, "a", encoding="utf-8") as f:
            f.write(log_entry)
        return path