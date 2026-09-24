"""Static HTML dashboard: embed refined rows, no server, no export step."""

from __future__ import annotations

import json
import os
import sqlite3
import stat
import tempfile

# Explicit full column list matching refined_store.py's CREATE TABLE.
_QUERY_COLUMNS = (
    "id",
    "raw_ref",
    "runtime",
    "session_id",
    "turn_id",
    "date",
    "timestamp",
    "model",
    "command_text",
    "family",
    "command_shape",
    "step_index",
    "step_count",
    "operator",
    "execution_certain",
    "resolved_cwd",
    "source_confidence",
    "tokens_input",
    "tokens_output",
    "price",
    "price_confidence",
    "rtk_input_tokens",
    "rtk_output_tokens",
    "rtk_saved_tokens",
    "rtk_savings_pct",
    "rtk_rewrote",
    "inferred_family",
    "inferred_confidence",
    "exec_duration_ms",
)

_HTML_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>ai-kit usage metrics</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500&display=swap">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined">
<script type="module">
/* unpkg's "?module" transform resolves every bare specifier (tslib, lit/*)
   to a canonical per-version-range URL, so all nine submodules below share
   ONE instance of shared internals like md-focus-ring instead of each
   getting its own bundled copy -- esm.run/jsDelivr's "+esm" transform
   bundles each deep submodule import independently and re-registers
   shared custom elements, which throws
   "the name 'md-focus-ring' has already been used with this registry"
   (confirmed live and documented upstream:
   https://github.com/jsdelivr/jsdelivr/issues/18473,
   https://github.com/material-components/material-web/discussions/5587).

   md-outlined-select/md-select-option are deliberately NOT imported: live
   Playwright testing reproduced its md-menu popup closing itself on the
   very click that opens it -- worse in Firefox than Chromium, consistent
   with the browser-dependent light-dismiss/focus-retargeting bugs tracked
   upstream against md-menu. The 4 filter dropdowns below use native
   <select> instead (fillSelect() populates <option>, styled in CSS to
   match the outlined-field look), which has none of that component's
   focus-trap machinery to misfire. */
import "https://unpkg.com/@material/web@2.5.0/checkbox/checkbox.js?module";
import "https://unpkg.com/@material/web@2.5.0/textfield/outlined-text-field.js?module";
import "https://unpkg.com/@material/web@2.5.0/button/text-button.js?module";
import "https://unpkg.com/@material/web@2.5.0/button/filled-button.js?module";
import "https://unpkg.com/@material/web@2.5.0/iconbutton/icon-button.js?module";
import "https://unpkg.com/@material/web@2.5.0/icon/icon.js?module";
import "https://unpkg.com/@material/web@2.5.0/dialog/dialog.js?module";
import "https://unpkg.com/@material/web@2.5.0/progress/linear-progress.js?module";
</script>
<script type="module">
import { Virtualizer, observeElementRect, observeElementOffset, elementScroll } from "https://esm.run/@tanstack/virtual-core@3.17.11";
window.__virtualCore = {
  Virtualizer: Virtualizer,
  observeElementRect: observeElementRect,
  observeElementOffset: observeElementOffset,
  elementScroll: elementScroll
};
window.dispatchEvent(new Event("virtual-core-ready"));
</script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js"
        integrity="sha384-jb8JQMbMoBUzgWatfe6COACi2ljcDdZQ2OxczGA3bGNeWe+6DChMTBJemed7ZnvJ"
        crossorigin="anonymous"></script>
<style>
:root {
  --md-sys-color-surface: #FFFBFE;
  --md-sys-color-surface-variant: #E7E0EC;
  --md-sys-color-primary: #6750A4;
  --md-sys-color-error: #B3261E;
  --md-sys-color-on-surface: #1C1B1F;
  --md-sys-color-outline: #79747E;
  --md-sys-typescale-body-size: 16px;
  --md-sys-typescale-body-weight: 400;
  --md-sys-typescale-body-line-height: 24px;
  --md-sys-typescale-label-size: 14px;
  --md-sys-typescale-label-weight: 500;
  --md-sys-typescale-label-line-height: 20px;
  --md-sys-typescale-heading-size: 22px;
  --md-sys-typescale-heading-weight: 400;
  --md-sys-typescale-heading-line-height: 28px;
  --md-sys-typescale-display-size: 24px;
  --md-sys-typescale-display-weight: 400;
  --md-sys-typescale-display-line-height: 32px;
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;
  --space-2xl: 48px;
  /* Subtle tonal row treatments for the table -- distinct from, and
     lighter than, --md-sys-color-surface-variant (which the filter bar
     and chart panels already use), so the table's own rhythm doesn't
     compete with those surfaces for visual weight. */
  --row-stripe: #F7F2FA;
  --row-hover: #ECE6F0;
  --date-input-color-scheme: light;
  --date-icon-filter: none;
}
@media (prefers-color-scheme: dark) {
  :root {
    --md-sys-color-surface: #1C1B1F;
    --md-sys-color-surface-variant: #49454F;
    --md-sys-color-primary: #D0BCFF;
    --md-sys-color-error: #F2B8B5;
    --md-sys-color-on-surface: #E6E1E5;
    --md-sys-color-outline: #938F99;
    --row-stripe: #242327;
    --row-hover: #2D2C31;
    --date-input-color-scheme: dark;
    --date-icon-filter: invert(1);
  }
}
body {
  font-family: "Roboto", sans-serif;
  background: var(--md-sys-color-surface);
  color: var(--md-sys-color-on-surface);
  font-size: var(--md-sys-typescale-body-size);
  font-weight: var(--md-sys-typescale-body-weight);
  line-height: var(--md-sys-typescale-body-line-height);
  margin: var(--space-2xl) var(--space-lg);
}
h1 {
  font-size: var(--md-sys-typescale-display-size);
  font-weight: var(--md-sys-typescale-display-weight);
  line-height: var(--md-sys-typescale-display-line-height);
}
/* D-20 (revised): the filter bar controls what the charts show, so it
   reads BEFORE them, as its own full-width row -- not squeezed into the
   same row beside them. That side-by-side arrangement (D-20's original
   form) is what the live UAT feedback specifically named ("graficos al
   mismo nivel de los filtros") as still wrong: cramped charts, an
   over-narrow filter column, and no natural reading order between
   "narrow the data" and "see the result". Stacking top-to-bottom removes
   all three at once. */
#dashboard-top {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
  margin-bottom: var(--space-lg);
  width: 100%;
}
#charts-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-xl);
  width: 100%;
}
#filters {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: var(--space-md) var(--space-lg);
  background: var(--md-sys-color-surface-variant);
  padding: var(--space-lg);
  border-radius: 4px;
  width: 100%;
  box-sizing: border-box;
}
#filters label {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  font-size: var(--md-sys-typescale-label-size);
  font-weight: var(--md-sys-typescale-label-weight);
  line-height: var(--md-sys-typescale-label-line-height);
}
#filters md-outlined-text-field {
  min-width: 140px;
}
/* Native <select> in place of md-outlined-select (see the import-block
   comment above for why) -- styled to read as the same outlined-field
   family as md-outlined-text-field beside it: same height, corner
   radius, and outline color, so swapping the implementation doesn't
   read as a visual regression. */
#filters select {
  min-width: 140px;
  height: 40px;
  box-sizing: border-box;
  padding: 0 var(--space-sm);
  border: 1px solid var(--md-sys-color-outline);
  border-radius: 4px;
  background: var(--md-sys-color-surface);
  color: var(--md-sys-color-on-surface);
  font-family: inherit;
  font-size: var(--md-sys-typescale-body-size);
  cursor: pointer;
}
#filters select:hover {
  border-color: var(--md-sys-color-on-surface);
}
#filters select:focus-visible {
  outline: 2px solid var(--md-sys-color-primary);
  outline-offset: -1px;
  border-color: var(--md-sys-color-primary);
}
#filters select:disabled {
  cursor: default;
  opacity: 0.6;
}
/* D-13: two native date inputs visually merged into one bordered,
   flight-booking-style control with a single shared <label> above it --
   no @material/web date-range component exists (UI-SPEC.md live-checked). */
#date-range-group {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  border: 1px solid var(--md-sys-color-outline);
  border-radius: 4px;
  padding: 0 var(--space-sm);
  background: var(--md-sys-color-surface);
  height: 40px;
  box-sizing: border-box;
}
#date-range-group input[type="date"] {
  border: none;
  background: transparent;
  padding: var(--space-sm) 0;
  font-family: inherit;
  font-size: var(--md-sys-typescale-body-size);
  color: var(--md-sys-color-on-surface);
  color-scheme: var(--date-input-color-scheme, light);
  cursor: pointer;
}
/* The browser's own calendar-icon glyph defaults to near-black -- on the
   dark palette below it goes nearly invisible against the same dark
   field background. Inverting it in that palette is the fix; there is
   no cross-browser way to recolor the glyph directly. */
#date-range-group input[type="date"]::-webkit-calendar-picker-indicator {
  filter: var(--date-icon-filter, none);
  cursor: pointer;
  border-radius: 4px;
  padding: 2px;
}
#date-range-group input[type="date"]::-webkit-calendar-picker-indicator:hover {
  background: var(--md-sys-color-surface-variant);
}
#date-range-group:focus-within {
  border-color: var(--md-sys-color-primary);
  outline: 2px solid var(--md-sys-color-primary);
  outline-offset: -1px;
}
#date-range-group .date-range-sep {
  color: var(--md-sys-color-outline);
  font-size: var(--md-sys-typescale-label-size);
}
/* Quick-select chips beside the flight-booking-style range control --
   set the two date inputs programmatically rather than requiring the
   user to type or pick each end of a range by hand for the common
   cases (today / last week / last 30 days / calendar month / no
   filter). "month" (last 30 days) is the default active preset on
   initial page load. */
#date-presets {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2xs, 4px);
  margin-top: var(--space-xs);
}
#date-presets md-text-button {
  --md-text-button-label-text-size: var(--md-sys-typescale-label-size);
  --md-text-button-container-height: 28px;
}
#date-presets md-text-button[data-active] {
  --md-text-button-label-text-color: var(--md-sys-color-primary);
  font-weight: var(--md-sys-typescale-label-weight);
  text-decoration: underline;
}
#clear-filters {
  align-self: flex-end;
}
/* Shared badge treatment (source_confidence AND the execution-uncertain
   marker) -- error-tinted, per UI-SPEC's Destructive/warning role. */
.badge {
  display: inline-block;
  padding: 2px var(--space-xs);
  border: 1px solid var(--md-sys-color-error);
  border-radius: 4px;
  color: var(--md-sys-color-error);
  font-size: var(--md-sys-typescale-label-size);
  font-weight: var(--md-sys-typescale-label-weight);
  line-height: var(--md-sys-typescale-label-line-height);
}
/* D-22: the checkbox has no default (unfocused) visual weight from
   @material/web alone -- give it visible border/fill contrast against the
   filter bar's surface-variant background, independent of :focus/:hover. */
#group-by-session {
  display: inline-flex;
  border: 1.5px solid var(--md-sys-color-outline);
  border-radius: 4px;
  background: var(--md-sys-color-surface);
}
/* D-18: shared styling for all three chart panels (runtime doughnut,
   tokens/price-per-day, family/subfamily distribution) -- generalized from
   Plan 01's single #chart-runtime-panel rule so a new panel only needs the
   .chart-panel/.chart-fallback classes, not a bespoke rule. */
.chart-panel {
  background: var(--md-sys-color-surface-variant);
  padding: var(--space-lg);
  border-radius: 4px;
  flex: 1 1 280px;
  min-width: 260px;
}
.chart-panel-title {
  font-size: var(--md-sys-typescale-heading-size);
  font-weight: var(--md-sys-typescale-heading-weight);
  line-height: var(--md-sys-typescale-heading-line-height);
  margin: 0 0 var(--space-md) 0;
}
.chart-fallback {
  color: var(--md-sys-color-error);
  font-size: var(--md-sys-typescale-label-size);
  display: none;
}
/* D-21: every chart canvas scales with its container's width instead of
   rendering at a fixed pixel size -- the wrapper gets a clamp()-based
   (never a bare fixed-pixel) height via CSS, width: 100%, and Chart.js's
   own responsive: true + maintainAspectRatio: false (set on every chart's
   options below) drives the canvas itself from that container. No new
   resize-observer JS is needed beyond what responsive: true already does. */
.chart-canvas-wrap {
  position: relative;
  width: 100%;
  height: clamp(260px, 36vh, 400px);
}
#table-scroll {
  overflow-y: auto;
  max-height: 480px;
  width: 100%;
  position: relative;
  border: 1px solid var(--md-sys-color-outline);
}
#usage-table {
  border-collapse: collapse;
  width: 100%;
}
#usage-table thead {
  position: sticky;
  top: 0;
  z-index: 1;
  background: var(--md-sys-color-surface-variant);
  border-bottom: 2px solid var(--md-sys-color-outline);
}
#usage-table thead tr, #usage-table tbody tr {
  display: flex;
  width: 100%;
}
#usage-table th, #usage-table td {
  padding: var(--space-sm) var(--space-md);
  text-align: left;
  box-sizing: border-box;
  border-bottom: 1px solid var(--md-sys-color-outline);
  overflow: hidden;
}
#usage-table th {
  cursor: pointer;
  font-size: var(--md-sys-typescale-label-size);
  font-weight: var(--md-sys-typescale-label-weight);
  line-height: var(--md-sys-typescale-label-line-height);
  padding-top: var(--space-md);
  padding-bottom: var(--space-md);
}
#usage-tbody {
  display: block;
  position: relative;
}
#usage-tbody tr {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 56px;
}
/* Alternating tonal rows and a hover highlight give a 13-column,
   thousands-of-rows table a scannable rhythm without touching the
   locked 56px row height (SD-2's virtualizer estimateSize constant).
   nth-child parity tracks visual row position within the current
   virtualized paint, which is what a reader's eye actually follows. */
#usage-tbody tr:nth-child(even) {
  background: var(--row-stripe);
}
#usage-tbody tr:hover {
  background: var(--row-hover);
}
/* D-10/D-12 flat-mode column order: runtime, model, family, subfamily,
   command, exec time, date, tokens_input, tokens_output, price,
   source_confidence, execution, session -- 13 columns. */
#usage-table th:nth-child(1), #usage-table td:nth-child(1) { flex: 0 0 90px; }
#usage-table th:nth-child(2), #usage-table td:nth-child(2) { flex: 0 0 110px; }
#usage-table th:nth-child(3), #usage-table td:nth-child(3) { flex: 0 0 90px; }
#usage-table th:nth-child(4), #usage-table td:nth-child(4) { flex: 0 0 90px; }
#usage-table th:nth-child(5), #usage-table td:nth-child(5) { flex: 1 1 320px; min-width: 0; }
#usage-table th:nth-child(6), #usage-table td:nth-child(6) { flex: 0 0 90px; }
#usage-table th:nth-child(7), #usage-table td:nth-child(7) { flex: 0 0 100px; }
#usage-table th:nth-child(8), #usage-table td:nth-child(8) { flex: 0 0 90px; }
#usage-table th:nth-child(9), #usage-table td:nth-child(9) { flex: 0 0 90px; }
#usage-table th:nth-child(10), #usage-table td:nth-child(10) { flex: 0 0 90px; }
#usage-table th:nth-child(11), #usage-table td:nth-child(11) { flex: 0 0 130px; }
#usage-table th:nth-child(12), #usage-table td:nth-child(12) { flex: 0 0 100px; }
#usage-table th:nth-child(13), #usage-table td:nth-child(13) { flex: 0 0 140px; }
/* D-12: the command cell is a flex row of two children -- .command-text
   (clamped, grows) and an optional .step-marker (fixed, reserved space) --
   never a clamp on the <td> itself, so the marker can never be swallowed by
   the 2-line clamp. */
#usage-table td.command-cell {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: var(--space-xs);
  overflow: hidden;
}
.command-text {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  overflow-wrap: anywhere;
  flex: 1 1 auto;
  min-width: 0;
}
.step-marker {
  flex: 0 0 auto;
  min-width: var(--space-2xl);
  font-size: var(--md-sys-typescale-label-size);
  font-weight: var(--md-sys-typescale-label-weight);
  line-height: var(--md-sys-typescale-label-line-height);
  color: var(--md-sys-color-outline);
}
/* D-23: grouped mode's own 5-column header/row set (session, count,
   tokens_input, tokens_output, price) -- scoped to .row-grouped so it never
   shares column meaning/widths with flat mode's 11-column nth-child rules
   above. The extra class selector outranks the plain #usage-table rule. */
/* session_id is a 36-char UUID -- it is the column that needs the
   flexible/growing width, not the trailing numeric columns (which are
   always short and were previously given flex-grow, stretching an
   empty price column while session_id wrapped in a cramped fixed
   200px). */
#usage-table .row-grouped th:nth-child(1),
#usage-table .row-grouped td:nth-child(1) { flex: 1 1 260px; min-width: 0; white-space: nowrap; }
#usage-table .row-grouped th:nth-child(2),
#usage-table .row-grouped td:nth-child(2) { flex: 0 0 100px; }
#usage-table .row-grouped th:nth-child(3),
#usage-table .row-grouped td:nth-child(3) { flex: 0 0 130px; }
#usage-table .row-grouped th:nth-child(4),
#usage-table .row-grouped td:nth-child(4) { flex: 0 0 130px; }
#usage-table .row-grouped th:nth-child(5),
#usage-table .row-grouped td:nth-child(5) { flex: 0 0 100px; }
#usage-table td.command-cell {
  cursor: pointer;
}
/* D-14: full-command detail dialog. Fixed max-height on the dialog surface
   itself (both the host's own CSS box AND @material/web's own container
   custom property, so the constraint holds regardless of which layer ends
   up governing size) with the decomposer step list scrolling INTERNALLY --
   RESEARCH.md live-verified a real 55-step compound command, so an
   unbounded dialog is a real case, not a hypothetical. */
#command-dialog {
  --md-dialog-container-max-block-size: 70vh;
  max-height: 70vh;
}
.dialog-command-text {
  font-family: inherit;
  font-size: var(--md-sys-typescale-body-size);
  line-height: var(--md-sys-typescale-body-line-height);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  margin: 0 0 var(--space-md) 0;
}
.dialog-copy-status {
  min-height: var(--md-sys-typescale-label-line-height);
  font-size: var(--md-sys-typescale-label-size);
  color: var(--md-sys-color-primary);
  margin: 0 0 var(--space-md) 0;
}
.dialog-copy-status--error {
  color: var(--md-sys-color-error);
}
.dialog-steps {
  max-height: 240px;
  overflow-y: auto;
}
.dialog-step {
  font-size: var(--md-sys-typescale-body-size);
  line-height: var(--md-sys-typescale-body-line-height);
  padding: var(--space-xs) 0;
  border-bottom: 1px solid var(--md-sys-color-surface-variant);
  overflow-wrap: anywhere;
}
/* Empty / loading / error page states -- today's dashboard leaves the table
   silently blank in every one of these cases; this closes that gap. */
#loading-progress {
  margin-bottom: var(--space-md);
  width: 100%;
}
.state-panel {
  padding: var(--space-lg);
}
.state-heading {
  font-size: var(--md-sys-typescale-heading-size);
  font-weight: var(--md-sys-typescale-heading-weight);
  line-height: var(--md-sys-typescale-heading-line-height);
  margin: 0 0 var(--space-sm) 0;
}
.state-body {
  font-size: var(--md-sys-typescale-body-size);
  line-height: var(--md-sys-typescale-body-line-height);
  margin: 0;
}
.state-panel--error .state-heading,
.state-panel--error .state-body {
  color: var(--md-sys-color-error);
}
.result-count {
  font-size: var(--md-sys-typescale-label-size);
  font-weight: var(--md-sys-typescale-label-weight);
  line-height: var(--md-sys-typescale-label-line-height);
  color: var(--md-sys-color-outline);
  margin: var(--space-sm) 0;
}
</style>
</head>
<body>
<h1>Usage metrics</h1>
<md-linear-progress id="loading-progress" indeterminate></md-linear-progress>
<div id="page-error-state" class="state-panel state-panel--error" hidden>
<p class="state-body">Couldn't load usage data. Regenerate the dashboard with
<code>ai-kit-usage-metrics dashboard</code>.</p>
</div>
<div id="dashboard-top">
<div id="charts-row">
<div id="chart-runtime-panel" class="chart-panel">
<h2 class="chart-panel-title">Runtime distribution</h2>
<div class="chart-canvas-wrap"><canvas id="runtime-chart"></canvas></div>
<p id="runtime-chart-fallback" class="chart-fallback"></p>
</div>
<div id="chart-per-day-panel" class="chart-panel">
<h2 class="chart-panel-title">Tokens &amp; price per day</h2>
<div class="chart-canvas-wrap"><canvas id="per-day-chart"></canvas></div>
<p id="per-day-chart-fallback" class="chart-fallback"></p>
</div>
<div id="chart-family-panel" class="chart-panel">
<h2 class="chart-panel-title">Family / subfamily distribution</h2>
<div class="chart-canvas-wrap"><canvas id="family-chart"></canvas></div>
<p id="family-chart-fallback" class="chart-fallback"></p>
</div>
</div>
<form id="filters">
<label>runtime
<select id="filter-runtime"></select>
</label>
<label>model
<select id="filter-model"></select>
</label>
<label>family
<select id="filter-family"></select>
</label>
<label>subfamily
<select id="filter-subfamily"></select>
</label>
<label>command
<md-outlined-text-field id="filter-command" type="text"></md-outlined-text-field>
</label>
<label>date range
<span id="date-range-group">
<input id="filter-date-from" type="date" aria-label="from date">
<span class="date-range-sep">&ndash;</span>
<input id="filter-date-to" type="date" aria-label="to date">
</span>
<span id="date-presets" role="group" aria-label="date range presets">
<md-text-button type="button" data-preset="today">Today</md-text-button>
<md-text-button type="button" data-preset="week">Last 7 days</md-text-button>
<md-text-button type="button" data-preset="month">Last 30 days</md-text-button>
<md-text-button type="button" data-preset="current-month">This month</md-text-button>
<md-text-button type="button" data-preset="all">All time</md-text-button>
</span>
</label>
<label>tokens min
<md-outlined-text-field id="filter-tokens-min" type="number"></md-outlined-text-field>
</label>
<label>tokens max
<md-outlined-text-field id="filter-tokens-max" type="number"></md-outlined-text-field>
</label>
<label>price min
<md-outlined-text-field id="filter-price-min" type="number"></md-outlined-text-field>
</label>
<label>price max
<md-outlined-text-field id="filter-price-max" type="number"></md-outlined-text-field>
</label>
<label>group by session
<md-checkbox id="group-by-session"></md-checkbox>
</label>
<md-text-button id="clear-filters" type="button">Clear filters</md-text-button>
</form>
</div>
<p id="result-count" class="result-count" role="status"></p>
<div id="table-scroll" tabindex="-1">
<table id="usage-table">
<thead>
<tr id="thead-flat">
<th data-sort-key="runtime">runtime</th>
<th data-sort-key="model">model</th>
<th data-sort-key="family">family</th>
<th data-sort-key="subfamily">subfamily</th>
<th data-sort-key="command_text">command</th>
<th data-sort-key="exec_duration_ms">exec time</th>
<th data-sort-key="date">date</th>
<th data-sort-key="tokens_input">tokens_input</th>
<th data-sort-key="tokens_output">tokens_output</th>
<th data-sort-key="price">price</th>
<th data-sort-key="source_confidence">source_confidence</th>
<th data-sort-key="execution_certain">execution</th>
<th data-sort-key="session_id">session</th>
</tr>
<tr id="thead-grouped" class="row-grouped" style="display:none;">
<th data-sort-key="session_id">session</th>
<th data-sort-key="count">count</th>
<th data-sort-key="tokens_input">tokens_input</th>
<th data-sort-key="tokens_output">tokens_output</th>
<th data-sort-key="price">price</th>
</tr>
</thead>
<tbody id="usage-tbody"></tbody>
</table>
</div>
<div id="table-empty-state" class="state-panel" hidden>
<p class="state-heading">No commands match these filters</p>
<p class="state-body">Widen the date range or clear a filter to see more.</p>
</div>
<md-dialog id="command-dialog">
<div slot="headline">Command</div>
<div slot="content">
<pre id="dialog-command-text" class="dialog-command-text"></pre>
<p id="dialog-copy-status" class="dialog-copy-status" role="status"></p>
<div id="dialog-steps" class="dialog-steps"></div>
</div>
<div slot="actions">
<md-filled-button id="dialog-copy-button" aria-label="Copy command">Copy command</md-filled-button>
<md-icon-button id="dialog-close-button" aria-label="Close dialog">
<md-icon>close</md-icon>
</md-icon-button>
</div>
</md-dialog>
<script type="application/json" id="usage-metrics-data">"""

_HTML_MID = """</script>
<script>
/* PURE_FUNCTIONS_START */
function inDateRange(date, start, end) {
  if (!date) return false;
  var d = String(date);
  if (start && d < start) return false;
  if (end && d > end) return false;
  return true;
}

function numOrNull(v) {
  if (v === "" || v == null) return null;
  var n = Number(v);
  return isNaN(n) ? null : n;
}

function combinedTokens(row) {
  if (row.tokens_input == null && row.tokens_output == null) return null;
  var a = row.tokens_input == null ? 0 : Number(row.tokens_input);
  var b = row.tokens_output == null ? 0 : Number(row.tokens_output);
  return a + b;
}

function displayFamily(row) {
  var fam = row.family;
  if (fam != null && String(fam) !== "") return String(fam);
  if (row.inferred_family) {
    return String(row.inferred_family) + " (inferred, " +
      String(row.inferred_confidence) + ")";
  }
  return "";
}

// D-16: a null value is NOT the same as a real zero/blank -- both display
// helpers below return the em dash marker for null/missing and the real
// value otherwise, so 37,231 rows with no computed price stop reading as
// "price is always 0" and rows with a genuinely NULL date stop reading as
// a blank cell with no visual marker.
var EM_DASH = "\\u2014";
var PRICE_UNKNOWN_TOOLTIP = "unknown \\u2014 model not in catalog";
/* rtk rows carry price_confidence "not_applicable" (refiner.py never
   attempts a catalog lookup for them -- rtk is a shell-command wrapper
   measuring token savings, not a model call). Showing the catalog-miss
   tooltip on those rows falsely implies rtk should have a priceable
   model, so it gets its own distinct message. */
var PRICE_NOT_APPLICABLE_TOOLTIP =
  "not applicable \\u2014 rtk measures token savings, not model cost";

function priceCellText(price) {
  return price == null ? EM_DASH : String(price);
}

function dateCellText(date) {
  return date == null || date === "" ? EM_DASH : String(date);
}

// D-11 / SD-1: literal JavaScript port of family.py's subfamily_of() and its
// three supporting constants (_WRAPPERS, _ASSIGNMENT_RE, _VALUE_FLAGS) plus
// the plausibility filter regex. Kept inside the pure-function marker block
// so the suite's node-executed parity test (test_subfamily_js_matches_spec_table_and_python)
// picks it up automatically. Any change here must be mirrored in family.py,
// and vice versa -- SUBFAMILY_SPEC_CASES is the shared oracle for both.
var SUBFAMILY_WRAPPERS = ["sudo", "env", "time", "nice", "ionice", "export"];
var SUBFAMILY_ASSIGNMENT_RE = /^[A-Za-z_][A-Za-z0-9_]*=\\S*$/;
var SUBFAMILY_CANDIDATE_RE = /^[A-Za-z][A-Za-z0-9_.:-]*$/;
var SUBFAMILY_VALUE_FLAGS = {
  "git": ["-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env"],
  "make": ["-C", "--directory", "-f", "--file", "-j", "--jobs", "-o", "-W"],
  "docker": ["-H", "--host", "--context", "--config", "--log-level"],
  "kubectl": ["-n", "--namespace", "--context", "--cluster", "--user", "--kubeconfig"],
  "npm": ["--prefix", "-w", "--workspace", "--registry"],
  "cargo": ["--manifest-path", "--config", "-Z"],
  "go": ["-C"],
  "pip": ["-r", "--requirement", "--index-url", "--extra-index-url", "-t", "--target"],
  "pip3": ["-r", "--requirement", "--index-url", "--extra-index-url", "-t", "--target"],
  "systemctl": ["-H", "--host", "-M", "--machine"],
  "apt": ["-o", "-c", "-t"],
  "apt-get": ["-o", "-c", "-t"],
  "tar": ["-f", "--file", "-C", "--directory"],
  "rsync": ["-e", "--exclude-from", "--files-from"]
};

function subfamilyOf(commandText) {
  var tokens = (commandText || "").split(/\\s+/).filter(function (t) { return t.length > 0; });
  var i = 0;
  while (i < tokens.length) {
    var tok = tokens[i];
    if (SUBFAMILY_ASSIGNMENT_RE.test(tok)) {
      i += 1;
      continue;
    }
    if (SUBFAMILY_WRAPPERS.indexOf(tok) !== -1) {
      i += 1;
      while (i < tokens.length && tokens[i].indexOf("-") === 0) {
        i += 1;
      }
      continue;
    }
    break;
  }
  if (i >= tokens.length) return "";
  var familyTokenParts = tokens[i].split("/");
  var familyToken = familyTokenParts[familyTokenParts.length - 1];
  var valueFlags = SUBFAMILY_VALUE_FLAGS[familyToken] || [];
  i += 1;
  while (i < tokens.length && tokens[i].indexOf("-") === 0) {
    if (tokens[i] === "--") {
      i += 1;
      break;
    }
    var flag = tokens[i];
    i += 1;
    if (flag.indexOf("=") === -1 && valueFlags.indexOf(flag) !== -1 && i < tokens.length) {
      i += 1;
    }
  }
  if (i >= tokens.length) return "";
  var candidate = tokens[i];
  if (!SUBFAMILY_CANDIDATE_RE.test(candidate)) return "";
  return candidate;
}

function decorateSubfamily(rows) {
  // Called exactly once, immediately after the embedded payload is parsed
  // and before any filter/sort/render runs -- deriving subfamily per filter
  // event across the full ~84k-row payload is precisely the per-event cost
  // D-02 exists to remove. Gated on command_shape === "simple" (mirroring
  // Plan 02's Python-side family gate) so opaque control_flow_script/
  // unclassified blobs never populate the subfamily axis with garbage.
  rows.forEach(function (row) {
    row.subfamily = row.command_shape === "simple" ? subfamilyOf(row.command_text) : "";
  });
  return rows;
}

function filterRows(rows, criteria) {
  criteria = criteria || {};
  var runtime = criteria.runtime;
  var family = criteria.family;
  var model = criteria.model;
  var subfamily = criteria.subfamily;
  var cmd = criteria.commandText ? String(criteria.commandText).toLowerCase() : "";
  var dateFrom = criteria.dateFrom;
  var dateTo = criteria.dateTo;
  var tmin = numOrNull(criteria.tokensMin);
  var tmax = numOrNull(criteria.tokensMax);
  var pmin = numOrNull(criteria.priceMin);
  var pmax = numOrNull(criteria.priceMax);
  return rows.filter(function (row) {
    if (runtime && runtime !== "all" && row.runtime !== runtime) return false;
    if (family && family !== "all" && row.family !== family) return false;
    if (model && model !== "all" && row.model !== model) return false;
    if (subfamily && subfamily !== "all" && row.subfamily !== subfamily) return false;
    if (cmd) {
      var hay = row.command_text == null ? "" : String(row.command_text);
      if (hay.toLowerCase().indexOf(cmd) === -1) return false;
    }
    // D-13: a single from/to range replaces the 4 removed preset branches.
    // An empty string on either end is an open bound (inDateRange's own
    // falsy check); when BOTH ends are empty this block is skipped
    // entirely, so a null-date row is only excluded once a bound is set.
    if (dateFrom || dateTo) {
      if (!inDateRange(row.date, dateFrom, dateTo)) return false;
    }
    if (tmin != null || tmax != null) {
      var tok = combinedTokens(row);
      if (tok == null) return false;
      if (tmin != null && tok < tmin) return false;
      if (tmax != null && tok > tmax) return false;
    }
    if (pmin != null || pmax != null) {
      if (row.price == null) return false;
      var price = Number(row.price);
      if (pmin != null && price < pmin) return false;
      if (pmax != null && price > pmax) return false;
    }
    return true;
  });
}

function sortRows(rows, key, direction) {
  var dir = direction === "desc" ? -1 : 1;
  return rows.slice().sort(function (a, b) {
    var av = a[key];
    var bv = b[key];
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    if (av < bv) return -1 * dir;
    if (av > bv) return 1 * dir;
    return 0;
  });
}

// SD-4: the single shared turn-level dedup identity (Plan 05's per-day chart
// aggregation reuses this function rather than defining a second one). Token
// and price figures are turn-level values duplicated onto every step-row
// sharing a (session_id, turn_id) -- when a turn id exists, that pair IS the
// identity. codex/rtk rows with no turn concept at all fall back to
// (session_id, raw_ref): every step of one decomposed command shares one
// raw_ref, so the fallback collapses the siblings' duplicated figures to one
// contribution WITHOUT collapsing two genuinely different null-turn commands
// in the same session (their raw_ref differs). step_index is deliberately
// NEVER part of either branch -- including it would treat each sibling step
// as a unique turn and inflate the sum by the step count, the exact
// over-count the Round-1 cross-AI review identified in the previous plan.
// The "t:"/"r:" markers keep the two key namespaces from ever colliding.
function turnKey(row) {
  var sid = String(row.session_id);
  if (row.turn_id != null) {
    return sid + "\\0t:" + String(row.turn_id);
  }
  return sid + "\\0r:" + String(row.raw_ref);
}

function groupBySession(rows) {
  var counts = {};
  var order = [];
  rows.forEach(function (row) {
    var sid = row.session_id;
    if (!Object.prototype.hasOwnProperty.call(counts, sid)) {
      counts[sid] = 0;
      order.push(sid);
    }
    counts[sid] += 1;
  });
  var seen = {};
  var sums = {};
  rows.forEach(function (row) {
    var sid = row.session_id;
    var key = turnKey(row);
    if (seen[key]) return;
    seen[key] = true;
    if (!sums[sid]) {
      sums[sid] = {tokens_input: null, tokens_output: null, price: null};
    }
    var acc = sums[sid];
    if (row.tokens_input != null) {
      acc.tokens_input = (acc.tokens_input || 0) + Number(row.tokens_input);
    }
    if (row.tokens_output != null) {
      acc.tokens_output = (acc.tokens_output || 0) + Number(row.tokens_output);
    }
    if (row.price != null) {
      acc.price = (acc.price || 0) + Number(row.price);
    }
  });
  return order.map(function (sid) {
    var acc = sums[sid] || {};
    return {
      session_id: sid,
      count: counts[sid],
      tokens_input: acc.tokens_input == null ? null : acc.tokens_input,
      tokens_output: acc.tokens_output == null ? null : acc.tokens_output,
      price: acc.price == null ? null : acc.price
    };
  });
}

function sliceForItems(rows, items) {
  // Pure mapping from the virtualizer's virtual-item window to
  // {index, start, row} triples. This IS the production materialization
  // path -- the one painter below iterates this function's output and
  // nothing else, so materialization is bounded by items.length (the
  // virtual window), never by rows.length (the full dataset).
  return items.map(function (item) {
    return {index: item.index, start: item.start, row: rows[item.index]};
  });
}

function runtimeCounts(rows) {
  var counts = {};
  var order = [];
  rows.forEach(function (row) {
    var rt = row.runtime;
    if (rt == null || rt === "") return;
    if (!Object.prototype.hasOwnProperty.call(counts, rt)) {
      counts[rt] = 0;
      order.push(rt);
    }
    counts[rt] += 1;
  });
  return {
    labels: order,
    counts: order.map(function (rt) { return counts[rt]; })
  };
}

// SD-9: the DOM-free companion to clearFilters() (defined outside the
// marker block, since it touches document) -- the criteria object a fully
// cleared filter bar produces. filterRows(rows, clearedCriteria()) returning
// every row is the node-testable proof that "cleared" really means
// unfiltered.
// SD-10 / empty state: a pure, DOM-free predicate so the node harness can
// drive it directly -- true for a zero-length filtered/grouped row set
// (flat OR grouped mode; a grouped session count of zero reuses the same
// empty state per UI-SPEC.md's zero-one-many resolution), false otherwise.
function shouldShowEmptyState(rows) {
  return !rows || rows.length === 0;
}

function clearedCriteria() {
  return {
    runtime: "all",
    model: "all",
    family: "all",
    subfamily: "all",
    commandText: "",
    dateFrom: "",
    dateTo: "",
    tokensMin: "",
    tokensMax: "",
    priceMin: "",
    priceMax: ""
  };
}
// D-14 / SD-3: a single refined row does NOT carry the full decomposer
// breakdown -- only its own step's fields. The sibling steps of one
// decomposed command are separate rows sharing one raw_ref (refined_store.py's
// UNIQUE(raw_ref, step_index) constraint guarantees the pair is unique per
// row). indexByRawRef(rows) is the real lookup mechanism: built ONCE at load
// over the FULL embedded payload (never the filtered set), it returns a Map
// from raw_ref to that record's rows sorted ascending by step_index.
function indexByRawRef(rows) {
  var map = new Map();
  rows.forEach(function (row) {
    var key = row.raw_ref;
    if (key == null) return;
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(row);
  });
  map.forEach(function (bucket) {
    bucket.sort(function (a, b) {
      return Number(a.step_index) - Number(b.step_index);
    });
  });
  return map;
}

// stepEntries: pure render-data helper for the detail dialog's decomposer
// section. A row whose step_count is 1 (or absent) has no siblings to show,
// so it returns an empty array and the dialog omits the entire step section
// -- the dialog body directly above already shows that single command in
// full, so a single-command empty state would only restate it (this is the
// concrete choice UI-SPEC.md required the planner to record, not silently
// default).
function stepEntries(rowsByRawRef, row) {
  var stepCount = row.step_count == null ? null : Number(row.step_count);
  if (stepCount == null || stepCount <= 1) return [];
  var bucket = rowsByRawRef.get(row.raw_ref);
  if (!bucket) return [];
  return bucket.map(function (sibling) {
    return {
      position: Number(sibling.step_index) + 1,
      total: Number(sibling.step_count),
      operator: sibling.operator == null ? "" : String(sibling.operator),
      text: sibling.command_text == null ? "" : String(sibling.command_text)
    };
  });
}

// D-18 item 2 / SD-7: family/subfamily distribution bar cap -- a real
// module-level constant (not a phrase) inside the marker block so the
// node-executed test harness sees it too.
var CHART_FAMILY_LIMIT = 15;

// D-18 item 1 / SD-5: per-day token totals broken down by runtime, plus one
// overall price total -- both deduplicated on the shared turnKey identity
// BEFORE summing, per refined_store.py's module docstring. Summing first and
// deduplicating afterwards is the exact regression this function exists to
// prevent: it would inflate every date's totals by the step count of every
// compound command sharing that date. A null tokens/price/date value is
// skipped rather than coerced to zero; a genuine zero price is still summed.
function aggregateTokensAndPriceByDay(rows) {
  var dateOrder = [];
  var seenKeysByDate = {};
  var priceByDate = {};
  var runtimeSeen = {};
  var runtimeOrder = [];
  var tokensByDateRuntime = {};
  rows.forEach(function (row) {
    var date = row.date;
    if (date == null || date === "") return;
    if (!Object.prototype.hasOwnProperty.call(tokensByDateRuntime, date)) {
      tokensByDateRuntime[date] = {};
      priceByDate[date] = null;
      dateOrder.push(date);
    }
    var key = turnKey(row);
    if (!seenKeysByDate[date]) seenKeysByDate[date] = {};
    if (seenKeysByDate[date][key]) return;
    seenKeysByDate[date][key] = true;
    var runtime = row.runtime;
    if (runtime != null && runtime !== "") {
      if (!Object.prototype.hasOwnProperty.call(runtimeSeen, runtime)) {
        runtimeSeen[runtime] = true;
        runtimeOrder.push(runtime);
      }
      var tokens = null;
      if (row.tokens_input != null) {
        tokens = (tokens == null ? 0 : tokens) + Number(row.tokens_input);
      }
      if (row.tokens_output != null) {
        tokens = (tokens == null ? 0 : tokens) + Number(row.tokens_output);
      }
      if (tokens != null) {
        var byRuntime = tokensByDateRuntime[date];
        byRuntime[runtime] = (byRuntime[runtime] == null ? 0 : byRuntime[runtime]) + tokens;
      }
    }
    if (row.price != null) {
      priceByDate[date] = (priceByDate[date] == null ? 0 : priceByDate[date]) + Number(row.price);
    }
  });
  dateOrder.sort();
  runtimeOrder.sort();
  return {
    dates: dateOrder,
    runtimes: runtimeOrder,
    tokensByRuntime: runtimeOrder.map(function (rt) {
      return dateOrder.map(function (d) {
        var v = tokensByDateRuntime[d][rt];
        return v == null ? 0 : v;
      });
    }),
    price: dateOrder.map(function (d) { return priceByDate[d]; })
  };
}

// D-18 item 2 / SD-7: family/subfamily distribution, ranked by row count.
// This chart counts ROWS, not tokens or price -- every decomposed step is a
// genuinely separate command invocation -- so it deliberately does NOT
// deduplicate on turnKey. Do not "fix" that in later.
function aggregateFamilyDistribution(rows) {
  var counts = {};
  var order = [];
  rows.forEach(function (row) {
    if (row.family == null || row.family === "") return;
    var label = row.subfamily ? row.family + " " + row.subfamily : row.family;
    if (!Object.prototype.hasOwnProperty.call(counts, label)) {
      counts[label] = 0;
      order.push(label);
    }
    counts[label] += 1;
  });
  // Count descending; ties broken by the label string ascending using a
  // plain "<" comparison (never localeCompare), so node and the browser
  // agree on the same order.
  order.sort(function (a, b) {
    if (counts[a] !== counts[b]) return counts[b] - counts[a];
    if (a < b) return -1;
    if (a > b) return 1;
    return 0;
  });
  var top = order.slice(0, CHART_FAMILY_LIMIT);
  var rest = order.slice(CHART_FAMILY_LIMIT);
  var labels = top.slice();
  var values = top.map(function (label) { return counts[label]; });
  if (rest.length > 0) {
    var remainderSum = rest.reduce(function (sum, label) { return sum + counts[label]; }, 0);
    labels.push("other (" + rest.length + " more)");
    values.push(remainderSum);
  }
  return {labels: labels, counts: values};
}

// SD-6: DOM-free debounce factory so the #filters `input` listener (text and
// number fields) does not run a full-dataset filter+chart recompute on every
// keystroke. `change` events (selects, date inputs, the checkbox) stay
// immediate -- only `input` is debounced, at a fixed 150ms delay.
function debounce(fn, delay) {
  var timer = null;
  return function () {
    var args = arguments;
    var context = this;
    if (timer) clearTimeout(timer);
    timer = setTimeout(function () {
      fn.apply(context, args);
    }, delay);
  };
}
/* PURE_FUNCTIONS_END */

var CHART_PALETTE_LIGHT = ["#6750A4", "#7D5260", "#625B71", "#79747E", "#1C1B1F"];
var CHART_PALETTE_DARK = ["#D0BCFF", "#EFB8C8", "#CCC2DC", "#938F99", "#E6E1E5"];

function chartJsAvailable() {
  return typeof Chart !== "undefined";
}

(function () {
  var dataEl = document.getElementById("usage-metrics-data");
  var tbody = document.getElementById("usage-tbody");
  var scrollEl = document.getElementById("table-scroll");
  var theadFlat = document.getElementById("thead-flat");
  var theadGrouped = document.getElementById("thead-grouped");
  var filtersForm = document.getElementById("filters");
  var chartsRow = document.getElementById("charts-row");
  var loadingBar = document.getElementById("loading-progress");
  var pageErrorState = document.getElementById("page-error-state");
  var tableEmptyState = document.getElementById("table-empty-state");
  var resultCount = document.getElementById("result-count");
  var sortKey = "date";
  var sortDir = "asc";
  var virtualizer = null;
  // WR-02 (re-review): tracks the 5s virtualizer-load fallback timer (see
  // initialize() below) so a mount that succeeds -- whether before or after
  // the timer fires -- can neutralize it / reverse its effects.
  var virtualizerFallbackTimer = null;
  var currentRows = [];
  var currentBuilder = flatRowBuilder;
  var runtimeChart = null;
  var perDayChart = null;
  var familyChart = null;
  // The filtered (but not yet sorted/grouped) row set from the most recent
  // applyFilters() call -- applySort() re-sorts THIS set rather than
  // re-running filterRows(), matching SD-6's "re-sorts the already-filtered
  // row set" wording exactly.
  var currentFiltered = [];
  // D-14: the element that opened the dialog, restored on close (see the
  // "closed"-event listener registered once at mount, below).
  var dialogTrigger = null;
  var dialogCommandText = "";
  // Populated by initialize() below, after a successful payload parse --
  // NOT synchronously here, so a malformed payload never reaches
  // decorateSubfamily/indexByRawRef with garbage.
  var data = [];
  var rowsByRawRef = new Map();

  function setFilterControlsDisabled(disabled) {
    // UI-SPEC.md's explicit loading sub-decision: filter controls stay
    // disabled for exactly the interval the progress bar is shown, so a
    // filter event can never fire against a virtualizer that has not
    // mounted yet.
    var controls = filtersForm.querySelectorAll(
      "select, md-outlined-text-field, input, md-checkbox, md-text-button"
    );
    controls.forEach(function (el) {
      el.disabled = disabled;
    });
  }

  function showPageError() {
    // UI-SPEC.md: ONE page-level error state, not three independent
    // per-surface error UIs -- the filter bar and charts row are hidden
    // behind the same state the table area shows.
    if (pageErrorState) pageErrorState.hidden = false;
    if (filtersForm) filtersForm.style.display = "none";
    if (chartsRow) chartsRow.style.display = "none";
    if (scrollEl) scrollEl.style.display = "none";
    if (loadingBar) loadingBar.remove();
  }

  // WR-02 (re-review): reverses showPageError()'s effects. The 5s virtualizer
  // fallback timer (initialize(), below) can legitimately fire BEFORE a
  // merely-slow (not actually failed) "virtual-core-ready" event arrives --
  // clearing the timer alone only prevents a redundant future fire, it does
  // not undo an error already shown. mountVirtualizer() calls this
  // unconditionally on every successful mount so a late-but-successful mount
  // is a true no-op when the timer never fired, and a full recovery
  // (re-show filtersForm/chartsRow/scrollEl, hide pageErrorState) when it did.
  function hidePageError() {
    if (!pageErrorState || pageErrorState.hidden) return;
    pageErrorState.hidden = true;
    if (filtersForm) filtersForm.style.display = "";
    if (chartsRow) chartsRow.style.display = "";
    if (scrollEl) scrollEl.style.display = "";
  }

  // The embedded-payload parse is wrapped: a malformed/truncated payload
  // fails into the page-level error state instead of leaving the rest of
  // this script to run against undefined data.
  try {
    data = JSON.parse(dataEl.textContent);
  } catch (parseError) {
    showPageError();
    return;
  }

  function distinctValues(key) {
    var seen = {};
    var out = [];
    data.forEach(function (row) {
      var v = row[key];
      if (v == null || v === "") return;
      var s = String(v);
      if (!seen[s]) {
        seen[s] = true;
        out.push(s);
      }
    });
    out.sort();
    return out;
  }

  function fillSelect(id, values) {
    // A native <select> (see the import-block comment for why) -- clear
    // first so repeat calls stay idempotent; the all-value option is
    // always created first, one option per distinct value follows, then
    // the select's own value is set to "all".
    var select = document.getElementById(id);
    select.textContent = "";
    function addOption(value) {
      var opt = document.createElement("option");
      opt.value = value;
      opt.textContent = value;
      select.appendChild(opt);
    }
    addOption("all");
    values.forEach(addOption);
    select.value = "all";
  }

  function readCriteria() {
    return {
      runtime: document.getElementById("filter-runtime").value,
      model: document.getElementById("filter-model").value,
      family: document.getElementById("filter-family").value,
      subfamily: document.getElementById("filter-subfamily").value,
      commandText: document.getElementById("filter-command").value,
      dateFrom: document.getElementById("filter-date-from").value,
      dateTo: document.getElementById("filter-date-to").value,
      tokensMin: document.getElementById("filter-tokens-min").value,
      tokensMax: document.getElementById("filter-tokens-max").value,
      priceMin: document.getElementById("filter-price-min").value,
      priceMax: document.getElementById("filter-price-max").value
    };
  }

  function clearFilters() {
    // SD-9: reset every filter-* control, then applyFilters() exactly once
    // at the end. The session-grouping checkbox is deliberately left alone
    // -- it is a view mode, not a filter.
    ["filter-runtime", "filter-model", "filter-family", "filter-subfamily"].forEach(
      function (id) {
        document.getElementById(id).value = "all";
      }
    );
    [
      "filter-command",
      "filter-tokens-min",
      "filter-tokens-max",
      "filter-price-min",
      "filter-price-max"
    ].forEach(function (id) {
      document.getElementById(id).value = "";
    });
    ["filter-date-from", "filter-date-to"].forEach(function (id) {
      document.getElementById(id).value = "";
    });
    markActiveDatePreset("all");
    applyFilters();
  }

  function markActiveDatePreset(name) {
    document.querySelectorAll("#date-presets md-text-button").forEach(function (btn) {
      if (btn.getAttribute("data-preset") === name) btn.setAttribute("data-active", "");
      else btn.removeAttribute("data-active");
    });
  }

  function isoDate(dt) {
    var mm = String(dt.getMonth() + 1);
    if (mm.length < 2) mm = "0" + mm;
    var dd = String(dt.getDate());
    if (dd.length < 2) dd = "0" + dd;
    return dt.getFullYear() + "-" + mm + "-" + dd;
  }

  // Quick-select date-range presets (airline/hotel-booking pattern: a
  // single bordered from/to control per D-13, plus quick-select chips
  // rather than requiring every range to be hand-picked). "today"/"week"
  // (last 7 days)/"month" (last 30 days) are ROLLING windows anchored on
  // the moment the page is opened -- the same "computed in the browser
  // from new Date() when opened" pattern SKILL.md already documents for
  // the current-month case, so the same generated HTML answers
  // differently depending on when it is opened, by design. "current-month"
  // is the CALENDAR month to date (1st of this month through today),
  // distinct from the rolling 30-day "month" preset. "all" clears the
  // range entirely.
  function applyDatePreset(name) {
    var today = new Date();
    var from = "", to = "";
    if (name === "today") {
      from = isoDate(today);
      to = from;
    } else if (name === "week") {
      from = isoDate(new Date(today.getFullYear(), today.getMonth(), today.getDate() - 6));
      to = isoDate(today);
    } else if (name === "month") {
      from = isoDate(new Date(today.getFullYear(), today.getMonth(), today.getDate() - 29));
      to = isoDate(today);
    } else if (name === "current-month") {
      from = isoDate(new Date(today.getFullYear(), today.getMonth(), 1));
      to = isoDate(today);
    }
    document.getElementById("filter-date-from").value = from;
    document.getElementById("filter-date-to").value = to;
    markActiveDatePreset(name);
    applyFilters();
  }
  document.querySelectorAll("#date-presets md-text-button").forEach(function (btn) {
    btn.addEventListener("click", function () {
      applyDatePreset(btn.getAttribute("data-preset"));
    });
  });
  // A manual edit of either date input no longer matches any preset's
  // computed range -- drop the active highlight rather than leave a
  // preset looking selected when it no longer describes the filter.
  ["filter-date-from", "filter-date-to"].forEach(function (id) {
    document.getElementById(id).addEventListener("input", function () {
      markActiveDatePreset(null);
    });
  });

  function td(text) {
    var cell = document.createElement("td");
    cell.textContent = text == null ? "" : String(text);
    return cell;
  }

  function isConditional(row) {
    return row.execution_certain === false || row.execution_certain === 0;
  }

  function commandCell(row) {
    // D-12: a flex row of two children -- .command-text (clamped, grows)
    // and an optional .step-marker (fixed, reserved space) -- never a clamp
    // on the <td> itself, so a long two-line command can never push the
    // compound-step marker out of view.
    // D-14: focusable (tabindex 0) so the full-command dialog is reachable
    // without a mouse -- activation is wired via the delegated tbody
    // listeners below, not a per-cell listener here.
    var cell = document.createElement("td");
    cell.className = "command-cell";
    cell.setAttribute("tabindex", "0");
    var text = document.createElement("span");
    text.className = "command-text";
    text.textContent = row.command_text == null ? "" : String(row.command_text);
    cell.appendChild(text);
    var stepCount = row.step_count == null ? null : Number(row.step_count);
    if (stepCount != null && stepCount > 1) {
      var marker = document.createElement("span");
      marker.className = "step-marker";
      var stepPosition = row.step_index == null ? "" : String(Number(row.step_index) + 1);
      marker.textContent = stepPosition + "/" + String(stepCount);
      cell.appendChild(marker);
    }
    return cell;
  }

  function priceTd(row) {
    var cell = document.createElement("td");
    cell.textContent = priceCellText(row.price);
    if (row.price == null) {
      cell.title = row.price_confidence === "not_applicable"
        ? PRICE_NOT_APPLICABLE_TOOLTIP
        : PRICE_UNKNOWN_TOOLTIP;
    }
    return cell;
  }

  function dateTd(row) {
    var cell = document.createElement("td");
    cell.textContent = dateCellText(row.date);
    return cell;
  }

  function flatRowBuilder(row) {
    var tr = document.createElement("tr");
    tr.appendChild(td(row.runtime));
    tr.appendChild(td(row.model));
    tr.appendChild(td(displayFamily(row)));
    tr.appendChild(td(row.subfamily));
    tr.appendChild(commandCell(row));
    tr.appendChild(td(row.exec_duration_ms));
    tr.appendChild(dateTd(row));
    tr.appendChild(td(row.tokens_input));
    tr.appendChild(td(row.tokens_output));
    tr.appendChild(priceTd(row));
    var conf = document.createElement("td");
    if (row.source_confidence === "low") {
      conf.textContent = String(row.source_confidence);
      conf.className = "badge";
    } else if (row.source_confidence) {
      conf.textContent = String(row.source_confidence);
    }
    tr.appendChild(conf);
    var exec = document.createElement("td");
    if (isConditional(row)) {
      exec.textContent = "conditional";
      exec.className = "badge";
    }
    tr.appendChild(exec);
    tr.appendChild(td(row.session_id));
    return tr;
  }

  function groupedRowBuilder(row) {
    var tr = document.createElement("tr");
    // D-23: grouped mode's own class, matched by the .row-grouped CSS scope
    // so these 5 cells never inherit flat mode's 11-column nth-child widths.
    tr.className = "row-grouped";
    tr.appendChild(td(row.session_id));
    tr.appendChild(td(row.count));
    tr.appendChild(td(row.tokens_input));
    tr.appendChild(td(row.tokens_output));
    tr.appendChild(td(row.price));
    return tr;
  }

  // D-14: full-command detail dialog. Wired once at mount (this whole
  // block runs exactly once, since the enclosing IIFE runs exactly once per
  // page load) -- never per dialog-open, which would accumulate listeners.
  var CLIPBOARD_SUCCESS_MESSAGE = "Command copied to clipboard.";
  var CLIPBOARD_FAILURE_MESSAGE =
    "Couldn't copy the command \\u2014 clipboard access is unavailable.";
  var dialogEl = document.getElementById("command-dialog");
  var dialogCommandTextEl = document.getElementById("dialog-command-text");
  var dialogCopyStatusEl = document.getElementById("dialog-copy-status");
  var dialogStepsEl = document.getElementById("dialog-steps");
  var dialogCopyButton = document.getElementById("dialog-copy-button");
  var dialogCloseButton = document.getElementById("dialog-close-button");

  function renderDialogSteps(row) {
    dialogStepsEl.textContent = "";
    var entries = stepEntries(rowsByRawRef, row);
    entries.forEach(function (entry) {
      var stepEl = document.createElement("div");
      stepEl.className = "dialog-step";
      var opSuffix = entry.operator ? " (" + entry.operator + ")" : "";
      stepEl.textContent =
        "Step " + entry.position + " of " + entry.total + opSuffix + ": " + entry.text;
      dialogStepsEl.appendChild(stepEl);
    });
    // Zero-one-many (UI-SPEC.md): a single-step row shows no step section
    // at all -- the dialog body above already shows that one command in
    // full, so an empty-state restating it would add nothing.
    dialogStepsEl.style.display = entries.length > 0 ? "" : "none";
  }

  function openDialogForRow(row, trigger) {
    dialogCommandText = row.command_text == null ? "" : String(row.command_text);
    dialogCommandTextEl.textContent = dialogCommandText;
    dialogCopyStatusEl.textContent = "";
    dialogCopyStatusEl.classList.remove("dialog-copy-status--error");
    renderDialogSteps(row);
    dialogTrigger = trigger;
    dialogEl.show();
  }

  function resolveRowFromCell(cell) {
    var tr = cell.closest("tr");
    if (!tr) return null;
    var idx = Number(tr.getAttribute("data-row-index"));
    if (isNaN(idx)) return null;
    return currentRows[idx];
  }

  function activateCommandCell(event) {
    // Resolve the activated element as the closest [tabindex] ancestor so a
    // pointer activation on the inner .command-text span still records the
    // focusable command cell itself, not the span.
    var cell = event.target.closest("[tabindex]");
    if (!cell || !cell.classList.contains("command-cell")) return;
    var row = resolveRowFromCell(cell);
    if (!row) return;
    openDialogForRow(row, cell);
  }

  tbody.addEventListener("click", activateCommandCell);
  tbody.addEventListener("keydown", function (event) {
    if (event.key !== "Enter" && event.key !== " ") return;
    // preventDefault on the space case so the scrollport does not page down
    // behind the now-open dialog.
    if (event.key === " ") event.preventDefault();
    activateCommandCell(event);
  });

  // "closed" (NOT "close") -- in the pinned @material/web@2.5.0 md-dialog,
  // "close" is cancelable and fires BEFORE the close animation runs, so an
  // element referenced inside a "close" handler can still be mid-transition.
  // "closed" fires once the dialog has actually finished closing, which is
  // the point at which restoring focus is safe.
  dialogEl.addEventListener("closed", function () {
    if (dialogTrigger && dialogTrigger.isConnected) {
      dialogTrigger.focus();
    } else {
      // The virtualizer can have recycled the triggering row out of the DOM
      // while the dialog was open -- fall back to the scroll container
      // (tabindex="-1" so it can receive programmatic focus) rather than
      // silently dropping keyboard focus onto <body>.
      scrollEl.focus();
    }
    dialogTrigger = null;
  });

  dialogCloseButton.addEventListener("click", function () {
    dialogEl.close();
  });

  dialogCopyButton.addEventListener("click", function () {
    function showFailure() {
      dialogCopyStatusEl.textContent = CLIPBOARD_FAILURE_MESSAGE;
      dialogCopyStatusEl.classList.add("dialog-copy-status--error");
    }
    function showSuccess() {
      dialogCopyStatusEl.textContent = CLIPBOARD_SUCCESS_MESSAGE;
      dialogCopyStatusEl.classList.remove("dialog-copy-status--error");
    }
    // Both clipboard-refusal shapes route to the same visible message: an
    // insecure context (e.g. a file:// page) may not expose
    // navigator.clipboard at all -- reading .writeText off it would throw
    // before any promise exists, so that shape is guarded explicitly here --
    // and a secure-context browser may still reject the write, handled by
    // the .catch below.
    if (!navigator.clipboard || typeof navigator.clipboard.writeText !== "function") {
      showFailure();
      return;
    }
    navigator.clipboard.writeText(dialogCommandText).then(showSuccess).catch(showFailure);
  });

  function virtualizerOptions(count) {
    var vc = window.__virtualCore;
    return {
      count: count,
      getScrollElement: function () { return scrollEl; },
      estimateSize: function () { return 56; },
      observeElementRect: vc.observeElementRect,
      observeElementOffset: vc.observeElementOffset,
      scrollToFn: vc.elementScroll,
      overscan: 8,
      onChange: paint
    };
  }

  function paint() {
    // The ONE function in this file that writes rows to <tbody>. Both flat
    // and grouped modes route through it -- buildCurrentRowsFromFiltered()
    // only ever changes which row array (currentRows) and which
    // cell-builder (currentBuilder) it reads, never adds a second append
    // loop.
    if (!virtualizer) return;
    tbody.style.height = virtualizer.getTotalSize() + "px";
    tbody.textContent = "";
    var items = sliceForItems(currentRows, virtualizer.getVirtualItems());
    items.forEach(function (entry) {
      var tr = currentBuilder(entry.row);
      tr.style.transform = "translateY(" + entry.start + "px)";
      // D-14: the painter is the ONLY place that knows a materialized <tr>'s
      // position in currentRows -- the delegated dialog-activation listener
      // below resolves the activated row through this attribute rather than
      // binding a listener per rendered row (rows are recycled by the
      // virtualizer as the user scrolls).
      tr.setAttribute("data-row-index", String(entry.index));
      tbody.appendChild(tr);
    });
  }

  function mountVirtualizer() {
    var vc = window.__virtualCore;
    if (!vc || virtualizer) return;
    // WR-02: neutralize the fallback timer on every successful mount --
    // whether it is still pending (clearing it prevents a redundant future
    // fire) or has already fired (hidePageError() below reverses it).
    if (virtualizerFallbackTimer) {
      clearTimeout(virtualizerFallbackTimer);
      virtualizerFallbackTimer = null;
    }
    virtualizer = new vc.Virtualizer(virtualizerOptions(currentRows.length));
    virtualizer._didMount();
    virtualizer._willUpdate();
    hidePageError();
    paint();
  }

  function buildRuntimeChart(rows) {
    var canvas = document.getElementById("runtime-chart");
    var fallback = document.getElementById("runtime-chart-fallback");
    if (!chartJsAvailable()) {
      if (canvas) canvas.style.display = "none";
      if (fallback) {
        fallback.textContent = "Chart unavailable \\u2014 chart.js failed to load";
        fallback.style.display = "block";
      }
      return;
    }
    if (canvas) canvas.style.display = "";
    if (fallback) fallback.style.display = "none";
    var agg = runtimeCounts(rows);
    var dark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    var palette = dark ? CHART_PALETTE_DARK : CHART_PALETTE_LIGHT;
    var colors = agg.labels.map(function (_, i) { return palette[i % 5]; });
    if (runtimeChart) {
      runtimeChart.data.labels = agg.labels;
      runtimeChart.data.datasets[0].data = agg.counts;
      runtimeChart.data.datasets[0].backgroundColor = colors;
      runtimeChart.update();
      return;
    }
    runtimeChart = new Chart(canvas, {
      type: "doughnut",
      data: {
        labels: agg.labels,
        datasets: [{data: agg.counts, backgroundColor: colors}]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false
      }
    });
  }

  // D-18 item 1 / SD-5: Chart.js mixed chart -- one stacked bar dataset per
  // runtime on the left "y" axis (deduplicated token totals) plus one line
  // dataset on the right "y1" axis (deduplicated daily price total, Accent
  // colour). Both required measures are rendered, never one tooltip-only.
  function buildPerDayChart(rows) {
    var canvas = document.getElementById("per-day-chart");
    var fallback = document.getElementById("per-day-chart-fallback");
    if (!chartJsAvailable()) {
      if (canvas) canvas.style.display = "none";
      if (fallback) {
        fallback.textContent = "Chart unavailable \\u2014 chart.js failed to load";
        fallback.style.display = "block";
      }
      return;
    }
    var agg = aggregateTokensAndPriceByDay(rows);
    var noData = agg.dates.length === 0;
    if (canvas) canvas.style.display = noData ? "none" : "";
    if (fallback) {
      fallback.textContent = noData ? "No data for this range" : "";
      fallback.style.display = noData ? "block" : "none";
    }
    if (noData) return;
    var dark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    var palette = dark ? CHART_PALETTE_DARK : CHART_PALETTE_LIGHT;
    var barDatasets = agg.runtimes.map(function (rt, i) {
      return {
        type: "bar",
        label: rt,
        data: agg.tokensByRuntime[i],
        backgroundColor: palette[i % 5],
        stack: "tokens",
        yAxisID: "y"
      };
    });
    // Accent role (--md-sys-color-primary) reserved for exactly this line --
    // palette[0] is that same colour in both light and dark modes.
    var lineDataset = {
      type: "line",
      label: "price",
      data: agg.price,
      borderColor: palette[0],
      yAxisID: "y1"
    };
    var datasets = barDatasets.concat([lineDataset]);
    if (perDayChart) {
      perDayChart.data.labels = agg.dates;
      perDayChart.data.datasets = datasets;
      perDayChart.update("none");
      return;
    }
    perDayChart = new Chart(canvas, {
      type: "bar",
      data: {labels: agg.dates, datasets: datasets},
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {stacked: true},
          y: {
            type: "linear",
            position: "left",
            stacked: true,
            title: {display: true, text: "tokens"}
          },
          y1: {
            type: "linear",
            position: "right",
            grid: {drawOnChartArea: false},
            title: {display: true, text: "price"}
          }
        }
      }
    });
  }

  // D-18 item 2 / SD-7: capped, deterministically-ordered horizontal bar
  // chart over aggregateFamilyDistribution's row-count ranking.
  function buildFamilyDistributionChart(rows) {
    var canvas = document.getElementById("family-chart");
    var fallback = document.getElementById("family-chart-fallback");
    if (!chartJsAvailable()) {
      if (canvas) canvas.style.display = "none";
      if (fallback) {
        fallback.textContent = "Chart unavailable \\u2014 chart.js failed to load";
        fallback.style.display = "block";
      }
      return;
    }
    var agg = aggregateFamilyDistribution(rows);
    var noData = agg.labels.length === 0;
    if (canvas) canvas.style.display = noData ? "none" : "";
    if (fallback) {
      fallback.textContent = noData ? "No data for this range" : "";
      fallback.style.display = noData ? "block" : "none";
    }
    if (noData) return;
    var dark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    var palette = dark ? CHART_PALETTE_DARK : CHART_PALETTE_LIGHT;
    var colors = agg.labels.map(function (_, i) { return palette[i % 5]; });
    if (familyChart) {
      familyChart.data.labels = agg.labels;
      familyChart.data.datasets[0].data = agg.counts;
      familyChart.data.datasets[0].backgroundColor = colors;
      familyChart.update("none");
      return;
    }
    familyChart = new Chart(canvas, {
      type: "bar",
      data: {labels: agg.labels, datasets: [{data: agg.counts, backgroundColor: colors}]},
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        /* Each bar is its own category colour, not a multi-series
           breakdown -- a dataset-level legend entry has no dataset
           `label` to show (hence the earlier "undefined" swatch) and
           wouldn't represent the per-bar colouring anyway; the y-axis
           category labels already identify each bar. */
        plugins: {legend: {display: false}}
      }
    });
  }

  // WR-01 (re-review): groupBySession()'s output rows are {session_id,
  // count, tokens_input, tokens_output, price} -- "date" (the default
  // sortKey) is not one of them. Checking "group by session" as a user's
  // very first action -- before ever clicking a column header -- must not
  // silently degrade sortRows into a no-op (undefined == undefined for
  // every row) with zero visual indication anything is unsorted.
  var GROUPED_SORT_KEYS = ["session_id", "count", "tokens_input", "tokens_output", "price"];

  // WR-01 (15.2 mirror): the flat-mode analog of the grouped fallback above.
  // A grouped-only key such as "count" stays in sortKey after
  // group-by-session is unchecked, and without this guard every flat row's
  // row[sortKey] is undefined, so sortRows treats every pair as equal and
  // silently does nothing -- insertion order, no visual indication anything
  // is unsorted.
  var FLAT_SORT_KEYS = [
    "runtime", "model", "family", "subfamily", "command_text",
    "exec_duration_ms", "date", "tokens_input", "tokens_output", "price",
    "source_confidence", "execution_certain", "session_id"
  ];

  // SD-6: the sole entry point that recomputes currentRows from the current
  // filter criteria and the current sort/grouping -- shared by applyFilters
  // (which recomputes currentFiltered too) and applySort (which re-sorts the
  // ALREADY-filtered set without re-running filterRows).
  function buildCurrentRowsFromFiltered() {
    var grouped = document.getElementById("group-by-session").checked;
    if (grouped) {
      // WR-01: fall back to a grouped-valid key when the active sortKey
      // (e.g. the flat-mode default "date", or any other flat-only column)
      // doesn't exist on a grouped row -- never silently no-op the sort.
      var groupedKey = GROUPED_SORT_KEYS.indexOf(sortKey) === -1 ? "session_id" : sortKey;
      currentRows = sortRows(
        groupBySession(currentFiltered),
        groupedKey,
        sortDir
      );
      currentBuilder = groupedRowBuilder;
    } else {
      // WR-01 (15.2): symmetric guard for the flat branch -- never mutate
      // the shared sortKey (re-checking group-by-session must restore the
      // user's grouped-mode choice unchanged).
      var flatKey = FLAT_SORT_KEYS.indexOf(sortKey) === -1 ? "date" : sortKey;
      currentRows = sortRows(currentFiltered, flatKey, sortDir);
      currentBuilder = flatRowBuilder;
    }
  }

  function repaintTable() {
    var grouped = document.getElementById("group-by-session").checked;
    // D-23: swap the visible <thead> row alongside the render-mode toggle so
    // headers always match the cell count/meaning currentBuilder emits.
    if (theadFlat) theadFlat.style.display = grouped ? "none" : "flex";
    if (theadGrouped) theadGrouped.style.display = grouped ? "flex" : "none";
    // Empty state (UI-SPEC.md): a zero-length filtered/grouped row set
    // replaces the table with the locked empty-state copy instead of an
    // empty <tbody>. Relaxing the filter removes the state and resumes
    // normal rendering.
    var empty = shouldShowEmptyState(currentRows);
    if (tableEmptyState) tableEmptyState.hidden = !empty;
    if (scrollEl) scrollEl.style.display = empty ? "none" : "";
    if (virtualizer) {
      virtualizer.setOptions(virtualizerOptions(currentRows.length));
      virtualizer.measure();
    }
    if (resultCount) {
      resultCount.textContent = grouped
        ? currentFiltered.length + " matching commands across " + currentRows.length + " sessions"
        : currentRows.length + " matching commands";
    }
    paint();
  }

  // SD-6: applyFilters() recomputes the filtered row set, repaints the
  // table, AND recomputes all three chart instances IN PLACE from that same
  // filtered set. applySort() re-sorts the already-filtered row set and
  // repaints the table ONLY -- sorting cannot change any chart's contents,
  // so its body must never call a chart-update function. The <th> click
  // listener below calls applySort(), never applyFilters().
  function applyFilters() {
    currentFiltered = filterRows(data, readCriteria());
    buildCurrentRowsFromFiltered();
    repaintTable();
    buildRuntimeChart(currentFiltered);
    buildPerDayChart(currentFiltered);
    buildFamilyDistributionChart(currentFiltered);
  }

  function applySort() {
    buildCurrentRowsFromFiltered();
    repaintTable();
  }

  document.querySelectorAll("#usage-table th").forEach(function (th) {
    th.addEventListener("click", function () {
      var key = th.getAttribute("data-sort-key");
      if (!key) return;
      if (sortKey === key) sortDir = sortDir === "asc" ? "desc" : "asc";
      else {
        sortKey = key;
        sortDir = "asc";
      }
      applySort();
    });
  });

  // SD-6: `change` (selects, date inputs, the group-by-session checkbox)
  // stays immediate; `input` (text/number fields) is debounced at a fixed
  // 150ms so a keystroke does not run three full-dataset aggregations.
  var debouncedApplyFilters = debounce(applyFilters, 150);
  filtersForm.addEventListener("input", debouncedApplyFilters);
  filtersForm.addEventListener("change", applyFilters);
  document.getElementById("clear-filters").addEventListener("click", function (event) {
    event.preventDefault();
    clearFilters();
  });

  function initialize() {
    // SD-10 step 3: the blocking initialization, run only once the browser
    // has had a chance to paint the progress bar shown synchronously below.
    decorateSubfamily(data);
    // D-14 / SD-3: built ONCE at load, immediately after decorateSubfamily,
    // over the full embedded payload -- this is what lets a sibling step
    // excluded by the current filter still appear in the detail dialog.
    rowsByRawRef = indexByRawRef(data);

    fillSelect("filter-runtime", distinctValues("runtime"));
    fillSelect("filter-model", distinctValues("model"));
    fillSelect("filter-family", distinctValues("family"));
    fillSelect("filter-subfamily", distinctValues("subfamily"));

    // Default to the last-30-days preset on initial load rather than an
    // unfiltered view of the full embedded dataset -- applyDatePreset()
    // sets the date inputs and calls applyFilters() itself.
    applyDatePreset("month");
    if (window.__virtualCore) {
      mountVirtualizer();
    } else {
      window.addEventListener("virtual-core-ready", function () {
        mountVirtualizer();
      }, {once: true});
      // WR-02: if the CDN-hosted @tanstack/virtual-core script never loads
      // (network failure, ad-blocker, offline file:// open -- a real
      // scenario for a local-first tool), "virtual-core-ready" never fires,
      // virtualizer stays null forever, and paint() silently no-ops on
      // every call while the loading bar has already been removed below.
      // Surface the same page-level error state the JSON-parse-failure path
      // uses if the virtualizer still hasn't mounted a few seconds later --
      // a no-op if it mounted in time (virtualizer is non-null by then).
      // The timer id is stashed in virtualizerFallbackTimer so a mount that
      // succeeds later -- via the listener above, even after this timer has
      // already fired and shown the error -- can neutralize/reverse it
      // (see mountVirtualizer()'s hidePageError() call).
      virtualizerFallbackTimer = setTimeout(function () {
        if (!virtualizer) showPageError();
      }, 5000);
    }

    if (loadingBar) loadingBar.remove();
    setFilterControlsDisabled(false);
  }

  // SD-10: show the bar and disable the controls SYNCHRONOUSLY (both true
  // the instant this script runs), then defer the blocking work behind a
  // DOUBLE requestAnimationFrame -- a single frame only schedules the
  // callback, it does not guarantee the browser has actually painted the
  // bar first. Falls back to setTimeout(fn, 0) when requestAnimationFrame
  // is unavailable (the node-executed test harness, which has no browser).
  setFilterControlsDisabled(true);
  if (typeof requestAnimationFrame === "function") {
    requestAnimationFrame(function () {
      requestAnimationFrame(initialize);
    });
  } else {
    setTimeout(initialize, 0);
  }
})();
</script>
</body>
</html>
"""


def _ensure_private_dir(directory: str) -> None:
    if not directory:
        directory = "."
    os.makedirs(directory, mode=0o700, exist_ok=True)
    os.chmod(directory, 0o700)


def _atomic_write_text(path: str, text: str) -> None:
    """Ported from `tools/config_doctor_appliers.py::_atomic_write_text`."""
    directory = os.path.dirname(path) or "."
    _ensure_private_dir(directory)
    target = os.path.realpath(path)
    dirname = os.path.dirname(target) or "."
    existed = os.path.isfile(target)
    mode = stat.S_IMODE(os.stat(target).st_mode) if existed else 0o600
    fd, tmp = tempfile.mkstemp(dir=dirname, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, target)
    except OSError:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    try:
        dir_fd = os.open(dirname, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        pass


def _query_rows(conn: sqlite3.Connection | None) -> list[dict]:
    if conn is None:
        return []
    conn.row_factory = sqlite3.Row
    sql = "SELECT " + ", ".join(_QUERY_COLUMNS) + " FROM refined_commands"
    return [dict(item) for item in conn.execute(sql).fetchall()]


def _encode_payload(rows: list[dict]) -> str:
    payload = json.dumps(rows, ensure_ascii=False, default=str)
    return payload.replace("</script", "<\\/script")


def _render_html(payload: str) -> str:
    return _HTML_HEAD + payload + _HTML_MID


def generate(conn: sqlite3.Connection | None, output_path: str) -> None:
    """Write a static dashboard HTML file from an already-open refined DB."""
    rows = _query_rows(conn)
    _atomic_write_text(output_path, _render_html(_encode_payload(rows)))
