# model_finder/settings_model.py
import os
import json
import traceback
import logging # Import logging

logger = logging.getLogger(__name__) # Get logger for this module

class SettingsModel:
    """Handles loading and saving application settings from/to a JSON file."""

    SETTINGS_FILENAME = "settings.json"
    DEFAULT_SETTINGS = {
        'auto_open_html': True,
        'chrome_path': '',
        'random_theme': True,
        'theme': 'cosmo', # Default theme
        'retention_days': 30
    }

    def __init__(self):
        self._settings_path = self._get_settings_path()
        logger.info(f"Settings file path determined: {self._settings_path}")

    def _get_settings_path(self):
        """Determines the absolute path to the settings file."""
        return os.path.join(os.path.dirname(__file__), self.SETTINGS_FILENAME)

    def load(self):
        """
        Loads settings from the JSON file.
        Returns the loaded settings dictionary or defaults if file not found/invalid.
        """
        if not os.path.exists(self._settings_path):
            logger.warning(f"Settings file not found at {self._settings_path}. Returning default settings.")
            return self.DEFAULT_SETTINGS.copy()

        try:
            with open(self._settings_path, 'r', encoding='utf-8') as f:
                loaded_settings = json.load(f)
                settings = self.DEFAULT_SETTINGS.copy()
                settings.update(loaded_settings)
                logger.info("Settings loaded successfully.")
                return settings
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from {self._settings_path}. Returning default settings.", exc_info=True)
            return self.DEFAULT_SETTINGS.copy()
        except Exception as e:
            logger.error(f"Error reading settings file {self._settings_path}. Returning default settings.", exc_info=True)
            return self.DEFAULT_SETTINGS.copy()

    def save(self, settings_data):
        """
        Saves the provided settings dictionary to the JSON file.
        Returns True on success, False on failure.
        :param settings_data: Dictionary containing settings to save.
        """
        logger.debug(f"Attempting to save settings: {settings_data}") # Log data being saved
        try:
            with open(self._settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Settings saved successfully to {self._settings_path}")
            return True
        except Exception as e:
            logger.error(f"Error writing settings file {self._settings_path}", exc_info=True)
            return False