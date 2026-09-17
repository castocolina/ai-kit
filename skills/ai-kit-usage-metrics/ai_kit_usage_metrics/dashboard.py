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
<script type="importmap">
{
  "imports": {
    "@material/web/": "https://esm.run/@material/web@2.5.0/"
  }
}
</script>
<script type="module">
import "@material/web/checkbox/checkbox.js";
import "@material/web/select/outlined-select.js";
import "@material/web/select/select-option.js";
import "@material/web/textfield/outlined-text-field.js";
import "@material/web/button/text-button.js";
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
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js"></script>
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
}
@media (prefers-color-scheme: dark) {
  :root {
    --md-sys-color-surface: #1C1B1F;
    --md-sys-color-surface-variant: #49454F;
    --md-sys-color-primary: #D0BCFF;
    --md-sys-color-error: #F2B8B5;
    --md-sys-color-on-surface: #E6E1E5;
    --md-sys-color-outline: #938F99;
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
#filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm) var(--space-md);
  margin-bottom: var(--space-lg);
  background: var(--md-sys-color-surface-variant);
  padding: var(--space-md);
  border-radius: 4px;
}
#filters label {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  font-size: var(--md-sys-typescale-label-size);
  font-weight: var(--md-sys-typescale-label-weight);
  line-height: var(--md-sys-typescale-label-line-height);
}
#filters md-outlined-select,
#filters md-outlined-text-field {
  min-width: 140px;
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
}
#date-range-group .date-range-sep {
  color: var(--md-sys-color-outline);
  font-size: var(--md-sys-typescale-label-size);
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
#charts-row {
  display: flex;
  gap: var(--space-xl);
  margin-bottom: var(--space-lg);
}
#chart-runtime-panel {
  background: var(--md-sys-color-surface-variant);
  padding: var(--space-md);
  border-radius: 4px;
}
#runtime-chart-fallback {
  color: var(--md-sys-color-error);
  font-size: var(--md-sys-typescale-label-size);
  display: none;
}
#table-scroll {
  overflow-y: auto;
  max-height: 480px;
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
#usage-table .row-grouped th:nth-child(1),
#usage-table .row-grouped td:nth-child(1) { flex: 0 0 200px; }
#usage-table .row-grouped th:nth-child(2),
#usage-table .row-grouped td:nth-child(2) { flex: 0 0 100px; }
#usage-table .row-grouped th:nth-child(3),
#usage-table .row-grouped td:nth-child(3) { flex: 0 0 130px; }
#usage-table .row-grouped th:nth-child(4),
#usage-table .row-grouped td:nth-child(4) { flex: 0 0 130px; }
#usage-table .row-grouped th:nth-child(5),
#usage-table .row-grouped td:nth-child(5) { flex: 1 1 100px; min-width: 0; }
</style>
</head>
<body>
<h1>Usage metrics</h1>
<form id="filters">
<label>runtime
<md-outlined-select id="filter-runtime"></md-outlined-select>
</label>
<label>model
<md-outlined-select id="filter-model"></md-outlined-select>
</label>
<label>family
<md-outlined-select id="filter-family"></md-outlined-select>
</label>
<label>subfamily
<md-outlined-select id="filter-subfamily"></md-outlined-select>
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
<div id="charts-row">
<div id="chart-runtime-panel">
<canvas id="runtime-chart" width="240" height="240"></canvas>
<p id="runtime-chart-fallback"></p>
</div>
</div>
<div id="table-scroll">
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
var SUBFAMILY_WRAPPERS = ["sudo", "env", "time", "nice", "ionice"];
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
    var key = String(sid) + "\\0" + String(row.turn_id);
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
/* PURE_FUNCTIONS_END */

var CHART_PALETTE_LIGHT = ["#6750A4", "#7D5260", "#625B71", "#79747E", "#1C1B1F"];
var CHART_PALETTE_DARK = ["#D0BCFF", "#EFB8C8", "#CCC2DC", "#938F99", "#E6E1E5"];

function chartJsAvailable() {
  return typeof Chart !== "undefined";
}

(function () {
  var dataEl = document.getElementById("usage-metrics-data");
  var data = JSON.parse(dataEl.textContent);
  decorateSubfamily(data);
  var tbody = document.getElementById("usage-tbody");
  var scrollEl = document.getElementById("table-scroll");
  var theadFlat = document.getElementById("thead-flat");
  var theadGrouped = document.getElementById("thead-grouped");
  var sortKey = "date";
  var sortDir = "asc";
  var virtualizer = null;
  var currentRows = [];
  var currentBuilder = flatRowBuilder;
  var runtimeChart = null;

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
    // SD-8: md-outlined-select does not render bare <option> children --
    // it needs md-select-option elements with a slotted headline div. Clear
    // first so repeat calls stay idempotent; the all-value option is always
    // created first, one option per distinct value follows, then the
    // select's own value is set to "all".
    var select = document.getElementById(id);
    select.textContent = "";
    function addOption(value) {
      var opt = document.createElement("md-select-option");
      opt.value = value;
      var headline = document.createElement("div");
      headline.slot = "headline";
      headline.textContent = value;
      opt.appendChild(headline);
      select.appendChild(opt);
    }
    addOption("all");
    values.forEach(addOption);
    select.value = "all";
  }

  fillSelect("filter-runtime", distinctValues("runtime"));
  fillSelect("filter-model", distinctValues("model"));
  fillSelect("filter-family", distinctValues("family"));
  fillSelect("filter-subfamily", distinctValues("subfamily"));

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
    // SD-9: reset every filter-* control, then render() exactly once at the
    // end. The session-grouping checkbox is deliberately left alone -- it
    // is a view mode, not a filter.
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
    render();
  }

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
    var cell = document.createElement("td");
    cell.className = "command-cell";
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
    if (row.price == null) cell.title = PRICE_UNKNOWN_TOOLTIP;
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
    if (row.source_confidence) {
      conf.textContent = String(row.source_confidence);
      conf.className = "badge";
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
    // and grouped modes route through it -- render() only ever changes which
    // row array (currentRows) and which cell-builder (currentBuilder) it
    // reads, never adds a second append loop.
    if (!virtualizer) return;
    tbody.style.height = virtualizer.getTotalSize() + "px";
    tbody.textContent = "";
    var items = sliceForItems(currentRows, virtualizer.getVirtualItems());
    items.forEach(function (entry) {
      var tr = currentBuilder(entry.row);
      tr.style.transform = "translateY(" + entry.start + "px)";
      tbody.appendChild(tr);
    });
  }

  function mountVirtualizer() {
    var vc = window.__virtualCore;
    if (!vc || virtualizer) return;
    virtualizer = new vc.Virtualizer(virtualizerOptions(currentRows.length));
    virtualizer._didMount();
    virtualizer._willUpdate();
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
      }
    });
  }

  function render() {
    var grouped = document.getElementById("group-by-session").checked;
    var filtered = filterRows(data, readCriteria());
    if (grouped) {
      currentRows = sortRows(
        groupBySession(filtered),
        sortKey === "session_id" ? "session_id" : sortKey,
        sortDir
      );
      currentBuilder = groupedRowBuilder;
    } else {
      currentRows = sortRows(filtered, sortKey, sortDir);
      currentBuilder = flatRowBuilder;
    }
    // D-23: swap the visible <thead> row alongside the render-mode toggle so
    // headers always match the cell count/meaning currentBuilder emits.
    if (theadFlat) theadFlat.style.display = grouped ? "none" : "flex";
    if (theadGrouped) theadGrouped.style.display = grouped ? "flex" : "none";
    if (virtualizer) {
      virtualizer.setOptions(virtualizerOptions(currentRows.length));
      virtualizer.measure();
    }
    paint();
    buildRuntimeChart(filtered);
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
      render();
    });
  });

  document.getElementById("filters").addEventListener("input", render);
  document.getElementById("filters").addEventListener("change", render);
  document.getElementById("clear-filters").addEventListener("click", function (event) {
    event.preventDefault();
    clearFilters();
  });

  render();
  if (window.__virtualCore) {
    mountVirtualizer();
  } else {
    window.addEventListener("virtual-core-ready", function () {
      mountVirtualizer();
    }, {once: true});
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
