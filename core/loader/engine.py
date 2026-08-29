import os
import logging
from typing import Dict, Tuple
from .entity import PluginEntity

logger = logging.getLogger(__name__)


class LoaderEngine:
    _PLUGINS_CACHE: Dict[str, PluginEntity] = {}
    _KEYWORDS_CACHE: Dict[str, str] = {}
    _IS_DISCOVERED: bool = False

    @classmethod
    def discover(cls, plugins_directory: str, force_refresh: bool = False) -> Tuple[Dict[str, PluginEntity], Dict[str, str]]:
        if cls._IS_DISCOVERED and not force_refresh:
            return cls._PLUGINS_CACHE, cls._KEYWORDS_CACHE

        discovered_plugins = {}
        keywords_mapping = {}

        if not os.path.exists(plugins_directory):
            logger.warning(f"Plugins directory '{plugins_directory}' does not exist.")
            return {}, {}

        for item_name in os.listdir(plugins_directory):
            full_path = os.path.join(plugins_directory, item_name)
            manifest_path = os.path.join(full_path, "manifest.json")

            if os.path.isdir(full_path) and os.path.exists(manifest_path):
                try:
                    plugin_object = PluginEntity(full_path)
                    if plugin_object.action_name != "unknown":
                        discovered_plugins[plugin_object.action_name] = plugin_object
                        for keyword in plugin_object.all_keywords:
                            keywords_mapping[keyword] = plugin_object.action_name
                except Exception as e:
                    logger.error(f"Failed to initialize plugin at {full_path}: {e}")
                    continue

        cls._PLUGINS_CACHE = discovered_plugins
        cls._KEYWORDS_CACHE = keywords_mapping
        cls._IS_DISCOVERED = True

        return cls._PLUGINS_CACHE, cls._KEYWORDS_CACHE

    @classmethod
    def clear_cache(cls):
        cls._PLUGINS_CACHE.clear()
        cls._KEYWORDS_CACHE.clear()
        cls._IS_DISCOVERED = False