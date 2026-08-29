from .processor import ReportingProcessor
from .writers import ReportingWriters

class Reporting:
    @staticmethod
    def save_error_log(error_msg, action_context="General"):
        return ReportingWriters.save_error_log(error_msg, action_context)

    @staticmethod
    def save_network_report(logs_list):
        return ReportingWriters.save_network_report(logs_list)

    @staticmethod
    def _generate_report(results, mode, is_simulation):
        standardized = ReportingProcessor.process_execution_results(results)
        summary = ReportingProcessor.summarize(standardized)
        summary["execution_mode"] = mode
        return ReportingWriters.write_all(standardized, summary, is_simulation=is_simulation)

    @staticmethod
    def save_simulation_report(results):
        return Reporting._generate_report(results, "Simulation", True)

    @staticmethod
    def save_execution_report(results):
        return Reporting._generate_report(results, "Execution", False)