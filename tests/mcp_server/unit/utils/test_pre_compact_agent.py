"""Regression tests for the agent PreCompact transcript parser."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType


def _load_pre_compact_agent_module() -> ModuleType:
    module_path = (
        Path(__file__).resolve().parents[4] / "scripts" / "copilot_hooks" / "pre_compact_agent.py"
    )
    spec = spec_from_file_location("pre_compact_agent", module_path)
    assert spec is not None
    assert spec.loader is not None

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
