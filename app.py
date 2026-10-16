"""Drift — configuration comparison (Streamlit).

Run:  streamlit run app.py
Files: core.py (parsing + logic) · data.py (sample data) · explain.py (AI) · ui.py (HTML/CSS)

Flow: the app starts empty. Upload a CURRENT file (JSON or sshd_config). A BASELINE file is optional:
with one, the two files are compared; without one, the current file is checked against the
built-in standard baseline.
"""
import json
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from core import (RISK_ORDER, STANDARD_BASELINE, TYPE_LABEL, ConfigError, analyze, build_run, f_actual,
                  f_expected, label, report_csv, report_data, totals)
from data import get_mock_servers
from explain import explain
from ui import (BRAND, CSS, FOOTER, baseline_table, chip, empty, empty_clean, empty_state, esc, features,
                finding_chips, fmt_date, hero, raw_json, ready_line, result_head, rich, ring,
                risk_badge, status_badge, step_head, time_ago, trend, type_badge, verdict)

st.set_page_config(page_title="Drift · Configuration comparison", page_icon="🛡️", layout="wide",
                   initial_sidebar_state="collapsed")
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

ss = st.session_state
DEC_FILE = Path(__file__).with_name("decisions.json")
NAV = [("compare", "Compare"), ("findings", "Findings"), ("remediation", "Remediation"), ("reports", "Reports")]
PAGES = dict(NAV)


def H(html: str):
    """Render an HTML snippet."""
    if not html.startswith(("<div", "<svg", "<section", "<table")):
        html = f"<div>{html}</div>"
    st.markdown(html, unsafe_allow_html=True)


# ================================================================= state
def load_decisions() -> dict:
    try:
        return json.loads(DEC_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_decisions():
    try:
        DEC_FILE.write_text(json.dumps(ss.decisions, indent=2), encoding="utf-8")
    except Exception:
        pass  # read-only folder: keep decisions in memory only


if "ready" not in ss:
    ss.ready = True
    qp = st.query_params.get("page", "compare")
    ss.page = qp if qp in PAGES else "compare"
    ss.run = None            # nothing loaded: the app starts empty
    ss.history = []
    ss.decisions = load_decisions()
    ss.review_id = None
    ss.error = ""


def go(page: str):
    ss.page = page
    st.query_params["page"] = page


def open_review(fid: str):
    ss.review_id = fid


def decide(fid: str, status: str):
    if status == "Pending":
        ss.decisions.pop(fid, None)
        msg = "Decision reopened"
    else:
        ss.decisions[fid] = {"status": status, "by": "You", "at": datetime.now().isoformat(timespec="seconds"),
                             "note": ss.get(f"note_{fid}", "")}
        msg = f"Fix {status.lower()} (recorded only; no server was changed)"
    save_decisions()
    ss.flash = msg
    ss.review_id = fid          # reopen the panel so the new state is visible
    st.rerun()


def dstatus(fid: str) -> str:
    return ss.decisions.get(fid, {}).get("status", "Pending")


def run_comparison(cur_name, cur_bytes, base_name=None, base_bytes=None):
    try:
        run = build_run(cur_name, cur_bytes, base_name, base_bytes)
    except ConfigError as e:
        ss.error = str(e)
        return
    ss.run, ss.error = run, ""
    a = analyze(run)
    ss.history.append({"time": run["last_scan"], "name": run["name"], "against": run["base_label"],
                       "drifts": len(a["findings"]), "high": sum(f["risk"] == "High" for f in a["findings"]),
                       "score": a["score"]})
    ss.flash = "Comparison complete"
    go("findings")


def do_compare():
    cur, base = ss.get("up_cur"), ss.get("up_base")
    if not cur:
        ss.error = "Add a current configuration file first."
        return
    run_comparison(cur.name, cur.getvalue(), base.name if base else None, base.getvalue() if base else None)


def do_sample():
    sample = json.dumps(get_mock_servers()[0]["current"], indent=2).encode()
    run_comparison("sample-server.json", sample)


# ================================================================= data
A = [analyze(ss.run)] if ss.run else []
T = totals(A)
PENDING = sum(1 for f in T["all"] if dstatus(f["id"]) == "Pending")
BY_ID = {f["id"]: (f, s) for s in A for f in s["findings"]}

if ss.get("flash"):
    st.toast(ss.pop("flash"))


# ================================================================= helpers
def table(prefix: str, widths: list, headers: list, rows: list):
    """A styled table made of columns. Each cell is an HTML string or a function that draws widgets."""
    with st.container(key=f"tbl_{prefix}"):
        with st.container(key=f"thead_{prefix}"):
            for c, h in zip(st.columns(widths), headers):
                c.markdown(f'<div class="th">{h}</div>', unsafe_allow_html=True)
        for i, row in enumerate(rows):
            with st.container(key=f"trow_{prefix}_{i}"):
                for c, cell in zip(st.columns(widths, vertical_alignment="center"), row):
                    with c:
                        if callable(cell):
                            cell()
                        else:
                            H(cell)


def review_btn(fid: str, ctx: str):
    def _draw():
        st.button("Review", key=f"rev_{ctx}_{fid}", on_click=open_review, args=(fid,))
    return _draw


def need_run(title: str, msg: str) -> bool:
    """Empty state for pages that need a comparison. Returns True when there is nothing to show."""
    if ss.run:
        return False
    H(empty_state(title, msg))
    st.write("")
    _, mid, _ = st.columns([2, 1.2, 2])
    mid.button("Start a comparison", key=f"start_{ss.page}", type="primary", on_click=go, args=("compare",))
    return True


# ================================================================= top navigation
active = ss.page
dyn = (f".st-key-nav_{active} button{{background:var(--alt)!important;color:var(--ink)!important;font-weight:650!important}}")
if PENDING:
    dyn += (f'.st-key-nav_remediation button::after{{content:"{PENDING}";margin-left:6px;background:#0071E3;color:#fff;'
            "border-radius:999px;font-size:.7rem;font-weight:600;padding:0 7px}")
st.markdown(f"<style>{dyn}</style>", unsafe_allow_html=True)

with st.container(key="topnav"):
    cols = st.columns([1.5, 0.95, 0.95, 1.25, 0.95, 3], vertical_alignment="center")
    cols[0].markdown(BRAND, unsafe_allow_html=True)
    for col, (key, text) in zip(cols[1:5], NAV):
        col.button(text, key=f"nav_{key}", on_click=go, args=(key,), use_container_width=True)
    if ss.run:
        cols[5].markdown(f'<div class="nav-right">{esc(ss.run["name"])} · {time_ago(ss.run["last_scan"])}</div>',
                         unsafe_allow_html=True)


# ================================================================= pages
def page_compare():
    H(hero())
    left, right = st.columns(2, gap="large")
    with left:
        with st.container(key="card_cur"):
            H(step_head("1", "Current configuration", "Required", "req",
                        "The file you want to check. Drop in a JSON file or an sshd_config."))
            st.file_uploader("Current configuration", key="up_cur", label_visibility="collapsed")
    with right:
        with st.container(key="card_base"):
            H(step_head("2", "Baseline", "Optional", "opt",
                        "What it should look like. Skip it and we use our standard secure baseline."))
            st.file_uploader("Baseline", key="up_base", label_visibility="collapsed")

    cur, base = ss.get("up_cur"), ss.get("up_base")
    if cur and base:
        H(ready_line(f"<b>{esc(cur.name)}</b> will be compared with your baseline <b>{esc(base.name)}</b>", True))
    elif cur:
        H(ready_line(f"<b>{esc(cur.name)}</b> will be checked against the <b>standard secure baseline</b>", True))
    else:
        H(ready_line("Add a current configuration to begin", False))

    if ss.error:
        _, mid, _ = st.columns([1, 3, 1])
        mid.error(ss.error)

    _, b1, b2, _ = st.columns([2, 1.3, 1.3, 2], vertical_alignment="center")
    b1.button("Compare", key="do_compare", type="primary", disabled=not cur, on_click=do_compare,
              use_container_width=True)
    b2.button("Try sample data", key="do_sample", type="tertiary", on_click=do_sample, use_container_width=True)

    st.write("")
    with st.expander("What is the standard baseline?"):
        st.caption("Used only when you don't upload a baseline. Only settings that exist in your file are checked.")
        H(baseline_table())
    H(features())


def page_findings():
    if need_run("No results yet", "Upload a configuration on the Compare page and your findings will appear here."):
        return
    s = A[0]
    h1, h2 = st.columns([5, 1.2], vertical_alignment="bottom")
    h1.markdown(result_head(s["name"], s["kind"], s["base_label"], fmt_date(s["last_scan"])), unsafe_allow_html=True)
    h2.button("New comparison", key="new_cmp", on_click=go, args=("compare",), use_container_width=True)

    ca, cb = st.columns([1, 2.3], gap="large")
    with ca:
        with st.container(key="card_ring"):
            H('<div class="center"><div class="card-title">Security posture</div>' + ring(s["score"]) +
              '<p class="formula">100 − 15 per High − 7 per Medium − 2 per Low</p></div>')
    with cb:
        with st.container(key="card_verdict"):
            H(verdict(s["findings"], len(s["baseline"])))
    st.write("")

    if s["mode"] == "standard":
        extra = ""
        if s["not_covered"]:
            extra += (f'<b>{len(s["not_covered"])}</b> setting{"" if len(s["not_covered"]) == 1 else "s"} in your file '
                      f'aren\'t covered by the standard baseline and were left out. ')
        extra += "Upload your own baseline to compare everything."
        H(f'<div class="note"><b>Checked {len(s["baseline"])} of {len(STANDARD_BASELINE)} standard settings.</b> {extra}</div>')
        if s["not_covered"]:
            with st.expander("Settings that weren't checked"):
                st.write(", ".join(f"`{k}`" for k in s["not_covered"]))
        st.write("")

    # Informational section: current settings that do not exist in the uploaded baseline.
    # These are not classified as vulnerabilities; they are simply not comparable.
    if s["mode"] == "custom":
        current_only = [(k, value) for k, value in s["current"].items() if k not in s["baseline"]]
        if current_only:
            H('<div class="card-title">Configurations Not Available in Baseline</div>')
            st.caption(
                "These settings are present in the current configuration but do not exist "
                "in the uploaded baseline, so they are not available for comparison. "
                "They are listed for information only and are not automatically marked as risky."
            )
            info_rows = []
            for setting, value in current_only:
                info_rows.append([
                    f'{esc(label(setting))}<span class="key">{esc(setting)}</span>',
                    chip(value, "", True),
                    '<span class="muted">Not available to compare with baseline.</span>',
                ])
            table(
                "current_only",
                [2, 1.2, 2.5],
                ["Setting", "Current value", "Comparison status"],
                info_rows,
            )
            st.write("")

    t_find, t_raw = st.tabs(["Findings", "Raw data"])
    with t_find:
        e1, e2, e3, _ = st.columns([1, 1, 1.6, 2], vertical_alignment="bottom")
        xr = e1.selectbox("Risk", ["All", "High", "Medium", "Low"], key="x_risk")
        xt = e2.selectbox("Change", ["All", "Modified", "Added", "Removed"], key="x_type")
        xu = e3.checkbox("Show unchanged settings", key="x_unch")
        keys = list(dict.fromkeys(list(s["baseline"]) + list(s["current"])))
        fmap = {f["setting"]: f for f in s["findings"]}
        ordered = sorted(keys, key=lambda k: RISK_ORDER[fmap[k]["risk"]] if k in fmap else 9)
        rows = []
        for k in ordered:
            f = fmap.get(k)
            if not f and not xu:
                continue
            if xr != "All" and (not f or f["risk"] != xr):
                continue
            if xt != "All" and (not f or f["type"] != xt.lower()):
                continue
            typ = f["type"] if f else "same"
            rows.append([f'{esc(label(k))}<span class="key">{esc(k)}</span>',
                         chip(s["baseline"].get(k), "", k in s["baseline"]),
                         chip(s["current"].get(k), "t-" + typ if f else "", k in s["current"]),
                         type_badge(typ), risk_badge(f["risk"]) if f else '<span class="muted">—</span>',
                         status_badge(dstatus(f["id"])) if f else "",
                         review_btn(f["id"], "ex") if f else ""])
        if rows:
            table("explorer", [2.2, 1.6, 1.6, 1.1, 1, 1.1, 1],
                  ["Setting", "Baseline", "Current", "Change", "Risk", "Decision", ""], rows)
        elif not s["findings"] and xr == "All" and xt == "All":
            H(empty_clean("Everything matches the baseline."))
        else:
            H(empty("No settings match these filters"))

    with t_raw:
        r1, r2 = st.columns(2)
        base_title = "baseline" if s["mode"] == "custom" else "standard baseline"
        r1.markdown(f'<div class="code-title">{base_title} <span class="muted">· approved</span></div>' +
                    raw_json(s["baseline"], s["findings"]), unsafe_allow_html=True)
        r2.markdown(f'<div class="code-title">{esc(s["name"])} <span class="muted">· observed</span></div>' +
                    raw_json(s["current"], s["findings"]), unsafe_allow_html=True)
        H('<p class="hint">Highlighted lines differ from the baseline. SSH files are shown as normalised settings.</p>')


def page_remediation():
    H('<div class="res-head"><div class="eyebrow">Remediation</div><h1 style="font-family:inherit">Review proposed fixes</h1>'
      '<p class="sub muted" style="margin-top:8px">Approving records your decision only. Nothing is changed on any server.</p></div>')
    if need_run("Nothing to review yet", "Once a comparison finds drift, proposed fixes will be listed here."):
        return
    n = {"Pending": 0, "Approved": 0, "Rejected": 0}
    for f in T["all"]:
        n[dstatus(f["id"])] += 1
    H('<div class="mini-row">' + "".join(f'<div class="mini"><b>{v}</b><span class="muted">{k}</span></div>'
                                          for k, v in n.items()) + "</div>")
    if not T["all"]:
        H(empty_clean("There are no findings to remediate."))
        return
    flt = st.selectbox("Status", ["All", "Pending", "Approved", "Rejected"], key="f_rem")
    order = {"Pending": 0, "Approved": 1, "Rejected": 2}
    rows = [f for f in T["all"] if flt == "All" or dstatus(f["id"]) == flt]
    rows.sort(key=lambda f: (order[dstatus(f["id"])], RISK_ORDER[f["risk"]]))
    if not rows:
        H(empty("Nothing to show", "No findings match this status."))
        return
    out = []
    for f in rows:
        d = ss.decisions.get(f["id"], {})
        out.append([f'{esc(label(f["setting"]))}<span class="key">{esc(f_expected(f))} → {esc(f_actual(f))}</span>',
                    risk_badge(f["risk"]), status_badge(dstatus(f["id"])), esc(d.get("by", "—")),
                    fmt_date(d["at"]) if d.get("at") else "—",
                    f'<span class="muted">{esc(d.get("note") or "—")}</span>', review_btn(f["id"], "rem")])
    table("rem", [2.4, 1, 1.1, 0.9, 1.4, 2, 1], ["Setting", "Risk", "Status", "Decided by", "When", "Note", ""], out)


def print_report_html() -> str:
    parts = [f'<div class="print-report"><h1>Configuration Drift Report</h1><p>Generated {datetime.now():%d %b %Y, %I:%M %p} · '
             f'{T["total"]} drifts (High {T["c"]["High"]}, Medium {T["c"]["Medium"]}, Low {T["c"]["Low"]}) '
             f'· posture {T["posture"]}/100</p>']
    for s in A:
        parts.append(f'<h2>{esc(s["name"])} vs {esc(s["base_label"])}</h2>')
        if s["findings"]:
            parts.append("<table><thead><tr><th>Setting</th><th>Change</th><th>Expected</th><th>Actual</th><th>Risk</th><th>Status</th></tr></thead><tbody>" +
                         "".join(f'<tr><td>{esc(label(f["setting"]))}</td><td>{TYPE_LABEL[f["type"]]}</td><td>{esc(f_expected(f))}</td>'
                                 f'<td>{esc(f_actual(f))}</td><td>{f["risk"]}</td><td>{dstatus(f["id"])}</td></tr>' for f in s["findings"]) +
                         "</tbody></table>")
        else:
            parts.append("<p>No drift detected.</p>")
    parts.append("<p style='margin-top:14pt;font-size:9pt'>Detection and risk are rule-based. AI only explains verified findings. A person approves every fix.</p></div>")
    return "".join(parts)


def page_reports():
    H('<div class="res-head"><div class="eyebrow">Reports</div><h1 style="font-family:inherit">Export and history</h1>'
      '<p class="sub muted" style="margin-top:8px">Download the current findings and review earlier comparisons from this session.</p></div>')
    if need_run("No reports yet", "Run a comparison first, then export it here as JSON, CSV or PDF."):
        return
    with st.container(key="card_download"):
        H('<div class="card-title" style="margin:0">Download report</div>')
        st.caption("Includes every finding, its risk, and your approval decisions.")
        d1, d2, d3, _ = st.columns([1, 1, 1.6, 3])
        d1.download_button("JSON", json.dumps(report_data(A, ss.decisions), indent=2, default=str),
                           "drift_report.json", "application/json", icon=":material/download:", key="dl_json")
        d2.download_button("CSV", report_csv(A, ss.decisions), "drift_report.csv", "text/csv",
                           icon=":material/download:", key="dl_csv")
        if d3.button("Print / save as PDF", icon=":material/print:", key="print_btn"):
            ss.do_print = True
    st.write("")
    body = "".join(
        f'<tr><td>{fmt_date(p["time"])}</td><td><span class="mono">{esc(p["name"])}</span></td><td>{esc(p["against"])}</td>'
        f'<td class="num"><b>{p["drifts"]}</b></td><td class="num">{p["high"]}</td><td class="num">{p["score"]}</td></tr>'
        for p in reversed(ss.history))
    H('<div class="card-title">Comparisons this session</div><div class="table-wrap"><table>'
      '<thead><tr><th>Time</th><th>File</th><th>Compared with</th><th class="num">Drifts</th><th class="num">High</th>'
      f'<th class="num">Score</th></tr></thead><tbody>{body}</tbody></table></div>')
    if len(ss.history) > 1:
        st.write("")
        with st.container(key="card_trend"):
            H('<div class="card-title">Drift trend <small>Total drifts per comparison</small></div>' + trend(ss.history))
    st.markdown(print_report_html(), unsafe_allow_html=True)
    if ss.pop("do_print", False):
        components.html("<script>window.parent.print()</script>", height=0)


# ================================================================= review drawer
@st.cache_data(show_spinner=False)
def cached_explanation(f: dict) -> dict:
    return explain(f)


@st.dialog("Finding details", width="large")
def review_dialog(fid: str):
    hit = BY_ID.get(fid)
    if not hit:
        st.write("This finding is no longer available.")
        return
    f, s = hit
    with st.spinner("Loading explanation…"):
        exp = cached_explanation({k: f[k] for k in ("setting", "type", "expected", "actual", "risk")})
    d = ss.decisions.get(fid)
    e_chip, a_chip = finding_chips(f)
    after = '<span class="chip none">remove setting</span>' if f["type"] == "added" else e_chip
    H(f'<div class="drawer-head"><div class="eyebrow">{esc(s["name"])}</div><h2>{esc(label(f["setting"]))}</h2>'
      f'<code>{esc(f["setting"])}</code></div>'
      f'<div class="badges">{risk_badge(f["risk"])}{type_badge(f["type"])}{status_badge(dstatus(fid))}</div>'
      '<div class="sec" style="margin-top:0">Evidence<span class="tag tag-rule">Rule-based</span></div>'
      f'<div class="evidence"><div class="box"><div class="lbl">Expected (baseline)</div>{e_chip}</div><div class="arr">→</div>'
      f'<div class="box"><div class="lbl">Actual (observed)</div>{a_chip}</div></div>'
      '<div class="sec">Before / after fix</div>'
      f'<div class="evidence"><div class="box"><div class="lbl">Now</div>{a_chip}</div><div class="arr">→</div>'
      f'<div class="box"><div class="lbl">After fix</div>{after}</div></div>'
      '<p class="hint">Proposed state only. Nothing is changed on the server.</p>'
      f'<div class="sec">Explanation<span class="tag tag-ai">{esc(exp["source"])}</span></div>'
      f'<div class="exp-block"><h4>Why it matters</h4><p>{rich(exp["why_it_matters"])}</p></div>'
      f'<div class="exp-block"><h4>Impact</h4><p>{rich(exp["impact"])}</p></div>'
      f'<div class="exp-block"><h4>Suggested fix</h4><div class="fixbox">{rich(exp["suggested_fix"])}</div></div>')
    st.divider()
    if not d:
        H('<div class="sec" style="margin-top:0">Your decision</div>')
        st.text_area("Note", key=f"note_{fid}", placeholder="Optional note (why you approve or reject)",
                     label_visibility="collapsed")
        b1, b2 = st.columns(2)
        if b1.button("Approve fix", type="primary", key=f"ap_{fid}"):
            decide(fid, "Approved")
        if b2.button("Reject", key=f"rj_{fid}"):
            decide(fid, "Rejected")
        H('<p class="hint">Approving only records your decision. The tool never changes a server.</p>')
    else:
        note = f'<p style="margin-top:8px">“{esc(d["note"])}”</p>' if d.get("note") else ""
        H(f'<div class="sec" style="margin-top:0">Your decision</div><div class="decided">{status_badge(d["status"])} '
          f'by <b>{esc(d["by"])}</b> · {fmt_date(d["at"])}{note}</div>')
        if st.button("Reopen", key=f"ro_{fid}"):
            decide(fid, "Pending")


# ================================================================= router
{"compare": page_compare, "findings": page_findings, "remediation": page_remediation,
 "reports": page_reports}.get(ss.page, page_compare)()
H(FOOTER)

rid = ss.pop("review_id", None)
if rid:
    review_dialog(rid)
