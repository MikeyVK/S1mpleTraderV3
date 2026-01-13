# Config-locatie onderzoek (MCP server vs project config)

**Datum:** 2026-01-11  
**Scope:** Inventariseren waar de repo (code + docs + VS Code config) aannames maakt over *config locaties* en waar paden hardcoded zijn. Doel: config-first gedrag zonder machine-specifieke paden, en minder verwarring tussen MCP-server-config en ST3-projectconfig.

---

## 1. Samenvatting (TL;DR)

### Kernproblemen
- Machine-specifieke paden komen voor in de MCP setup en docs (bv. `D:/dev/...`, `d:/dev/...`, `file:///d:/...`). Dit breekt portability.
- Config-locatie is inconsistent gedocumenteerd:
  - MCP server settings komen uit `mcp_config.yaml` (met `MCP_CONFIG_PATH` override),
  - “platform config” (workflows/labels/quality/state/projects) zit in `.st3/`,
  - docs noemen soms ook `config/`.
- `.st3/` is effectief hardcoded op meerdere plekken in code voor platform-bestanden (`workflows.yaml`, `labels.yaml`, `quality.yaml`, `state.json`, `projects.json`).

### Aanbevolen richting
- Maak een expliciet onderscheid:
  - MCP server config: `mcp_config.yaml` (of via `MCP_CONFIG_PATH`), met portable defaults.
  - Platform/project-automation config: directory (nu `.st3/`) die configureerbaar is via een setting (bv. `platform_config_dir`).
- Verwijder absolute paden uit:
  - `mcp_config.yaml` (geen `D:/dev/...`)
  - `.vscode/mcp.json` (`command` en `cwd` niet hardcoded)
  - docs (geen `d:/dev/...` en geen `file:///...` links)

---

## 2. Observaties (evidence)

### 2.1 MCP server settings en config pad
- Settings loader ondersteunt `MCP_CONFIG_PATH` env override.
  - Zie mcp_server/config/settings.py
- In de praktijk kan `mcp_config.yaml` een absolute `workspace_root` bevatten.
  - Zie mcp_config.yaml

**Risico:** als `workspace_root` hardcoded is, draaien tools (filesystem, project/phase managers) tegen een vaste directory i.p.v. de actuele workspace.

### 2.2 VS Code MCP registratie
- In `.vscode/mcp.json` kunnen `command` en `cwd` hardcoded zijn (machine pad + workspace pad).
  - Zie .vscode/mcp.json

**Risico:** checkout op andere machine/locatie faalt direct.

### 2.3 Platform config / `.st3/` hardcodings
In code wordt `.st3/` gebruikt als platform config directory voor o.a.:
- workflows: `.st3/workflows.yaml`
- labels: `.st3/labels.yaml`
- quality: `.st3/quality.yaml`
- state: `.st3/state.json`
- projects: `.st3/projects.json`

Concrete plekken (niet uitputtend):
- mcp_server/config/workflows.py
- mcp_server/config/label_config.py
- mcp_server/config/quality_config.py
- mcp_server/managers/phase_state_engine.py
- mcp_server/managers/project_manager.py

**Risico:** je kunt niet clean “MCP server config” los trekken van “project config” als `.st3` niet te verplaatsen is.

### 2.4 Docs met absolute paden / file:/// links
- In docs wordt `d:/dev/SimpleTraderV3` als voorbeeld gebruikt.
  - Zie docs/mcp_server/ARCHITECTURE.md
- In docs staan `file:///d:/dev/...` links die alleen lokaal werken.
  - Zie docs/mcp_server/IMPLEMENTATION_PLAN.md

---

## 3. Aanbevelingen (concreet)

### 3.1 Portable defaults in `mcp_config.yaml`
- Gebruik `server.workspace_root: "."` (of laat weg zodat `os.getcwd()` geldt).
- Geen absolute paden in repo-tracked config.

### 3.2 Maak platform config dir configureerbaar
Introduceer een setting, bv:
- `server.platform_config_dir: ".st3"`

en env overrides, bv:
- `MCP_PLATFORM_CONFIG_DIR`
- (optioneel) `MCP_WORKSPACE_ROOT`
- (optioneel) `MCP_SERVER_NAME`

Pas vervolgens alle `.st3/...` path-joins aan naar:
- `Path(settings.server.workspace_root) / settings.server.platform_config_dir / ...`

### 3.3 VS Code MCP configuratie
Gebruik VS Code variabelen i.p.v. absolute paden:
- `"cwd": "${workspaceFolder}"`
- `"command": "${workspaceFolder}\\.venv\\Scripts\\python.exe"`

Alternatief (minder strak): `command: "python"` en werk met geselecteerde interpreter, maar dat is minder deterministisch.

### 3.4 Doc cleanup
- Vervang `d:/dev/...` door placeholders (`/absolute/path/to/...`) of beschrijving.
- Vervang `file:///...` links door repo-relatieve markdown links.

---

## 4. Voorstel: gecontroleerd wijzigingsplan (in kleine PR’s)

1. Docs-only PR: alle absolute paden en `file:///` links vervangen.
2. Settings PR: `platform_config_dir` + env overrides toevoegen.
3. Code migratie PR: per module de `.st3` literal vervangen door setting.
4. Test PR: tests toevoegen die aantonen dat platform config dir wijzigbaar is (bv. tmp_path + custom `platform_config_dir`).

---

## 5. Open vragen (voor jouw besluit)

- Wil je `.st3/` hernoemen naar iets explicieter voor MCP tooling (bv. `.mcp/`, `.workflow/`, `.st3-workflow/`)?
- Wil je `server.name` hernoemen van `st3-workflow` naar iets minder project-verwarrends (bv. `simpletrader-workflow`)?
- Moet de MCP server config (`mcp_config.yaml`) in een aparte directory (bv. `.mcp/mcp_config.yaml`) of blijft die op root (simpel)?
