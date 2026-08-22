# Conversation and Design Plan

## User Request Summary
The user requested an evolution of their web scraping codebase into a task scheduler system.

Requirements include:
- Interactive CLI for task creation.
- Input capabilities for lists of search terms, locality strings, and sets of zip codes.
- Alternative zip code entry via State selection (reading from `finalqueuebuilder.py`).
- Task queue management (running vs pipeline).
- Ability to cancel, reorder, delete tasks.
- Task execution modes: Emails only, Phones only, Both.
- Centralized tracking via `tasks.json`, `Task_Ids.txt`, and `health_profiles.json`.
- Unified Codebase: Refactor legacy scripts into modular Python functions (no dummy folders for email flow).
- Output cleanup post-run: transferring raw files to a timestamped folder inside `Logs_NewRuns`. Inside, structure includes `temp_csvs/`, `aggregated_results/`, and `final files/`.
- Ability to resume or add operations to previously completed tasks using their ID.
- Network tolerance (pause on disconnect by pinging Google).
- Healthy Chrome profile logic: test profile on a dummy search, allow creation (robocopy, manual extension setup, verification) and deletion.

The legacy scripts to be refactored into a single package:
- `lead.py`
- `aggregate.py`
- `pipeline.py`
- `python_findphone.py` / `findphone.py`
- `clean_emails.py`
- `extract_pure_emails.py`

## Implementation Plan

### High-Level Design (HLD)

1. **Interactive CLI Manager (`main.py`)**: The primary interface. It presents menus to add tasks, view the queue, delete/reorder tasks, and manage profiles. State-to-Zipcode mappings are parsed from `finalqueuebuilder.py`.
2. **Unified Codebase (Refactoring)**: The existing separate scripts will be refactored into modular Python functions within a unified package. 
3. **State & Queue Management**: All tasks are stored in `admin/tasks.json`. 
4. **Sequential Task Executor**: A background runner that picks the top task from the queue, assigns a healthy profile, and executes.
5. **Healthy Profiles Manager**: CLI can manage Chrome browser profiles (robocopy, setup, test scrape). Healthy profiles are recorded in `health_profiles.json`.
6. **Progress Tracker & Resumption**: Granular tracking via `history.json` allows pause/resume.
7. **Network Monitor**: Background thread pings Google; if it drops, sets a global `PAUSE` flag.
8. **Artifact Archiver**: Post-run cleanup moves outputs to `Logs_NewRuns/`, with `aggregated_results` and `final files`.

### Low-Level Design (LLD)

**Data Models**
- Task Object: UUID, search_terms, locality, zip_codes, mode, status, progress.

**Directory Structure (Desktop/Firecrawl/)**
- `main.py`
- `scraper_core/` (refactored modules)
- `profile_manager.py`
- `network_monitor.py`
- `file_manager.py`
- `admin/` -> `tasks.json`, `Task_Ids.txt`, `health_profiles.json`
- `Logs_NewRuns/` -> `<Task_Folder>/` -> `history.json`, `temp_csvs/`, `aggregated_results/`, `final files/`

**Pipeline Execution Flows**
- Emails Only: `pipeline` -> `clean_emails` -> `extract_pure_emails` -> Archive.
- Phones Only: `lead` -> `aggregate` -> `findphone` -> Archive.
- Both: `pipeline` -> `findphone` -> Archive.

*(End of Plan)*
