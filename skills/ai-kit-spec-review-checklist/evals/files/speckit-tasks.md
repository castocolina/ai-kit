# Tasks: CSV export

**Input**: design documents from `specs/001-csv-export/`

## Phase 1: Setup

- [ ] T001 Create the package folder `src/export/` with an empty `__init__.py`

## Phase 2: Core

- [ ] T002 [P] Add the `ExportSettings` dataclass (delimiter, header flag) in `src/export/settings.py`
- [ ] T003 [P] Add `load_settings()` in `src/export/settings.py`, returning an `ExportSettings` built from the user's saved choices
- [ ] T004 [P] Add the CSV writer in `src/export/writer.py`, taking the delimiter and the header flag as plain arguments

## Phase 3: Wiring

- [ ] T005 Wire the Export CSV button to `load_settings()` and the writer in `src/ui/report_page.py`
