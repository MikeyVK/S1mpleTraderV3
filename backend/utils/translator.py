# backend/utils/translator.py
"""
Handles loading and retrieving translated strings for the application.

@layer: Backend (Utility)
@dependencies: [backend.config.schemas.platform_schema]
@responsibilities:
    - Loads the appropriate language file based on the application configuration.
    - Provides a get method to retrieve translated strings using dot-notation keys.
    - Provides a get_param_name method for the special case of parameter display names.
"""

# Standard library
from pathlib import Path
from typing import Any, Dict

# Third-party
import yaml

# Project modules
from backend.config.schemas.platform_schema import PlatformConfig


class Translator:
    """Loads and manages internationalization (i18n) strings from YAML files.

    This class is instantiated once at startup. It loads the appropriate
    language file based on the application configuration and provides methods
    to retrieve translated strings using a dot-notation key.
    """

    def __init__(self, platform_config: PlatformConfig, project_root: Path):
        """Initializes the Translator by loading the appropriate language file.

        Args:
            platform_config: The application Pydantic config object.
            project_root: The absolute path to the project's root directory.
        """
        lang_path = project_root / "locales" / f"{platform_config.core.language}.yaml"
        self.strings: Dict[str, Any] = {}
        try:
            with open(lang_path, "r", encoding="utf-8") as f:
                self.strings = yaml.safe_load(f) or {}
        except FileNotFoundError:
            print(f"WARNING: Language file not found at {lang_path}")
        except yaml.YAMLError as e:
            print(f"ERROR: Failed to parse YAML file at {lang_path}: {e}")
        except OSError as e:
            print(f"ERROR: Failed to read language file at {lang_path}: {e}")

    def get(self, key: str, default: str | None = None) -> str:
        """Retrieves a nested translated string using dot-notation.

        If the key is not found, it returns the default value, or the key
        itself if no default is provided.

        Args:
            key: The dot-notation key (e.g., 'app.start').
            default: A fallback value to return if the key is not found. Defaults to None.

        Returns:
            The translated string (template).
        """
        try:
            value: Any = self.strings
            for part in key.split("."):
                value = value[part]

            # A valid translation must be a string. If we resolved a dict
            # (incomplete key), it's invalid.
            if not isinstance(value, str):
                return default or key

            return value
        except (KeyError, TypeError):
            return default or key

    def get_param_name(self, param_path: str, default: str | None = None) -> str:
        """Retrieves a display name for a full parameter path.

        This performs a direct lookup in the 'params_display_names' dictionary
        within the language file, which is a flat key-value map.

        Args:
            param_path: The full parameter path to look up.
            default: The value to return if the path is not found.
                    Defaults to the original param_path.

        Returns:
            The display name or a fallback value.
        """
        param_dict = self.strings.get("params_display_names", {})
        result = param_dict.get(param_path, default or param_path)
        # Ensure we always return a string
        return str(result) if result is not None else (default or param_path)
