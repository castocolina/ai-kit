# Requirements: CSV export

## Introduction

Users export a report as a CSV file from the report page.

## Requirements

### Requirement 1

**User Story:** As an analyst, I want to export the visible report rows, so that I can open them in a spreadsheet.

#### Acceptance Criteria

1. WHEN the user selects Export CSV THE SYSTEM SHALL write every visible row to one CSV file with a header line.
2. IF the report has no rows THEN THE SYSTEM SHALL show the message "Nothing to export" and write no file.

### Requirement 2

**User Story:** As an analyst, I want exports to work well on big reports.

#### Acceptance Criteria

1. Exports should be fast and handle big reports without problems.
