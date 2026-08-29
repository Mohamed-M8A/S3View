import json
import os
import subprocess
import webbrowser
import sys
from core import config
from core.paths import Paths
from core.main import run_logic_pipeline

class PipelineHandler:
    @staticmethod
    def execute(script_content, is_dry_run):
        try:
            current_configuration = config.load_config()
            current_configuration["DRY_RUN"] = bool(is_dry_run)
            config.save_config(current_configuration)
            
            commands_file_path = Paths.resource_path("WORKSPACE/Commands.view")
            with open(commands_file_path, "w", encoding="utf-8-sig") as file: 
                file.write(script_content)
            
            pipeline_output = run_logic_pipeline(is_cli=False)
            
            if isinstance(pipeline_output, dict) and "error" in pipeline_output:
                return {"status": "failed", "message": pipeline_output["error"]}

            serializable_output = json.loads(json.dumps(pipeline_output, default=str))

            return {
                "status": "completed",
                "results": serializable_output.get("results", {}),
                "message": "Execution finished successfully"
            }
        except Exception as error:
            return {"status": "error", "message": str(error)}

    @staticmethod
    def open_reports():
        reports_directory_path = Paths.resource_path("reports")
        if os.path.exists(reports_directory_path):
            try:
                if os.name == "nt":
                    os.startfile(reports_directory_path)
                elif sys.platform == "darwin":
                    subprocess.run(["open", reports_directory_path])
                else:
                    subprocess.run(["xdg-open", reports_directory_path])
                return {"status": "success"}
            except Exception as error:
                return {"status": "error", "message": str(error)}
        return {"status": "error", "message": "Reports directory not found"}

    @staticmethod
    def show_latest():
        html_reports_directory = Paths.resource_path("reports/html")
        if not os.path.exists(html_reports_directory):
            return {"status": "error", "message": "HTML reports directory not found"}
            
        list_of_files = [os.path.join(html_reports_directory, f) for f in os.listdir(html_reports_directory) if f.endswith(".html")]
        
        if not list_of_files:
            return {"status": "error", "message": "No HTML reports available"}
            
        latest_report_file = max(list_of_files, key=os.path.getmtime)
        webbrowser.open(latest_report_file)
        return {"status": "success"}