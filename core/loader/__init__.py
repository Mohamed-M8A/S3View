import os
from .engine import LoaderEngine
from core.paths import Paths

class PluginLoader:
    def __init__(self):
        self.root_directory = Paths.get_root_path()
        self.plugins_directory = os.path.join(self.root_directory, "plugins")

    def discover_plugins(self, force_refresh: bool = False):
        return LoaderEngine.discover(self.plugins_directory, force_refresh=force_refresh)

    def get_plugin_by_action(self, action_name: str):
        plugins, _ = self.discover_plugins()
        return plugins.get(action_name)

    def get_color_by_action(self, action_name: str) -> str:
        plugin = self.get_plugin_by_action(action_name)
        return plugin.syntax_color if plugin else "#cccccc"

    def get_plugin_and_flags_by_keyword(self, raw_keyword: str):
        plugins, keywords_mapping = self.discover_plugins()
        action_name = keywords_mapping.get(raw_keyword)
        if action_name:
            plugin = plugins[action_name]
            trigger_config = plugin.get_trigger_configuration(raw_keyword)
            return {
                "plugin": plugin,
                "flags": trigger_config.get("behavior_flags", {}),
                "parser_method": plugin.get_parser_method_name(),
                "requires_src": plugin.requires_src,
                "requires_dst": plugin.requires_dst
            }
        return None

    def get_all_keywords(self) -> list:
        _, keywords_mapping = self.discover_plugins()
        return list(keywords_mapping.keys())