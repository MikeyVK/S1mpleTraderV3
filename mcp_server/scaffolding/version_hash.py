"""
Version hash computation for template registry (Issue #72 Task 1.2).

Computes deterministic 8-character hashes from artifact type and tier chain versions.
Includes collision safety through artifact_type prefix.
"""

import hashlib


def compute_version_hash(
    artifact_type: str,
    template_file: str,
    tier_chain: list[tuple[str, str]]
) -> str:
    """
    Compute 8-char SHA256 hash of tier version chain.

    Collision safety: Includes artifact_type prefix, unique per type.

    Args:
        artifact_type: Artifact type (e.g., "worker", "research") from artifacts.yaml
        template_file: Concrete template (e.g., "worker.py.jinja2")
        tier_chain: Parent template chain from introspection
            Format: [(template_name, version), ...]
            Example: [("tier0_base_artifact", "1.0.0"), ("tier1_base_code", "1.1.0")]

    Returns:
        8-character hex hash (e.g., "a3f7b2c1")

    Note:
        artifact_type MUST be passed explicitly to avoid extraction bugs.
        Previous attempt: artifact_type = template_file.replace(".jinja2", "").split("/")[-1]
        Bug: "worker.py.jinja2" → "worker.py" (not "worker")
        Fix: ArtifactManager provides artifact_type from artifacts.yaml registry
    """
    # Build full chain (parents + concrete)
    full_chain = list(tier_chain)  # Copy to avoid mutation
    # Extract concrete template name without .jinja2
    concrete_name = template_file.replace(".jinja2", "")
    # For now, use concrete_name as version identifier (will be replaced with catalog lookup)
    full_chain.append((concrete_name, "concrete"))

    # Build hash input: "{type}|{tier}@{version}|..."
    parts = [artifact_type]
    for template_name, version in full_chain:
        # Normalize template name (remove _base_ prefix for consistency)
        short_name = template_name.replace("_base_", "_")
        parts.append(f"{short_name}@{version}")

    hash_input = "|".join(parts)

    # SHA256 truncated to 8 chars (4 bytes = 2^32 possibilities per artifact type)
    full_hash = hashlib.sha256(hash_input.encode()).hexdigest()
    return full_hash[:8]
