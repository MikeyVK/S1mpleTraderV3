# mcp_server/presenters/text_presenter.py
# template=service version=5d5b489a created=2026-06-12T20:49Z updated=2026-06-12T21:00Z
"""Text presenter service.

@layer: Presenters
"""

import json
import string
from typing import Any

from pydantic import BaseModel

from mcp_server.config.schemas.presentation_config import (
    GlobalPresentationConfig,
    PresentationConfig,
    ToolPresentationConfig,
)
from mcp_server.core.exceptions import ConfigError
from mcp_server.core.interfaces.ipresenter import ITextPresenter
from mcp_server.core.operation_notes import NoteEntry
from mcp_server.schemas.cache_publication import CachePublication


class SafeNoneFormatter(string.Formatter):
    """Subclass of string.Formatter that formats None values without errors."""

    def __init__(self, none_value: str = "-") -> None:
        super().__init__()
        self.none_value = none_value

    def format_field(self, value: object, format_spec: str) -> str:
        if value is None:
            return self.none_value
        try:
            return str(super().format_field(value, format_spec))
        except (ValueError, TypeError):
            return str(value)


# Legacy note mapping removed


_DEFAULT_RUN_ID = "DEFAULT_RUN_ID_SENTINEL"


class TextPresenter(ITextPresenter):
    """Formats structured tool outputs into markdown text fallbacks using templates."""

    global_config: GlobalPresentationConfig
    tools_config: dict[str, ToolPresentationConfig]

    def __init__(
        self,
        config_data: dict[str, Any] | None = None,
        config: PresentationConfig | None = None,
    ) -> None:
        """Initialize presenter with config data or PresentationConfig object."""
        if config is not None:
            resolved = config
        elif config_data is not None:
            resolved = PresentationConfig.model_validate(config_data)
        else:
            resolved = PresentationConfig.model_validate({"global": {}, "tools": {}})

        self.global_config = resolved.global_settings
        self.tools_config = resolved.tools

    def get_next_instruction_texts(self) -> dict[str, str]:
        """Get the next instruction texts lookup dictionary."""
        return self.global_config.next_instruction_texts

    def _get_default_failure_template(self) -> str:
        """Get the default failure template."""
        return self.global_config.default_failure_template

    def _is_complex(self, val: object) -> bool:
        """Check if a value represents complex structured data."""
        if isinstance(val, (list, dict, set, tuple)):
            return len(val) > 0
        return (
            isinstance(val, str)
            and "\n" in val
            and (val.startswith("diff ") or "@@ " in val or "\n+" in val or "\n-" in val)
        )

    def get_none_value(self) -> str:
        """Get the placeholder string for None values."""
        return self.global_config.formatting.none_value

    def present_text(
        self,
        tool_name: str,
        data: BaseModel | dict[str, Any],
        notes: list[NoteEntry] | None = None,
        cache_pub: CachePublication | None = None,
        success: bool | None = None,
    ) -> str:
        """Present the DTO or dict as a formatted string."""

        # 1. Resolve success and presentation category
        resolved_success = success if success is not None else getattr(data, "success", True)

        # Resolve category internally based on tool config to decouple transport
        tool_cfg = self.tools_config.get(tool_name)
        resolved_cat = "query"
        if tool_cfg is not None:
            if isinstance(tool_cfg, ToolPresentationConfig):
                resolved_cat = tool_cfg.category or "query"
            else:
                resolved_cat = tool_cfg.get("category") or "query"
        # 2. Convert DTO/dict to a flat dictionary for formatting
        data_dict = data.model_dump() if isinstance(data, BaseModel) else dict(data)

        # 3. Resolve run_id for placeholders and fallback trigger
        if cache_pub is not None:
            placeholder_run_id = cache_pub.run_id
            should_trigger_fallback = not cache_pub.success
        else:
            placeholder_run_id = data_dict.get("run_id")
            should_trigger_fallback = False

        # 4. Bepaal template op basis van success
        template = None
        next_instructions = []

        if tool_cfg is not None:
            # Support both Pydantic model and raw dict for tool config
            if isinstance(tool_cfg, ToolPresentationConfig):
                template = (
                    tool_cfg.template_success if resolved_success else tool_cfg.template_failure
                )
                next_instructions = tool_cfg.next_instructions
            else:
                template = (
                    tool_cfg.get("template_success")
                    if resolved_success
                    else tool_cfg.get("template_failure")
                )
                next_instructions = tool_cfg.get("next_instructions") or []

        # Fallback for failure template
        if not resolved_success and not template:
            # Try to resolve template via error_code if present
            error_code = None
            if isinstance(data, BaseModel):
                error_code = getattr(data, "error_code", None)
                if not error_code and hasattr(data, "params") and isinstance(data.params, dict):
                    error_code = data.params.get("error_code")
            elif isinstance(data, dict):
                error_code = data.get("error_code")
                if not error_code and isinstance(data.get("params"), dict):
                    error_code = data.get("params", {}).get("error_code")

            failures: dict[str, str] = {}
            if isinstance(self.global_config, dict):
                failures = self.global_config.get("failures", {})
            else:
                failures = getattr(self.global_config, "failures", {})

            if error_code and error_code in failures:
                template = failures[error_code]
            else:
                template = self._get_default_failure_template()

        # Format template if we have one, otherwise dump/default representation
        if template:
            try:
                # Fill missing keys in data_dict with None to trigger SafeNoneFormatter
                # Parse all placeholders in the template
                placeholders = []
                none_val = self.get_none_value()
                formatter = SafeNoneFormatter(none_val)
                for _, field_name, _, _ in formatter.parse(template):
                    if field_name is not None:
                        placeholders.append(field_name.split(".")[0].split("[")[0])

                format_dict = {}
                params_dict = data_dict.get("params", {}) or {}
                for key in placeholders:
                    val = None
                    if key in data_dict:
                        val = data_dict[key]
                    elif isinstance(params_dict, dict) and key in params_dict:
                        val = params_dict[key]
                    elif key == "error_message" and "message" in data_dict:
                        val = data_dict["message"]
                    elif key == "message" and "error_message" in data_dict:
                        val = data_dict["error_message"]
                    format_dict[key] = val

                text = formatter.format(template, **format_dict)
            except Exception as exc:
                text = f"Format error: {exc}"
        else:
            # If no template is found, use a fallback text or DTO string
            text = data_dict.get("message") or data_dict.get("error_message") or str(data_dict)

        # 5. Prepend emoji prefix
        emojis = self.global_config.emojis
        if not resolved_success:
            emoji = emojis.get("failure", "❌")
        else:
            emoji = emojis.get(resolved_cat, emojis.get("success", "✅"))
        if emoji:
            text = f"{emoji} {text}"

        # 6. Resolve and append next instructions
        if resolved_success and next_instructions:
            instruction_texts = self.get_next_instruction_texts()
            for key in next_instructions:
                raw_text = instruction_texts.get(key, "")
                if raw_text:
                    # Parse placeholders in the next instruction template
                    try:
                        placeholders = []
                        none_val = self.get_none_value()
                        formatter = SafeNoneFormatter(none_val)
                        for _, field_name, _, _ in formatter.parse(raw_text):
                            if field_name is not None:
                                placeholders.append(field_name.split(".")[0].split("[")[0])

                        format_dict = {}
                        for k in placeholders:
                            if k == "run_id":
                                format_dict[k] = placeholder_run_id
                            else:
                                format_dict[k] = data_dict.get(k, None)

                        formatted_instruction = formatter.format(raw_text, **format_dict)
                        text = f"{text}\n\n{formatted_instruction}"
                    except Exception as exc:
                        text = f"{text}\n\nFormat error in instruction '{key}': {exc}"

        # 7. Append formatted notes if provided
        if notes:
            notes_text = self.present_notes(tool_name, notes)
            if notes_text:
                text = f"{text}\n\n{notes_text}"

        # Check if cache URI needs to be appended (moved from server.py)
        if placeholder_run_id and "pgmcp://cache/runs/" not in text:
            uri_ref_tmpl = self.get_next_instruction_texts().get("uri_reference")
            if uri_ref_tmpl:
                try:
                    none_val = self.get_none_value()
                    formatter = SafeNoneFormatter(none_val)
                    uri_text = formatter.format(uri_ref_tmpl, run_id=placeholder_run_id)
                except Exception:
                    uri_text = uri_ref_tmpl.format(run_id=placeholder_run_id)
            else:
                uri_text = (
                    "*(Full details available in the structured JSON payload. "
                    f"View resource: pgmcp://cache/runs/{placeholder_run_id})*"
                )
            text = f"{text}\n\n{uri_text}"

        # 8. Fallback when cache publication failed
        if should_trigger_fallback:
            warning_note = self.get_next_instruction_texts().get(
                "cache_publication_failed",
                "*(Cache publication failed. Full details dumped inline)*",
            )
            # Strip traceback from ExecutionErrorOutput DTO to avoid leaking secrets
            json_dict = dict(data_dict)
            if "traceback" in json_dict:
                json_dict.pop("traceback", None)
            json_str = json.dumps(json_dict, indent=2)
            text = f"{text}\n\n{warning_note}\n```json\n{json_str}\n```"

        return text

    present = present_text

    def present_notes(self, tool_name: str, notes: list[NoteEntry]) -> str | None:
        """Format notes into markdown text blocks using templates."""
        group_names = ["exclusions", "suggestions", "recoveries", "info"]
        grouped_texts: dict[str, list[str]] = {g: [] for g in group_names}

        none_val = self.get_none_value()
        formatter = SafeNoneFormatter(none_val)

        # Retrieve group configuration
        # global.notes.groups
        global_notes = self.global_config.notes
        group_configs = global_notes.groups

        for note in notes:
            key = note.key
            params = note.params

            # Search for template and group
            found_template = None
            found_group = None

            for group in group_names:
                # 1. Local tool config lookup
                tool_cfg = self.tools_config.get(tool_name)
                local_tmpl = None
                if tool_cfg is not None:
                    group_dict = getattr(tool_cfg, group, {})
                    if isinstance(group_dict, dict):
                        local_tmpl = group_dict.get(key)

                if isinstance(local_tmpl, str):
                    found_template = local_tmpl
                    found_group = group
                    break

                # 2. Global notes config fallback lookup
                global_tmpl = None
                group_templates = global_notes.templates.get(group)
                if group_templates is not None:
                    global_tmpl = group_templates.get(key)

                if isinstance(global_tmpl, str):
                    found_template = global_tmpl
                    found_group = group
                    break

            if found_template is not None and found_group is not None:
                # Fill missing keys in params with None to trigger SafeNoneFormatter
                placeholders = []
                try:
                    for _, field_name, _, _ in formatter.parse(found_template):
                        if field_name is not None:
                            placeholders.append(field_name.split(".")[0].split("[")[0])
                except Exception:
                    pass

                format_dict = {}
                for p_key in placeholders:
                    format_dict[p_key] = params.get(p_key, None)

                try:
                    formatted_text = formatter.format(found_template, **format_dict)
                    grouped_texts[found_group].append(formatted_text)
                except Exception as exc:
                    grouped_texts[found_group].append(f"Format error: {exc}")
        lines = []
        for group in group_names:
            items = grouped_texts[group]
            if not items:
                continue

            # Get emoji and header
            cfg = group_configs.get(group)
            if cfg is None:
                raise ConfigError(
                    f"Note group config for '{group}' is missing in presentation.yaml"
                )
            emoji = cfg.emoji
            header = cfg.header

            group_header = f"{emoji} {header}".strip()
            lines.append(group_header)
            for item in items:
                lines.append(f"  - {item}")
            lines.append("")

        if not lines:
            return None
        return "\n".join(lines).strip()


def validate_presentation_alignment(presenter: TextPresenter, tools: list[Any]) -> None:
    """Verifies that templates align with DTO models, note classes, and errors to prevent drift."""
    import string  # noqa: PLC0415

    # ConfigError imported on module level
    pass
    blacklist = {"message", "msg", "text", "txt", "error_message", "error", "err"}
    blacklist = {"message", "msg", "text", "txt", "error_message", "error", "err"}

    # Mapping for system-level errors
    error_class_fields = {
        "ERR_CONFIG": {"message", "file_path", "code"},
        "config": {"message", "file_path", "code"},
        "ERR_VALIDATION": {
            "message",
            "validation_errors",
            "input_schema",
            "params",
            "success",
            "error_type",
            "traceback",
        },
        "validation": {
            "message",
            "validation_errors",
            "input_schema",
            "params",
            "success",
            "error_type",
            "traceback",
        },
        "ERR_EXECUTION": {"message", "params", "success", "error_type", "traceback"},
        "execution": {"message", "params", "success", "error_type", "traceback"},
        "ERR_SYSTEM": {"message", "fallback", "code"},
        "system": {"message", "fallback", "code"},
        "ERR_CACHE": {"message", "params", "success", "error_type", "traceback"},
        "cache": {"message", "params", "success", "error_type", "traceback"},
    }

    # Mapping for generic notes keys to their allowed parameters
    generic_note_fields = {
        "allowed_bases_suggestion": {"bases"},
        "initialize_project_suggestion": {"issue_number"},
        "close_open_pr_suggestion": set(),
        "transition_phase_suggestion": {"required_phase"},
        "load_context_suggestion": set(),
        "allowed_branch_types": {"types"},
        "branch_name_pattern_mismatch": {"pattern"},
        "commit_empty_files_suggestion": set(),
        "restore_empty_files_suggestion": set(),
        "delete_protected_branch_suggestion": {"protected_branches"},
        "pytest_no_tests_collected_suggestion": set(),
        "scaffold_missing_fields_suggestion": {"missing_fields", "artifact_type"},
        "submit_pr_commit_failed_recovery": {"error_details"},
        "submit_pr_push_failed_with_rollback_recovery": {"error_details"},
        "submit_pr_push_failed_no_rollback_recovery": {"error_details"},
        "rollback_local_reset_failed_recovery": {"error_details"},
        "rollback_remote_push_failed_recovery": {"error_details"},
        "submit_pr_api_failed_with_rollback_recovery": {"error_details"},
        "scaffold_fields_recovery": {"artifact_type"},
        "pytest_interrupted_recovery": set(),
        "pytest_internal_error_recovery": set(),
        "pytest_usage_error_recovery": set(),
        "pytest_unexpected_code_recovery": {"exit_code"},
        "transition_conflict_recovery": {"recovery_steps"},
        "docs_dir_not_found_expected": {"expected_dir"},
        "docs_dir_not_found_create": set(),
        "docs_dir_not_found_add_files": set(),
        "dirty_workspace_branch_blocker": set(),
        "pull_dirty_workspace_blocker": set(),
        "pull_detached_head_blocker": set(),
        "pull_no_upstream_blocker": set(),
        "pull_refspec_not_supported_blocker": set(),
        "merge_dirty_workspace_blocker": set(),
        "submit_pr_dirty_workspace_blocker": set(),
        "submit_pr_no_upstream_blocker": set(),
        "scaffold_validation_failed": {"error_details"},
    }

    def get_placeholders(tmpl: str) -> list[str]:
        p_list = []
        try:
            for _, field_name, _, _ in string.Formatter().parse(tmpl):
                if field_name is not None:
                    base_field = field_name.split(".")[0].split("[")[0]
                    p_list.append(base_field)
        except Exception as exc:
            raise ConfigError(f"Invalid template format: {exc}") from exc
        return p_list

    def check_blacklist(tmpl: str, template_key: str, is_default_fail: bool = False) -> None:
        placeholders = get_placeholders(tmpl)
        for p in placeholders:
            if p in blacklist:
                # Exceptions
                if is_default_fail and p == "error_message":
                    continue
                if template_key == "template_failure" and p == "error_message":
                    continue
                if template_key in generic_note_fields and p == "message":
                    continue
                raise ConfigError(
                    f"Template for '{template_key}' uses blacklisted generic parameter '{p}'"
                )

    # 1. Global settings validation
    global_cfg = presenter.global_config
    default_fail = global_cfg.default_failure_template
    failures = global_cfg.failures
    global_note_templates = global_cfg.notes.templates
    # Validate default failure template
    if default_fail:
        check_blacklist(default_fail, "default_failure_template", is_default_fail=True)

    # Validate global failures
    for err_code, template in failures.items():
        check_blacklist(template, err_code)
        placeholders = get_placeholders(template)
        # Verify placeholders against system error fields if it is a known code
        if err_code in error_class_fields:
            allowed = error_class_fields[err_code]
            for p in placeholders:
                if p not in allowed:
                    raise ConfigError(
                        f"Failure placeholder '{p}' not found in DTO fields for '{err_code}'"
                    )

    # Validate global note templates
    for _, group_templates in global_note_templates.items():
        if not isinstance(group_templates, dict):
            continue
        for key, template in group_templates.items():
            check_blacklist(template, key)
            placeholders = get_placeholders(template)
            if key in generic_note_fields:
                allowed = generic_note_fields[key]
                for p in placeholders:
                    if p not in allowed:
                        raise ConfigError(
                            f"Note template placeholder '{p}' not found in fields for note '{key}'"
                        )

    # 2. Tool-specific validation
    for tool in tools:
        tool_name = getattr(tool, "name", None)
        if not tool_name:
            continue

        output_model = getattr(tool, "output_model", None)
        tool_cfg = presenter.tools_config.get(tool_name)
        if not tool_cfg:
            continue

        # Get templates for this tool
        templates_to_check = []
        next_inst_keys = []

        if tool_cfg.template_success is not None:
            templates_to_check.append(("template_success", tool_cfg.template_success))
        if tool_cfg.template_failure is not None:
            templates_to_check.append(("template_failure", tool_cfg.template_failure))
        next_inst_keys = tool_cfg.next_instructions

        # Local notes
        local_notes = {
            "exclusions": tool_cfg.exclusions,
            "suggestions": tool_cfg.suggestions,
            "recoveries": tool_cfg.recoveries,
            "info": tool_cfg.info,
        }
        instruction_texts = presenter.get_next_instruction_texts()
        for key in next_inst_keys:
            raw_text = instruction_texts.get(key)
            if isinstance(raw_text, str):
                templates_to_check.append((f"instruction_{key}", raw_text))

        # Check local notes
        for _, notes_dict in local_notes.items():
            if not isinstance(notes_dict, dict):
                continue
            for key, template in notes_dict.items():
                check_blacklist(template, key)
                placeholders = get_placeholders(template)
                if key in generic_note_fields:
                    allowed = generic_note_fields[key]
                    for p in placeholders:
                        if p not in allowed:
                            raise ConfigError(
                                f"Note placeholder '{p}' not found in fields for '{key}'"
                            )

        # Skip output model validation if model is not defined (or None during migration)
        if (
            output_model is None
            or not isinstance(output_model, type)
            or not issubclass(output_model, BaseModel)
        ):
            continue

        allowed_fields = set(output_model.model_fields.keys())
        allowed_fields.update({"success", "error_message", "post_tool_instruction"})

        for key, template in templates_to_check:
            check_blacklist(template, key)
            placeholders = get_placeholders(template)
            for base_field in placeholders:
                if base_field.startswith("emoji_"):
                    continue
                if base_field not in allowed_fields:
                    raise ConfigError(
                        f"Template placeholder '{base_field}' not found in DTO "
                        f"'{output_model.__name__}' for tool '{tool_name}'"
                    )
