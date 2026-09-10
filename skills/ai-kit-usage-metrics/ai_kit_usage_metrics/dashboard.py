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
<style>
body { font-family: sans-serif; margin: 1.5rem; }
#filters { display: flex; flex-wrap: wrap; gap: 0.6rem 1rem; margin-bottom: 1rem; }
#filters label { display: flex; flex-direction: column; font-size: 0.85rem; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #ccc; padding: 0.4rem 0.6rem; text-align: left; }
th { cursor: pointer; }
input, select { padding: 0.3rem; }
.badge { color: #555; font-size: 0.85rem; }
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
<label><input id="group-by-session" type="checkbox"> group by session</label>
</form>
<table id="usage-table">
<thead>
<tr>
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
<th data-sort-key="runtime">runtime</th>
</tr>
</thead>
<tbody id="usage-tbody"></tbody>
</table>
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
/* PURE_FUNCTIONS_END */

(function () {
  var dataEl = document.getElementById("usage-metrics-data");
  var data = JSON.parse(dataEl.textContent);
  var tbody = document.getElementById("usage-tbody");
  var sortKey = "date";
  var sortDir = "asc";

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

  function renderFlat(rows) {
    tbody.textContent = "";
    rows.forEach(function (row) {
      var tr = document.createElement("tr");
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
      tr.appendChild(td(row.runtime));
      tbody.appendChild(tr);
    });
  }

  function renderGrouped(rows) {
    tbody.textContent = "";
    rows.forEach(function (row) {
      var tr = document.createElement("tr");
      tr.appendChild(td(row.session_id));
      tr.appendChild(td(row.count));
      tr.appendChild(td(row.tokens_input));
      tr.appendChild(td(row.tokens_output));
      tr.appendChild(td(row.price));
      tbody.appendChild(tr);
    });
  }

  function render() {
    var grouped = document.getElementById("group-by-session").checked;
    var rows = filterRows(data, readCriteria());
    if (grouped) {
      rows = groupBySession(rows);
      rows = sortRows(rows, sortKey === "session_id" ? "session_id" : sortKey, sortDir);
      renderGrouped(rows);
    } else {
      rows = sortRows(rows, sortKey, sortDir);
      renderFlat(rows);
    }
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
