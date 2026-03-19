"""Tests for the stop hook that enforces canonical handover blocks."""

import json
from pathlib import Path
from types import ModuleType

import copilot_orchestration.hooks.stop_handover_guard as _stop_guard_module


def _load_stop_handover_guard_module() -> ModuleType:
    return _stop_guard_module


def _event_for(transcript_path: str, *, stop_hook_active: bool = False) -> dict[str, object]:
    return {
        "cwd": "d:/dev/SimpleTraderV3",
        "transcript_path": transcript_path,
        "stop_hook_active": stop_hook_active,
    }


def _assistant_record(content: str) -> str:
    return json.dumps({"role": "assistant", "content": content})


class TestStopHandoverGuard:
    """Stop hook validation for final copy-paste handover prompts."""

    def test_imp_valid_handover_allows_stop(self, tmp_path: Path) -> None:
        module = _load_stop_handover_guard_module()
        transcript = tmp_path / "imp_valid.jsonl"
        transcript.write_text(
            "\n".join(
                [
                    _assistant_record(
                        "### Copy-Paste Prompt For QA Chat\n"
                        "```text\n"
                        "@qa Review the latest implementation work on this branch.\n"
                        "Use qa_agent.md as the project-specific QA guide.\n\n"
                        "Review target:\n- Branch: feature/test\n\n"
                        "Implementation claim under review:\n- Parser fix complete.\n\n"
                        "Proof provided by implementation:\n- Tests run: pytest\n\n"
                        "QA focus:\n- Verify the proof.\n"
                        "```"
                    ),
                ]
            ),
            encoding="utf-8",
        )

        result = module.evaluate_stop_hook(_event_for(str(transcript)), "imp")

        assert result == {}

    def test_imp_missing_handover_blocks_stop_with_specific_retry_instruction(
        self,
        tmp_path: Path,
    ) -> None:
        module = _load_stop_handover_guard_module()
        transcript = tmp_path / "imp_invalid.jsonl"
        transcript.write_text(
            _assistant_record("Implementation completed and tests passed."),
            encoding="utf-8",
        )

        result = module.evaluate_stop_hook(_event_for(str(transcript)), "imp")

        reason = result["hookSpecificOutput"]["reason"]
        assert result["hookSpecificOutput"]["decision"] == "block"
        assert "### Copy-Paste Prompt For QA Chat" in reason
        assert "@qa Review the latest implementation work on this branch." in reason

    def test_qa_valid_handover_allows_stop(self, tmp_path: Path) -> None:
        module = _load_stop_handover_guard_module()
        transcript = tmp_path / "qa_valid.jsonl"
        transcript.write_text(
            "\n".join(
                [
                    _assistant_record(
                        "### Copy-Paste Prompt For Implementation Chat\n"
                        "```text\n"
                        "@imp Address the latest QA findings on this branch.\n"
                        "Use imp_agent.md as the project-specific implementation guide.\n\n"
                        "Task:\n- Fix the latest QA findings.\n\n"
                        "Files likely in scope:\n"
                        "1. scripts/copilot_hooks/stop_handover_guard.py\n\n"
                        "Required fixes:\n1. Add the stop hook.\n\n"
                        "Out of scope:\n- Broader refactors.\n\n"
                        "Required proof on return:\n- Tests to run: pytest\n\n"
                        "Return requirement:\n"
                        "- End with a new copy-paste prompt block for the QA chat.\n"
                        "```"
                    ),
                ]
            ),
            encoding="utf-8",
        )

        result = module.evaluate_stop_hook(_event_for(str(transcript)), "qa")

        assert result == {}

    def test_retry_active_does_not_loop_forever(self, tmp_path: Path) -> None:
        module = _load_stop_handover_guard_module()
        transcript = tmp_path / "retry_invalid.jsonl"
        transcript.write_text(
            _assistant_record("Still no fenced handover block."),
            encoding="utf-8",
        )

        result = module.evaluate_stop_hook(
            _event_for(str(transcript), stop_hook_active=True),
            "qa",
        )

        assert result == {}
