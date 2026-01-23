"""
Version hash computation for template registry (Issue #72 Task 1.2).

Computes deterministic 8-character hashes from artifact type and tier chain versions.
Includes collision safety through artifact_type prefix.
"""

import hashlib
import re
from pathlib import Path


def extract_template_version(template_path: Path) -> str:
    """
    Extract version from template TEMPLATE_METADATA.
    
    Reads template file and extracts version from TEMPLATE_METADATA YAML block.
    Falls back to "1.0.0" if not found.
    
    Args:
        template_path: Absolute path to template file
        
    Returns:
        Version string (e.g., "1.0.0")
        
    Example template format:
        {#-
        TEMPLATE_METADATA:
          version: "1.0.0"
        -#}
    """
    try:
        content = template_path.read_text(encoding="utf-8")
        
        # Extract TEMPLATE_METADATA block
        # Pattern matches: {#- TEMPLATE_METADATA: ... -#}
        metadata_pattern = r'\{#-?\s*TEMPLATE_METADATA:(.*?)-?#\}'
        match = re.search(metadata_pattern, content, re.DOTALL)
        
        if not match:
            # Fallback: try simple {#- Version: X.X.X -#} format
            version_pattern = r'\{#-\s*Version:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*-?#\}'
            version_match = re.search(version_pattern, content)
            if version_match:
                return version_match.group(1)
            return "1.0.0"  # Default fallback
        
        metadata_yaml = match.group(1)
        
        # Extract version field from YAML
        version_pattern = r'version:\s*["\']?([0-9]+\.[0-9]+\.[0-9]+)["\']?'
        version_match = re.search(version_pattern, metadata_yaml)
        
        if version_match:
            return version_match.group(1)
        
        return "1.0.0"  # Default fallback
        
    except Exception:
        return "1.0.0"  # Fallback on any error


def compute_version_hash(
    artifact_type: str,
    template_file: str,
    tier_chain: list[tuple[str, str]],
    template_root: Path | None = None
) -> str:
    """
    Compute 8-char SHA256 hash of tier version chain.

    Collision safety: Includes artifact_type prefix, unique per type.

    Args:
        artifact_type: Artifact type (e.g., "worker", "research") from artifacts.yaml
        template_file: Concrete template (e.g., "worker.py.jinja2" or "concrete/dto.py.jinja2")
        tier_chain: Parent template chain from introspection
            Format: [(template_name, version), ...]
            Example: [("tier0_base_artifact", "1.0.0"), ("tier1_base_code", "1.1.0")]
        template_root: Root directory for templates (for version extraction)
            If None, uses default from get_template_root()

    Returns:
        8-character hex hash (e.g., "a3f7b2c1")

    Note (Task 1.1b Fix):
        - No longer uses placeholder "concrete" string
        - Extracts real version from concrete template TEMPLATE_METADATA
        - Falls back to "1.0.0" if extraction fails
    """
    # Get template root for version extraction
    if template_root is None:
        from mcp_server.config.template_config import get_template_root
        template_root = get_template_root()
    
    # Build full chain (parents + concrete)
    full_chain = list(tier_chain)  # Copy to avoid mutation
    
    # Extract concrete template version from file
    concrete_template_path = template_root / template_file
    concrete_version = extract_template_version(concrete_template_path)
    
    # Extract concrete template name without .jinja2
    concrete_name = template_file.replace(".jinja2", "")
    # Remove path components (e.g., "concrete/dto.py" → "dto.py")
    concrete_name = Path(concrete_name).name
    
    full_chain.append((concrete_name, concrete_version))

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
