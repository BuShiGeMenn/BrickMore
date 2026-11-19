import os
import yaml


class GlobalConfig:
    _instance = None
    _config_data = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GlobalConfig, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """
        Reads global_config.yaml from the same directory as this file
        and stores it in a dictionary format.
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, 'global_config.yaml')

        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                # Load yaml content as a dictionary
                self._config_data = yaml.safe_load(f) or {}
        else:
            # Initialize with an empty dict if file doesn't exist
            self._config_data = {}

    def get(self, key_path, default=None):
        """
        Retrieves a value using 'A.B' notation.
        Returns default if the key does not exist.
        """
        keys = key_path.split('.')
        value = self._config_data

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            # Return default if key path is invalid or interrupted
            return default

    def set(self, key_path, value):
        """
        Sets a value using 'A.B' notation.
        Creates intermediate dictionaries if they do not exist.
        """
        keys = key_path.split('.')
        target = self._config_data

        for k in keys[:-1]:
            # Ensure the path exists by creating nested dictionaries
            target = target.setdefault(k, {})

        target[keys[-1]] = value


def get_config():
    """
    Utility function to access the GlobalConfig singleton instance.
    """
    return GlobalConfig()
