"""Regression tests for the agent PreCompact transcript parser."""

from types import ModuleType

import copilot_orchestration.hooks.pre_compact_agent as _pre_compact_agent_module


def _load_pre_compact_agent_module() -> ModuleType:
    return _pre_compact_agent_module


class TestParseTranscriptContent:
    """Regression coverage for transcript parsing in the PreCompact hook."""

    def test_parses_single_json_document(self) -> None:
        module = _load_pre_compact_agent_module()

        payload = module.parse_transcript_content(
            '{"role": "user", "content": "Fix scripts/copilot_hooks/pre_compact_agent.py"}'
        )

        assert payload == {
            "role": "user",
            "content": "Fix scripts/copilot_hooks/pre_compact_agent.py",
        }

    def test_parses_jsonl_transcript_records(self) -> None:
        module = _load_pre_compact_agent_module()
        transcript = "\n".join(
            [
                '{"type": "session.start"}',
                '{"role": "user", "content": "Fix scripts/copilot_hooks/pre_compact_agent.py"}',
                '{"role": "assistant", "content": "Implemented parser fix."}',
            ]
        )

        payload = module.parse_transcript_content(transcript)
        records = module.collect_message_records(payload)

        assert isinstance(payload, list)
        assert [record["role"] for record in records] == ["user", "assistant"]
        assert records[0]["text"] == "Fix scripts/copilot_hooks/pre_compact_agent.py"
