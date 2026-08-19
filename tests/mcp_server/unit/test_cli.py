# tests/mcp_server/unit/test_cli.py
"""
Tests for CLI.

@layer: Tests (Unit)
@dependencies: [contextlib, pytest, unittest.mock, mcp_server.cli]
"""

# Standard library
import contextlib
from pathlib import Path
from unittest.mock import MagicMock, patch

# Third-party
import pytest

from mcp_server.cli import main
from mcp_server.config.settings import ServerSettings, Settings


def test_cli_version(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that --version flag prints version and exits without running server."""
    with (
        patch("mcp_server.config.settings.metadata.version", return_value="3.0.0"),
        patch("sys.exit") as mock_exit,
        patch("mcp_server.cli.ServerBootstrapper") as mock_bootstrapper,
        patch("sys.argv", ["mcp-server", "--version"]),
    ):
        mock_exit.side_effect = SystemExit(0)
        with contextlib.suppress(SystemExit):
            main()

        mock_exit.assert_called_with(0)
        mock_bootstrapper.assert_not_called()

    captured = capsys.readouterr()
    assert "Phase-Gate MCP Server v3.0.0" in captured.out


def test_cli_run() -> None:
    """Test that main() bootstraps and runs the server when no arguments provided."""
    mock_server = MagicMock()
    mock_bootstrapper_instance = MagicMock()
    mock_bootstrapper_instance.bootstrap.return_value = mock_server

    with (
        patch("mcp_server.config.settings.metadata.version", return_value="3.0.0"),
        patch("mcp_server.cli.ServerBootstrapper", return_value=mock_bootstrapper_instance),
        patch("asyncio.run") as mock_asyncio_run,
        patch("sys.argv", ["mcp-server"]),
    ):
        main()
        mock_bootstrapper_instance.bootstrap.assert_called_once()
        mock_asyncio_run.assert_called_once_with(mock_server.run())


def test_cli_init_success(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test that --init copies assets to resolved_server_root."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    settings = Settings(
        server=ServerSettings(
            workspace_root=str(workspace),
            server_root_dir=".pgmcp",
        )
    )

    # Set up mock assets dir
    mock_assets = tmp_path / "mock_assets"
    (mock_assets / "config").mkdir(parents=True)
    (mock_assets / "templates").mkdir(parents=True)
    (mock_assets / "config" / "workflows.yaml").touch()
    import shutil  # noqa: PLC0415

    orig_copytree = shutil.copytree

    def mock_copytree(src, dst, *args, **kwargs):
        shutil.copytree = orig_copytree
        try:
            return shutil.copytree(mock_assets, dst, *args, **kwargs)
        finally:
            shutil.copytree = mock_copytree

    with (
        patch("sys.argv", ["mcp-server", "--init"]),
        patch("sys.exit") as mock_exit,
        patch("shutil.copytree", side_effect=mock_copytree),
    ):
        mock_exit.side_effect = SystemExit(0)
        with contextlib.suppress(SystemExit):
            main(settings)

        mock_exit.assert_called_with(0)

    server_root = workspace / ".pgmcp"
    assert (server_root / "config").exists()
    assert (server_root / "templates").exists()
    assert (server_root / "config" / "workflows.yaml").exists()
    version_file = server_root / ".version"
    assert version_file.exists()
    assert version_file.read_text(encoding="utf-8").strip() == settings.server.version


def test_cli_fails_fast_when_state_dir_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test that CLI exits with error if .pgmcp directory is missing."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    settings = Settings(
        server=ServerSettings(
            workspace_root=str(workspace),
            server_root_dir=".pgmcp",
        )
    )

    with (
        patch("sys.argv", ["mcp-server"]),
        patch("sys.exit") as mock_exit,
    ):
        mock_exit.side_effect = SystemExit(1)
        with contextlib.suppress(SystemExit):
            main(settings)

        mock_exit.assert_called_with(1)

    captured = capsys.readouterr()
    assert (
        "Please run with --init to initialize" in captured.err
        or "Please run with --init to initialize" in captured.out
    )


def test_cli_init_already_exists(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test that --init gracefully aborts if .pgmcp already exists."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    server_root = workspace / ".pgmcp"
    server_root.mkdir()

    settings = Settings(
        server=ServerSettings(
            workspace_root=str(workspace),
            server_root_dir=".pgmcp",
        )
    )

    with (
        patch("sys.argv", ["mcp-server", "--init"]),
        patch("sys.exit") as mock_exit,
    ):
        mock_exit.side_effect = SystemExit(1)
        with contextlib.suppress(SystemExit):
            main(settings)

        mock_exit.assert_called_with(1)

    captured = capsys.readouterr()
    assert "already exists" in captured.err or "already exists" in captured.out


def test_cli_init_flat_copy(tmp_path: Path) -> None:
    """Test that --init copies the entire assets directory and ignores template_registry.json."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    settings = Settings(
        server=ServerSettings(
            workspace_root=str(workspace),
            server_root_dir=".pgmcp",
        )
    )

    with (
        patch("sys.argv", ["mcp-server", "--init"]),
        patch("sys.exit") as mock_exit,
        patch("shutil.copytree") as mock_copytree,
    ):
        mock_exit.side_effect = SystemExit(0)
        with contextlib.suppress(SystemExit):
            main(settings)

        # Should be called once with assets_dir and resolved_server_root
        mock_copytree.assert_called_once()
        args, kwargs = mock_copytree.call_args

        # Verify source and target paths
        assert args[0].name == "assets"
        assert args[1] == workspace / ".pgmcp"
        assert kwargs.get("dirs_exist_ok") is True

        # Verify ignore patterns ignore template_registry.json
        ignore_func = kwargs.get("ignore")
        assert ignore_func is not None
        # ignore_func takes (directory_path, list_of_names) and returns a list of names to ignore
        ignored = ignore_func(str(workspace), ["workflows.yaml", "template_registry.json"])
        assert "template_registry.json" in ignored
        assert "workflows.yaml" not in ignored


def test_cli_degraded_server_on_config_error(tmp_path: Path) -> None:
    """Test that CLI boots DegradedMCPServer when ConfigError is raised."""
    from unittest.mock import AsyncMock  # noqa: PLC0415

    from mcp_server.core.exceptions import ConfigError  # noqa: PLC0415

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    server_root = workspace / ".pgmcp"
    server_root.mkdir()

    settings = Settings(
        server=ServerSettings(
            workspace_root=str(workspace),
            server_root_dir=".pgmcp",
        )
    )

    with (
        patch("sys.argv", ["mcp-server"]),
        patch("mcp_server.bootstrap.ServerBootstrapper.bootstrap") as mock_bootstrap,
        patch("mcp_server.cli.Settings.from_env", return_value=settings),
    ):
        mock_bootstrap.side_effect = ConfigError("Corrupt artifacts.yaml config")

        # Patch DegradedMCPServer class
        with patch("mcp_server.server.DegradedMCPServer") as mock_degraded_server:
            mock_server_instance = mock_degraded_server.return_value
            mock_server_instance.run = AsyncMock()

            main(settings)

            mock_degraded_server.assert_called_once_with(settings, "Corrupt artifacts.yaml config")
            mock_server_instance.run.assert_called_once()


def test_cli_degraded_server_on_version_mismatch(tmp_path: Path) -> None:
    """Test that CLI boots DegradedMCPServer on version validation failure."""
    from unittest.mock import AsyncMock  # noqa: PLC0415

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    server_root = workspace / ".pgmcp"
    server_root.mkdir()

    # Create a mismatched version file
    version_file = server_root / ".version"
    version_file.write_text("9.9.9\n", encoding="utf-8")

    settings = Settings(
        server=ServerSettings(
            workspace_root=str(workspace),
            server_root_dir=".pgmcp",
            bypass_version_check=False,
        )
    )

    with (
        patch("sys.argv", ["mcp-server"]),
        patch("mcp_server.cli.Settings.from_env", return_value=settings),
        patch("mcp_server.server.DegradedMCPServer") as mock_degraded_server,
    ):
        mock_server_instance = mock_degraded_server.return_value
        mock_server_instance.run = AsyncMock()

        main(settings)

        # Verify DegradedMCPServer was initialized with version mismatch error
        mock_degraded_server.assert_called_once()
        assert "Workspace version mismatch" in mock_degraded_server.call_args[0][1]


def test_cli_upgrade_missing_server_root_exits_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verify --upgrade when .pgmcp is missing prints error and exits code 1."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    settings = Settings(
        server=ServerSettings(workspace_root=str(workspace), server_root_dir=".pgmcp")
    )

    with (
        patch("sys.exit") as mock_exit,
        patch("sys.argv", ["mcp-server", "--upgrade"]),
    ):
        mock_exit.side_effect = SystemExit(1)
        with contextlib.suppress(SystemExit):
            main(settings=settings)

        mock_exit.assert_called_with(1)
        captured = capsys.readouterr()
        assert "Error: Server root directory" in captured.err


def test_cli_upgrade_success_exits_0(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Verify --upgrade triggers upgrader service and exits code 0 on success."""
    workspace = tmp_path / "workspace"
    server_root = workspace / ".pgmcp"
    server_root.mkdir(parents=True)
    settings = Settings(
        server=ServerSettings(workspace_root=str(workspace), server_root_dir=".pgmcp")
    )

    mock_upgrader_instance = MagicMock()
    mock_log = MagicMock()
    mock_log.from_version = "1.0.0"
    mock_log.to_version = "2.0.0"
    mock_upgrader_instance.execute_upgrade.return_value = mock_log

    with (
        patch(
            "mcp_server.services.workspace_upgrader.WorkspaceUpgrader",
            return_value=mock_upgrader_instance,
        ),
        patch("sys.exit") as mock_exit,
        patch("sys.argv", ["mcp-server", "--upgrade"]),
    ):
        mock_exit.side_effect = SystemExit(0)
        with contextlib.suppress(SystemExit):
            main(settings=settings)

        mock_exit.assert_called_with(0)
        captured = capsys.readouterr()
        assert "Successfully upgraded server workspace" in captured.out


def test_cli_upgrade_failure_exits_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Verify --upgrade handles upgrader exception, prints error to stderr, and exits code 1."""
    workspace = tmp_path / "workspace"
    server_root = workspace / ".pgmcp"
    server_root.mkdir(parents=True)
    settings = Settings(
        server=ServerSettings(workspace_root=str(workspace), server_root_dir=".pgmcp")
    )

    mock_upgrader_instance = MagicMock()
    mock_upgrader_instance.execute_upgrade.side_effect = RuntimeError("Upgrade failed")

    with (
        patch(
            "mcp_server.services.workspace_upgrader.WorkspaceUpgrader",
            return_value=mock_upgrader_instance,
        ),
        patch("sys.exit") as mock_exit,
        patch("sys.argv", ["mcp-server", "--upgrade"]),
    ):
        mock_exit.side_effect = SystemExit(1)
        with contextlib.suppress(SystemExit):
            main(settings=settings)

        mock_exit.assert_called_with(1)
        captured = capsys.readouterr()
        assert "Error upgrading server root: Upgrade failed" in captured.err


def test_version_consistency() -> None:
    """Verify version parity across SSOT files (pyproject.toml, manifest, settings.py)."""
    import yaml  # noqa: PLC0415

    from mcp_server.config.settings import Settings  # noqa: PLC0415

    repo_root = Path(__file__).resolve().parent.parent.parent.parent

    # 1. pyproject.toml
    pyproject_path = repo_root / "pyproject.toml"
    assert pyproject_path.exists()
    pyproject_text = pyproject_path.read_text(encoding="utf-8")
    assert 'version = "2.0.0"' in pyproject_text

    # 2. release_manifest.yaml
    manifest_path = repo_root / ".pgmcp" / "config" / "release_manifest.yaml"
    assert manifest_path.exists()
    manifest_data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    assert manifest_data.get("version") == "2.0.0"

    # 3. Settings default version
    settings = Settings()
    assert settings.server.version == "2.0.0"
