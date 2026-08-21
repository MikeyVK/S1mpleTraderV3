# mcp_server/presenters/text_presenter.py
# template=service version=5d5b489a created=2026-06-12T20:49Z updated=2026-06-12T21:00Z
"""Text presenter service.

@layer: Presenters
"""

from __future__ import annotations

import json
import string
from collections.abc import Sequence
from enum import Enum
from typing import TYPE_CHECKING, Any, TypeGuard, get_origin

from pydantic import BaseModel

from mcp_server.config.schemas.presentation_config import (
    CollectionPresentationConfig,
    EnumCasePresentationConfig,
    GlobalPresentationConfig,
    PresentationConfig,
    ToolPresentationConfig,
)
from mcp_server.core.exceptions import ConfigError
from mcp_server.core.interfaces.ipresenter import ITextPresenter
from mcp_server.core.operation_notes import NoteEntry
from mcp_server.presenters.collection_text_renderer import (
    CollectionTextRenderer,
    classify_sequence_annotation,
)
from mcp_server.presenters.collection_text_renderer import (
    SafeNoneFormatter as SequenceSafeNoneFormatter,
)
from mcp_server.presenters.text_budget_limiter import TextBudgetLimiter
from mcp_server.schemas.cache_publication import CachePublication

if TYPE_CHECKING:
    from mcp_server.bootstrap import SupportedToolContract


class SafeNoneFormatter(SequenceSafeNoneFormatter):
    """Compatibility name for the shared generic value formatter."""


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
        collection_renderer: CollectionTextRenderer | None = None,
        budget_limiter: TextBudgetLimiter | None = None,
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
        self._collection_renderer = collection_renderer or CollectionTextRenderer(
            self.global_config.formatting
        )
        self._budget_limiter = budget_limiter or TextBudgetLimiter(
            max_text_response_bytes=self.global_config.max_text_response_bytes,
            formatting=self.global_config.formatting,
        )

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

    def _format_data_template(
        self,
        template: str,
        data: dict[str, Any],
        *,
        max_items: int | None,
        run_id: str | None = None,
    ) -> str:
        formatter = SafeNoneFormatter(
            self.get_none_value(),
            formatting=self.global_config.formatting,
            max_items=max_items,
        )
        placeholders = [
            field_name.split(".")[0].split("[")[0]
            for _, field_name, _, _ in formatter.parse(template)
            if field_name is not None
        ]
        params = data.get("params", {}) or {}
        values: dict[str, object] = {}
        for placeholder in placeholders:
            if placeholder == "run_id" and run_id is not None:
                values[placeholder] = run_id
            elif placeholder in data:
                values[placeholder] = data[placeholder]
            elif isinstance(params, dict) and placeholder in params:
                values[placeholder] = params[placeholder]
            elif placeholder == "error_message" and "message" in data:
                values[placeholder] = data["message"]
            elif placeholder == "message" and "error_message" in data:
                values[placeholder] = data["error_message"]
            else:
                values[placeholder] = None
        return formatter.format(template, **values)

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
                formatter = SafeNoneFormatter(
                    none_val,
                    formatting=self.global_config.formatting,
                    max_items=tool_cfg.max_items if tool_cfg else None,
                )
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

        if tool_cfg is not None:
            for enum_case in tool_cfg.enum_cases:
                raw_value = data_dict.get(enum_case.field)
                serialized_value = (
                    str(raw_value.value) if isinstance(raw_value, Enum) else str(raw_value)
                )
                enum_template = enum_case.cases.get(serialized_value)
                if enum_template is not None:
                    enum_text = self._format_data_template(
                        enum_template,
                        data_dict,
                        max_items=tool_cfg.max_items,
                    )
                    text = f"{text}\n\n{enum_text}"

            collections = tool_cfg.collections
            if not resolved_success:
                collections = tuple(
                    declaration for declaration in collections if declaration.field in data_dict
                )
            if collections:
                if tool_cfg.max_items is None:
                    raise ConfigError("Configured collections require max_items")
                collection_text = self._collection_renderer.render(
                    data_dict,
                    collections,
                    tool_cfg.max_items,
                )
                if collection_text:
                    text = f"{text}\n\n{collection_text}"

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
                        formatter = SafeNoneFormatter(
                            none_val,
                            formatting=self.global_config.formatting,
                            max_items=tool_cfg.max_items if tool_cfg else None,
                        )
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

        # 8. Fallback when cache publication failed
        if should_trigger_fallback:
            warning_note = self.get_next_instruction_texts().get(
                "cache_publication_failed",
                "*(Cache publication failed. Full details dumped inline)*",
            )
            json_dict = dict(data_dict)
            json_dict.pop("traceback", None)
            json_str = json.dumps(json_dict, indent=2)
            text = f"{text}\n\n{warning_note}\n```json\n{json_str}\n```"

        cache_reference = None
        if placeholder_run_id:
            uri_template = self.get_next_instruction_texts().get("uri_reference")
            if uri_template:
                cache_reference = self._format_data_template(
                    uri_template,
                    data_dict,
                    max_items=tool_cfg.max_items if tool_cfg else None,
                    run_id=placeholder_run_id,
                )
            else:
                cache_reference = (
                    "*(Full details available in the structured JSON payload. "
                    f"View resource: pgmcp://cache/runs/{placeholder_run_id})*"
                )
            if cache_reference not in text:
                text = f"{text}\n\n{cache_reference}"

        return self._budget_limiter.limit(text, cache_reference)

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


def validate_presentation_alignment(
    presenter: TextPresenter,
    contracts: Sequence[SupportedToolContract],
) -> None:
    """Fail fast when presentation policy and the supported tool catalog drift."""
    blacklist = {"message", "msg", "text", "txt", "error_message", "error", "err"}

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

    def get_placeholders(template: str) -> list[str]:
        try:
            return [
                field_name.split(".")[0].split("[")[0]
                for _, field_name, _, _ in string.Formatter().parse(template)
                if field_name is not None
            ]
        except ValueError as exc:
            raise ConfigError(f"Invalid template format: {exc}") from exc

    def check_blacklist(
        template: str,
        template_key: str,
        *,
        is_default_fail: bool = False,
    ) -> None:
        for placeholder in get_placeholders(template):
            if placeholder not in blacklist:
                continue
            if is_default_fail and placeholder == "error_message":
                continue
            if template_key == "template_failure" and placeholder == "error_message":
                continue
            if template_key in generic_note_fields and placeholder == "message":
                continue
            raise ConfigError(
                f"Template for '{template_key}' uses blacklisted generic parameter '{placeholder}'"
            )

    def is_model_type(
        annotation: object,
    ) -> TypeGuard[type[BaseModel]]:
        return isinstance(annotation, type) and issubclass(annotation, BaseModel)

    def is_scalar_type(annotation: object) -> bool:
        if not isinstance(annotation, type):
            return False
        return annotation in {str, int, float, bool} or issubclass(annotation, Enum)

    def get_sequence_item(annotation: object, path: str) -> object:
        return classify_sequence_annotation(annotation, path=path).item_type

    def template_uses_sequence(
        template: str,
        *,
        template_key: str,
        model: type[BaseModel],
        tool_name: str,
    ) -> bool:
        check_blacklist(template, template_key)
        uses_sequence = False
        allowed_fields = set(model.model_fields)
        allowed_fields.update({"success", "error_message", "post_tool_instruction"})

        for placeholder in get_placeholders(template):
            if placeholder.startswith("emoji_"):
                continue
            if placeholder not in allowed_fields:
                raise ConfigError(
                    f"Template placeholder '{placeholder}' not found in DTO "
                    f"'{model.__name__}' for tool '{tool_name}'"
                )
            model_field = model.model_fields.get(placeholder)
            if model_field is None:
                continue

            annotation = model_field.annotation
            origin = get_origin(annotation)
            if origin in {list, tuple}:
                item_type = get_sequence_item(
                    annotation,
                    f"{tool_name}.{placeholder}",
                )
                if not is_scalar_type(item_type):
                    raise ConfigError(
                        f"Template '{template_key}' for tool '{tool_name}' "
                        "cannot inline model-valued or nested sequence "
                        f"field '{placeholder}'"
                    )
                uses_sequence = True
            elif is_model_type(annotation) or origin in {dict, set}:
                raise ConfigError(
                    f"Template '{template_key}' for tool '{tool_name}' "
                    f"cannot inline structured field '{placeholder}'"
                )
        return uses_sequence

    def validate_collection(
        declaration: CollectionPresentationConfig,
        *,
        model: type[BaseModel],
        path: str,
    ) -> bool:
        if "." in declaration.field:
            raise ConfigError(
                f"Collection field '{path}.{declaration.field}' must be a direct field"
            )
        model_field = model.model_fields.get(declaration.field)
        if model_field is None:
            raise ConfigError(
                f"Collection field '{path}.{declaration.field}' is not present "
                f"on DTO '{model.__name__}'"
            )
        if declaration.heading and get_placeholders(declaration.heading):
            raise ConfigError(
                f"Collection heading for '{path}.{declaration.field}' must be literal Markdown"
            )

        item_type = get_sequence_item(
            model_field.annotation,
            f"{path}.{declaration.field}",
        )
        placeholders = get_placeholders(declaration.item_template)

        if is_scalar_type(item_type):
            if set(placeholders) - {"item"}:
                raise ConfigError(
                    f"Scalar collection '{path}.{declaration.field}' item_template "
                    "may reference only 'item'"
                )
            if declaration.children:
                raise ConfigError(
                    f"Scalar collection '{path}.{declaration.field}' cannot "
                    "declare child collections"
                )
            return True

        if not is_model_type(item_type):
            raise ConfigError(f"Collection '{path}.{declaration.field}' has unsupported item type")

        item_model = item_type
        for placeholder in placeholders:
            item_field = item_model.model_fields.get(placeholder)
            if item_field is None:
                raise ConfigError(
                    f"Collection item placeholder '{placeholder}' is not present "
                    f"on DTO '{item_model.__name__}' at "
                    f"'{path}.{declaration.field}'"
                )
            annotation = item_field.annotation
            origin = get_origin(annotation)
            if origin in {list, tuple}:
                nested_item = get_sequence_item(
                    annotation,
                    f"{path}.{declaration.field}.{placeholder}",
                )
                if not is_scalar_type(nested_item):
                    raise ConfigError(
                        f"Collection item template at '{path}.{declaration.field}' "
                        f"cannot inline nested model sequence '{placeholder}'"
                    )
            elif is_model_type(annotation) or origin in {dict, set}:
                raise ConfigError(
                    f"Collection item template at '{path}.{declaration.field}' "
                    f"cannot inline structured field '{placeholder}'"
                )

        for child in declaration.children:
            validate_collection(
                child,
                model=item_model,
                path=f"{path}.{declaration.field}",
            )
        return True

    def validate_enum_case(
        declaration: EnumCasePresentationConfig,
        *,
        model: type[BaseModel],
        tool_name: str,
    ) -> bool:
        if "." in declaration.field:
            raise ConfigError(
                f"Enum-case field '{tool_name}.{declaration.field}' must be a direct field"
            )
        model_field = model.model_fields.get(declaration.field)
        if model_field is None:
            raise ConfigError(
                f"Enum-case field '{declaration.field}' is not present "
                f"on DTO '{model.__name__}' for tool '{tool_name}'"
            )
        enum_type = model_field.annotation
        if not (isinstance(enum_type, type) and issubclass(enum_type, Enum)):
            raise ConfigError(
                f"Enum-case field '{tool_name}.{declaration.field}' must be enum-valued"
            )
        allowed_values = {str(member.value) for member in enum_type}
        invalid_values = set(declaration.cases) - allowed_values
        if invalid_values:
            values = ", ".join(sorted(invalid_values))
            raise ConfigError(
                f"Enum-case field '{tool_name}.{declaration.field}' "
                f"contains invalid case value(s): {values}"
            )

        uses_sequence = False
        for case_value, template in declaration.cases.items():
            uses_sequence = (
                template_uses_sequence(
                    template,
                    template_key=f"enum_case_{declaration.field}_{case_value}",
                    model=model,
                    tool_name=tool_name,
                )
                or uses_sequence
            )
        return uses_sequence

    global_cfg = presenter.global_config
    default_fail = global_cfg.default_failure_template
    if default_fail:
        check_blacklist(
            default_fail,
            "default_failure_template",
            is_default_fail=True,
        )

    for error_code, template in global_cfg.failures.items():
        check_blacklist(template, error_code)
        allowed = error_class_fields.get(error_code)
        if allowed is None:
            continue
        for placeholder in get_placeholders(template):
            if placeholder not in allowed:
                raise ConfigError(
                    f"Failure placeholder '{placeholder}' not found in DTO "
                    f"fields for '{error_code}'"
                )

    for group_templates in global_cfg.notes.templates.values():
        for key, template in group_templates.items():
            check_blacklist(template, key)
            allowed = generic_note_fields.get(key)
            if allowed is None:
                continue
            for placeholder in get_placeholders(template):
                if placeholder not in allowed:
                    raise ConfigError(
                        f"Note template placeholder '{placeholder}' not found "
                        f"in fields for note '{key}'"
                    )

    contract_names = [contract.name for contract in contracts]
    if len(contract_names) != len(set(contract_names)):
        raise ConfigError("Duplicate supported tool identity in runtime catalog")

    configured_names = set(presenter.tools_config)
    supported_names = set(contract_names)
    missing = supported_names - configured_names
    unknown = configured_names - supported_names
    if missing or unknown:
        details = []
        if missing:
            details.append(f"missing: {', '.join(sorted(missing))}")
        if unknown:
            details.append(f"unknown: {', '.join(sorted(unknown))}")
        raise ConfigError(
            "presentation.yaml must exactly match the supported tool catalog ("
            + "; ".join(details)
            + ")"
        )

    instruction_texts = presenter.get_next_instruction_texts()
    for contract in contracts:
        tool_name = contract.name
        output_model = contract.output_model
        if not (isinstance(output_model, type) and issubclass(output_model, BaseModel)):
            raise ConfigError(f"Supported tool '{tool_name}' has no concrete Pydantic output model")

        tool_cfg = presenter.tools_config[tool_name]
        uses_bounded_sequence = bool(tool_cfg.collections)

        templates_to_check: list[tuple[str, str]] = []
        if tool_cfg.template_success is not None:
            templates_to_check.append(("template_success", tool_cfg.template_success))
        if tool_cfg.template_failure is not None:
            templates_to_check.append(("template_failure", tool_cfg.template_failure))
        for key in tool_cfg.next_instructions:
            raw_text = instruction_texts.get(key)
            if raw_text is not None:
                templates_to_check.append((f"instruction_{key}", raw_text))

        local_notes = (
            tool_cfg.exclusions,
            tool_cfg.suggestions,
            tool_cfg.recoveries,
            tool_cfg.info,
        )
        for notes_dict in local_notes:
            for key, template in notes_dict.items():
                check_blacklist(template, key)
                allowed = generic_note_fields.get(key)
                if allowed is None:
                    continue
                for placeholder in get_placeholders(template):
                    if placeholder not in allowed:
                        raise ConfigError(
                            f"Note placeholder '{placeholder}' not found in fields for '{key}'"
                        )

        for key, template in templates_to_check:
            uses_bounded_sequence = (
                template_uses_sequence(
                    template,
                    template_key=key,
                    model=output_model,
                    tool_name=tool_name,
                )
                or uses_bounded_sequence
            )

        for collection in tool_cfg.collections:
            uses_bounded_sequence = (
                validate_collection(
                    collection,
                    model=output_model,
                    path=tool_name,
                )
                or uses_bounded_sequence
            )

        for enum_case in tool_cfg.enum_cases:
            uses_bounded_sequence = (
                validate_enum_case(
                    enum_case,
                    model=output_model,
                    tool_name=tool_name,
                )
                or uses_bounded_sequence
            )

        if uses_bounded_sequence and tool_cfg.max_items is None:
            raise ConfigError(f"Tool '{tool_name}' uses bounded sequences but has no max_items")
        if not uses_bounded_sequence and tool_cfg.max_items is not None:
            raise ConfigError(f"Tool '{tool_name}' defines orphaned max_items configuration")
