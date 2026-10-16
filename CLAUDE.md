# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

```bash
python3 main.py config/config.json
# or
./boot.sh
```

The config file path is the sole CLI argument and supports both JSON and YAML formats.

## Installing Dependencies

```bash
pip install -r requirements.txt
```

## Architecture Overview

**Music-Fuzzy (mfuz)** is a PyQt6 music management application with a tab-based plugin architecture.

### Core Components

- **`main.py`** — `TabManager` (QMainWindow) that loads modules dynamically from config
- **`base_module.py`** — Base class all modules must inherit from
- **`themes/themes.py`** — Centralized theme system; all UI theming flows through here
- **`db_creator.py`** — Orchestrates database population via config-driven script execution

### Module System

Modules are defined in `config/config.json` under the `modules` array. Each entry specifies:
- `path` — Python file to load (e.g., `"modules/music_fuzzy_module.py"`)
- `args` — Dict passed as kwargs to the module constructor
- `logging` — Per-module log settings

Disabled modules live in `modulos_desactivados`. To enable/disable a module, move its entry between these two arrays. Modules must inherit from `BaseModule`.

Active modules: `music_fuzzy_module`, `jaangle_module`, `muspy_releases_module`, `conciertos_module`, `estadisticas_module`, `url_playlist`.

### Database

Primary database: `db/sqlite/musica_local.sqlite` (SQLite, WAL mode, ~1 GB). Core tables: `artists`, `albums`, `tracks`. The `db/` directory contains standalone scripts for populating the database from external services (LastFM, MusicBrainz, Spotify, Discogs, charts, etc.).

Database tools are in `db/tools/` — these are standalone scripts, not part of the module system.

### UI Files

Qt Designer `.ui` files live under `ui/` organized by module (e.g., `ui/fuzzy/`, `ui/jaangle/`). Loaded at runtime via `PyQt6.uic.loadUi()`. Compiled Python stubs are in `ui/ui_*.py`. Icons are SVGs in `ui/svg/` bundled via `images.qrc` → `resources_rc.py`.

### Submodule Structure

Large modules split their logic into `modules/submodules/<name>/`:
- `fuzzy/` — search_handler, database_manager, ui_updater, link_manager, player_manager
- `jaangle/` — spotify_player, listenbrainz_player
- `muspy/` — spotify_manager, lastfm_manager, mb_manager, cache_manager, progress_utils
- `conciertos/` — ticketmaster, setlistfm, spotify, worker

### Logging

Custom logger with a `UI` level (15) between DEBUG and INFO. Colored console output + optional file output to `.content/logs/multi_module_manager.log`. Configured via `logging_options` in config.json.

### External Integrations

Spotify, LastFM, MusicBrainz, Discogs, YouTube, Ticketmaster, Setlist.fm, ListenBrainz, Bluesky. Credentials are stored in `config/config.json` under `global_theme_config` and per-module `args`.
