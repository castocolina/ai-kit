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
  font-size: var(--md-sys-typescale-label-size);
  font-weight: var(--md-sys-typescale-label-weight);
  line-height: var(--md-sys-typescale-label-line-height);
}
input, select {
  padding: var(--space-sm);
}
.badge {
  color: var(--md-sys-color-error);
  font-size: var(--md-sys-typescale-label-size);
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
#usage-table th:nth-child(1), #usage-table td:nth-child(1) { flex: 0 0 90px; }
#usage-table th:nth-child(2), #usage-table td:nth-child(2) { flex: 0 0 100px; }
#usage-table th:nth-child(3), #usage-table td:nth-child(3) { flex: 0 0 140px; }
#usage-table th:nth-child(4), #usage-table td:nth-child(4) { flex: 0 0 90px; }
#usage-table th:nth-child(5), #usage-table td:nth-child(5) { flex: 1 1 320px; min-width: 0; }
#usage-table th:nth-child(6), #usage-table td:nth-child(6) { flex: 0 0 90px; }
#usage-table th:nth-child(7), #usage-table td:nth-child(7) { flex: 0 0 90px; }
#usage-table th:nth-child(8), #usage-table td:nth-child(8) { flex: 0 0 80px; }
#usage-table th:nth-child(9), #usage-table td:nth-child(9) { flex: 0 0 130px; }
#usage-table th:nth-child(10), #usage-table td:nth-child(10) { flex: 0 0 100px; }
#usage-table th:nth-child(11), #usage-table td:nth-child(11) { flex: 0 0 140px; }
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
<label>family
<select id="filter-family"><option value="all">all</option></select>
</label>
<label>model
<select id="filter-model"><option value="all">all</option></select>
</label>
<label>command
<input id="filter-command" type="text">
</label>
<label>date
<select id="filter-date-preset">
<option value="all">all</option>
<option value="day">single day</option>
<option value="week">current week</option>
<option value="current_month">current month</option>
<option value="custom">custom range</option>
</select>
</label>
<label>day
<input id="filter-date-day" type="date">
</label>
<label>start
<input id="filter-date-start" type="date">
</label>
<label>end
<input id="filter-date-end" type="date">
</label>
<label>tokens min
<input id="filter-tokens-min" type="number">
</label>
<label>tokens max
<input id="filter-tokens-max" type="number">
</label>
<label>price min
<input id="filter-price-min" type="number">
</label>
<label>price max
<input id="filter-price-max" type="number">
</label>
<label>group by session
<md-checkbox id="group-by-session"></md-checkbox>
</label>
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
<th data-sort-key="date">date</th>
<th data-sort-key="model">model</th>
<th data-sort-key="family">family</th>
<th data-sort-key="command_text">command</th>
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
function pad2(n) {
  return n < 10 ? "0" + n : String(n);
}

function ymd(d) {
  return d.getFullYear() + "-" + pad2(d.getMonth() + 1) + "-" + pad2(d.getDate());
}

function currentMonthPrefix() {
  // "current month" is YYYY-MM prefix-matched against each row's date at
  // render time using the browser's own new Date(). The SAME dashboard HTML
  // file therefore answers "current month" differently depending on WHEN it
  // is opened. That is intentional, and distinct from every OTHER piece of
  // data in the file, which IS fixed at generation time.
  var now = new Date();
  return now.getFullYear() + "-" + pad2(now.getMonth() + 1);
}

function currentWeekRange() {
  var now = new Date();
  var day = now.getDay();
  var offset = day === 0 ? -6 : 1 - day;
  var monday = new Date(now.getFullYear(), now.getMonth(), now.getDate() + offset);
  var sunday = new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() + 6);
  return [ymd(monday), ymd(sunday)];
}

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
  var family = criteria.family;
  var model = criteria.model;
  var cmd = criteria.commandText ? String(criteria.commandText).toLowerCase() : "";
  var preset = criteria.datePreset;
  var tmin = numOrNull(criteria.tokensMin);
  var tmax = numOrNull(criteria.tokensMax);
  var pmin = numOrNull(criteria.priceMin);
  var pmax = numOrNull(criteria.priceMax);
  var week = preset === "week" ? currentWeekRange() : null;
  var monthPrefix = preset === "current_month" ? currentMonthPrefix() : null;
  return rows.filter(function (row) {
    if (family && family !== "all" && row.family !== family) return false;
    if (model && model !== "all" && row.model !== model) return false;
    if (cmd) {
      var hay = row.command_text == null ? "" : String(row.command_text);
      if (hay.toLowerCase().indexOf(cmd) === -1) return false;
    }
    if (preset === "day") {
      if (String(row.date || "") !== String(criteria.dateDay || "")) return false;
    } else if (preset === "week") {
      if (!inDateRange(row.date, week[0], week[1])) return false;
    } else if (preset === "current_month") {
      if (String(row.date || "").indexOf(monthPrefix) !== 0) return false;
    } else if (preset === "custom") {
      if (!inDateRange(row.date, criteria.dateStart, criteria.dateEnd)) {
        return false;
      }
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
    var select = document.getElementById(id);
    values.forEach(function (v) {
      var opt = document.createElement("option");
      opt.value = v;
      opt.textContent = v;
      select.appendChild(opt);
    });
  }

  fillSelect("filter-family", distinctValues("family"));
  fillSelect("filter-model", distinctValues("model"));

  function readCriteria() {
    return {
      family: document.getElementById("filter-family").value,
      model: document.getElementById("filter-model").value,
      commandText: document.getElementById("filter-command").value,
      datePreset: document.getElementById("filter-date-preset").value,
      dateDay: document.getElementById("filter-date-day").value,
      dateStart: document.getElementById("filter-date-start").value,
      dateEnd: document.getElementById("filter-date-end").value,
      tokensMin: document.getElementById("filter-tokens-min").value,
      tokensMax: document.getElementById("filter-tokens-max").value,
      priceMin: document.getElementById("filter-price-min").value,
      priceMax: document.getElementById("filter-price-max").value
    };
  }

  function td(text) {
    var cell = document.createElement("td");
    cell.textContent = text == null ? "" : String(text);
    return cell;
  }

  function isConditional(row) {
    return row.execution_certain === false || row.execution_certain === 0;
  }

  function flatRowBuilder(row) {
    var tr = document.createElement("tr");
    tr.appendChild(td(row.runtime));
    tr.appendChild(td(row.date));
    tr.appendChild(td(row.model));
    tr.appendChild(td(displayFamily(row)));
    tr.appendChild(td(row.command_text));
    tr.appendChild(td(row.tokens_input));
    tr.appendChild(td(row.tokens_output));
    tr.appendChild(td(row.price));
    var conf = document.createElement("td");
    if (row.source_confidence) {
      conf.textContent = String(row.source_confidence);
      conf.className = "badge";
    }
    tr.appendChild(conf);
    var exec = document.createElement("td");
    if (isConditional(row)) exec.textContent = "(conditional)";
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
