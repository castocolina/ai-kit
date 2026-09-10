"""Static HTML dashboard: embed refined rows, no server, no export step."""

from __future__ import annotations

import json
import os
import sqlite3
import stat
import tempfile

_TABLE_COLUMNS = (
    "date",
    "model",
    "family",
    "tokens_input",
    "tokens_output",
    "price",
)

_HTML_SHELL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>ai-kit usage metrics</title>
<style>
body {{ font-family: sans-serif; margin: 1.5rem; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ccc; padding: 0.4rem 0.6rem; text-align: left; }}
th {{ cursor: pointer; }}
input {{ margin-bottom: 0.8rem; padding: 0.3rem; width: 20rem; }}
</style>
</head>
<body>
<h1>Usage metrics</h1>
<input id="filter" type="search" placeholder="Filter rows">
<table id="usage-table">
<thead><tr>{thead}</tr></thead>
<tbody></tbody>
</table>
<script type="application/json" id="usage-metrics-data">{payload}</script>
<script>
(function () {{
  const cols = {cols};
  const data = JSON.parse(document.getElementById("usage-metrics-data").textContent);
  const tbody = document.querySelector("#usage-table tbody");
  const filter = document.getElementById("filter");
  let sortKey = "date";
  let sortAsc = true;
  function render() {{
    const q = (filter.value || "").toLowerCase();
    const rows = data.filter(function (row) {{
      return cols.some(function (c) {{
        return String(row[c] == null ? "" : row[c]).toLowerCase().indexOf(q) !== -1;
      }});
    }}).slice().sort(function (a, b) {{
      const av = a[sortKey], bv = b[sortKey];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      if (av < bv) return sortAsc ? -1 : 1;
      if (av > bv) return sortAsc ? 1 : -1;
      return 0;
    }});
    tbody.textContent = "";
    rows.forEach(function (row) {{
      const tr = document.createElement("tr");
      cols.forEach(function (c) {{
        const td = document.createElement("td");
        td.textContent = row[c] == null ? "" : String(row[c]);
        tr.appendChild(td);
      }});
      tbody.appendChild(tr);
    }});
  }}
  document.querySelectorAll("#usage-table th").forEach(function (th) {{
    th.addEventListener("click", function () {{
      const key = th.getAttribute("data-col");
      if (sortKey === key) sortAsc = !sortAsc;
      else {{ sortKey = key; sortAsc = true; }}
      render();
    }});
  }});
  filter.addEventListener("input", render);
  render();
}})();
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


def generate(conn: sqlite3.Connection | None, output_path: str) -> None:
    rows: list[dict] = []
    if conn is not None:
        conn.row_factory = sqlite3.Row
        fetched = conn.execute("SELECT * FROM refined_commands").fetchall()
        rows = [dict(item) for item in fetched]
    payload = json.dumps(rows, ensure_ascii=False, default=str)
    payload = payload.replace("</script", "<\\/script")
    thead = "".join(
        f'<th data-col="{col}">{col}</th>' for col in _TABLE_COLUMNS
    )
    html = _HTML_SHELL.format(
        thead=thead,
        payload=payload,
        cols=json.dumps(list(_TABLE_COLUMNS)),
    )
    _atomic_write_text(output_path, html)
