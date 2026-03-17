# Setup — Nieuwe Machine

Deze map bevat de portabele configuratiebestanden die niet via git getracked worden
maar noodzakelijk zijn om de MCP server werkend te krijgen op een nieuwe machine.

## Vereiste stappen

### 1. GITHUB_TOKEN instellen

De MCP server leest het token via `${env:GITHUB_TOKEN}`. Stel dit in als
permanente omgevingsvariabele (eenmalig per machine):

```powershell
[System.Environment]::SetEnvironmentVariable("GITHUB_TOKEN", "ghp_xxxxxxxxxxxx", "User")
```

Herstart VS Code daarna zodat de variabele beschikbaar is.

### 2. mcp.json kopiëren

Kopieer `docs/setup/mcp.json` naar `.vscode/mcp.json`:

```powershell
Copy-Item docs/setup/mcp.json .vscode/mcp.json
```

Het bestand gebruikt `${workspaceFolder}` en `${env:GITHUB_TOKEN}` — er zijn
**geen paden of geheimen** die je handmatig hoeft aan te passen.

### 3. Python virtual environment aanmaken

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\pip install -r requirements-dev.txt
```

### 4. VS Code herladen

Herstart VS Code (of gebruik `Developer: Reload Window`). De MCP server
start automatisch op via de `mcp.json` configuratie.

## Verificatie

Controleer in VS Code of de MCP server actief is:
- Open de Copilot Chat
- Typ `health_check` — de MCP server moet reageren

## Overzicht niet-getracked bestanden

| Bestand | Beschrijving | Actie |
|---|---|---|
| `.vscode/mcp.json` | MCP server config | Kopieer vanuit `docs/setup/mcp.json` |
| `GITHUB_TOKEN` | GitHub API token | Stel in als User environment variable |
| `.venv/` | Python virtual environment | Recreëer via `requirements.txt` |
