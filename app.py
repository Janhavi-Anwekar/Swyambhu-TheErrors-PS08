"""Config Drift Detector — Streamlit + Python version of the website.

Run:  streamlit run app.py
Files: core.py (logic) · data.py (mock data) · explain.py (AI) · ui.py (HTML/CSS helpers)
"""
import json
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from core import (RISK_ORDER, TYPE_LABEL, analyze, f_actual, f_expected, history_points, label,
                  report_csv, report_data, summary, totals)
from data import get_mock_history, get_mock_servers
from explain import explain
from ui import (BRAND, CSS, DOT, FOOTER, SIDE_NOTE, chip, donut, empty, empty_clean, esc, finding_chips,
                fmt_date, kpi, page_head, raw_json, rich, ring, risk_badge, stacked_bar, status_badge,
                status_dot, time_ago, trend, type_badge)

st.set_page_config(page_title="Config Drift Detector", page_icon="🛡️", layout="wide",
                   initial_sidebar_state="expanded")
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

ss = st.session_state
DEC_FILE = Path(__file__).with_name("decisions.json")
PAGES = {"overview": "Overview", "servers": "Servers", "remediation": "Remediation",
         "reports": "Reports & History", "server": "Server"}


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
    qp_page = st.query_params.get("page", "overview")
    ss.page = qp_page if qp_page in PAGES else "overview"
    ss.sid = st.query_params.get("sid")
    ss.servers = get_mock_servers()
    ss.history = get_mock_history()
    ss.uploaded = None
    ss.decisions = load_decisions()
    ss.last_run = datetime.now()
    ss.review_id = None
    ss.upload_msg = ""


def go(page: str, sid: str | None = None):
    ss.page, ss.sid = page, sid
    st.query_params["page"] = page
    if sid:
        st.query_params["sid"] = sid
    elif "sid" in st.query_params:
        del st.query_params["sid"]


def on_search():
    if ss.page != "servers":
        go("servers")


def clear_search():
    ss.search = ""


def rerun_comparison():
    ss.last_run = datetime.now()
    ss.flash = "Comparison re-run complete"


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


# ================================================================= data
def all_servers():
    return ss.servers + ([ss.uploaded] if ss.uploaded else [])


A = [analyze(s) for s in all_servers()]
T = totals(A)
PENDING = sum(1 for f in T["all"] if dstatus(f["id"]) == "Pending")
BY_ID = {f["id"]: (f, s) for s in A for f in s["findings"]}

if ss.get("flash"):
    st.toast(ss.pop("flash"))


# ================================================================= table helper
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


def link_btn(text: str, key: str, page: str, sid: str | None, sub: str = ""):
    def _draw():
        st.button(text, key=f"link_{key}", on_click=go, args=(page, sid))
        if sub:
            H(f'<span class="key">{esc(sub)}</span>')
    return _draw


def review_btn(fid: str, ctx: str):
    def _draw():
        st.button("Review", key=f"rev_{ctx}_{fid}", on_click=open_review, args=(fid,))
    return _draw


# ================================================================= sidebar
active = "servers" if ss.page == "server" else ss.page
dyn = (f".st-key-nav_{active} button{{background:#EEF2FF!important;color:#3730A3!important;font-weight:600!important}}")
if PENDING:
    dyn += (f'.st-key-nav_remediation button::after{{content:"{PENDING}";margin-left:auto;background:#4F46E5;color:#fff;'
            "border-radius:999px;font-size:.72rem;font-weight:600;padding:1px 8px}")
st.markdown(f"<style>{dyn}</style>", unsafe_allow_html=True)

with st.sidebar:
    H(BRAND)
    for key, text, icon in [("overview", "Overview", ":material/space_dashboard:"),
                            ("servers", "Servers", ":material/dns:"),
                            ("remediation", "Remediation", ":material/task_alt:"),
                            ("reports", "Reports & History", ":material/description:")]:
        st.button(text, key=f"nav_{key}", icon=icon, on_click=go, args=(key,))
    H(SIDE_NOTE)
    import os
    live = bool(os.getenv("ANTHROPIC_API_KEY"))
    H('<div class="side-ai">Explanations: ' + ("<b>live AI</b>" if live else "offline demo text. Set ANTHROPIC_API_KEY for live AI.") + "</div>")

# ================================================================= top bar
with st.container(key="topbar"):
    c1, c2, c3 = st.columns([5, 1.6, 2.2], vertical_alignment="center")
    c1.text_input("Search", key="search", placeholder="Search servers, environments, settings…",
                  label_visibility="collapsed", on_change=on_search, icon=":material/search:")
    c2.markdown('<div class="reviewer">Reviewer: <b>You</b></div>', unsafe_allow_html=True)
    c3.button("Re-run comparison", key="rerun", icon=":material/refresh:", type="primary",
              on_click=rerun_comparison)

try:  # the design needs Streamlit's light theme
    if st.context.theme.type == "dark":
        st.warning("For the intended look, run with the light theme: put the .streamlit/config.toml file "
                   "next to app.py (see instructions), or choose Settings → Theme → Light.")
except Exception:
    pass


# ================================================================= pages
def page_overview():
    H(page_head("Security overview",
                f"{len(A)} servers monitored · last comparison {ss.last_run.strftime('%I:%M %p')}"))
    cols = st.columns(5)
    cards = [kpi("Servers monitored", str(len(A)), "across prod, staging, dev"),
             kpi("Healthy vs affected", f'{T["healthy"]} <span class="muted" style="font-weight:500">/</span> {T["affected"]}',
                 f'{T["healthy"]} clean · {T["affected"]} with drift')]
    for r in ("High", "Medium", "Low"):
        n = T["c"][r]
        cards.append(kpi(f"{r} risk", str(n), "finding" + ("" if n == 1 else "s"), DOT[r]))
    for c, card in zip(cols, cards):
        c.markdown(card, unsafe_allow_html=True)
    st.write("")

    with st.container(key="grid3"):
        ca, cb, cc = st.columns([1, 1, 1.4])
        with ca:
            H('<div class="card center"><div class="card-title">Security posture</div>' + ring(T["posture"]) +
              '<p class="formula">Average of server scores. Each score = 100 − 15 per High − 7 per Medium − 2 per Low.</p></div>')
        with cb:
            leg = "".join(f'<span><i style="background:{DOT[r]}"></i>{r} {T["c"][r]}</span>' for r in ("High", "Medium", "Low"))
            H('<div class="card center"><div class="card-title">Risk distribution</div>' + donut(T["c"], T["total"]) +
              f'<div class="legend">{leg}</div></div>')
        with cc:
            with st.container(key="card_bars"):
                H('<div class="card-title" style="margin:0 0 8px">Drifts per server</div>')
                mx = max([1] + [len(s["findings"]) for s in A])
                for s in sorted(A, key=lambda s: -len(s["findings"])):
                    b1, b2, b3 = st.columns([2, 3, 0.4], vertical_alignment="center")
                    with b1:
                        link_btn(s["name"], f"bar_{s['id']}", "server", s["id"])()
                    b2.markdown(stacked_bar(s["findings"], mx), unsafe_allow_html=True)
                    b3.markdown(f'<div class="bar-n">{len(s["findings"])}</div>', unsafe_allow_html=True)
    st.write("")

    with st.container(key="card_recent"):
        H('<div class="card-title" style="margin:0">Recent changes <small>Highest risk first</small></div>')
        top = sorted(T["all"], key=lambda f: RISK_ORDER[f["risk"]])[:6]
        if not top:
            H(empty_clean("Every server matches its approved baseline."))
        for i, f in enumerate(top):
            s = BY_ID[f["id"]][1]
            with st.container(key=f"rrow_{i}"):
                r1, r2, r3, r4 = st.columns([0.9, 5, 1.1, 0.9], vertical_alignment="center")
                r1.markdown(risk_badge(f["risk"]), unsafe_allow_html=True)
                r2.markdown(f'<div><div class="cell-title">{esc(summary(f))}</div>'
                            f'<div class="cell-sub"><span class="mono">{esc(s["name"])}</span> · detected {time_ago(s["last_scan"])}</div></div>',
                            unsafe_allow_html=True)
                r3.markdown(status_badge(dstatus(f["id"])), unsafe_allow_html=True)
                with r4:
                    review_btn(f["id"], "ov")()


def matches(s: dict, q: str) -> bool:
    if not q:
        return True
    hay = " ".join([s["name"], s["id"], s["environment"], s["os"], s["location"], s["status"]] +
                   [label(f["setting"]) + " " + f["setting"] for f in s["findings"]]).lower()
    return all(w in hay for w in q.lower().split())


def do_upload():
    a, b = ss.get("up_base"), ss.get("up_cur")
    if not a or not b:
        ss.upload_msg = "Please choose both files: baseline.json and current.json."
        return
    try:
        base, cur = json.loads(a.getvalue()), json.loads(b.getvalue())
    except Exception:
        ss.upload_msg = "One of the files is not valid JSON. Check for missing commas or quotes and try again."
        return
    if not isinstance(base, dict) or not isinstance(cur, dict):
        ss.upload_msg = 'Both files must contain a JSON object of settings, e.g. {"firewall_enabled": true}.'
        return
    ss.uploaded = dict(id="uploaded", name="uploaded-config", environment="dev", os="Not specified",
                       location="Local upload", status="unknown", last_scan=datetime.now(),
                       baseline=base, current=cur)
    ss.upload_msg = ""
    ss.flash = "Comparison complete"
    go("server", "uploaded")


def page_servers():
    H(page_head("Servers", "Select a server to inspect its configuration changes."))
    f1, f2, f3, f4 = st.columns([1, 1, 1, 2], vertical_alignment="bottom")
    env = f1.selectbox("Environment", ["All", "Prod", "Staging", "Dev"], key="f_env")
    stat = f2.selectbox("Status", ["All", "Online", "Offline", "Unknown"], key="f_status")
    rk = f3.selectbox("Highest risk", ["All", "High", "Medium", "Low", "Clean"], key="f_risk")
    if ss.get("search"):
        f4.button(f"Search: {ss.search}  ✕", key="clear_search", on_click=clear_search)

    q = ss.get("search", "").strip()
    rows = [s for s in A if matches(s, q)
            and (env == "All" or s["environment"] == env.lower())
            and (stat == "All" or s["status"] == stat.lower())
            and (rk == "All" or s["highest"] == ("None" if rk == "Clean" else rk))]
    if not rows:
        H('<div class="card">' + empty("No servers match", "Try clearing the search or filters.") + "</div>")
    else:
        table("servers", [2.2, 1.1, 1.8, 1.2, 1.1, 0.8, 1.3],
              ["Server", "Environment", "OS", "Status", "Last scan", "Drifts", "Highest risk"],
              [[link_btn(s["name"], f"srv_{s['id']}", "server", s["id"], s["location"]),
                f'<span class="pill">{esc(s["environment"])}</span>', esc(s["os"]), status_dot(s["status"]),
                time_ago(s["last_scan"]), f'<b>{len(s["findings"])}</b>', risk_badge(s["highest"])] for s in rows])

    st.write("")
    with st.container(key="card_upload"):
        H('<div class="card-title" style="margin:0">Compare your own files</div>')
        st.caption("Upload a baseline.json and a current.json (flat key/value settings) to run the same "
                   "comparison on your data. Files stay on this machine.")
        u1, u2, u3 = st.columns([2, 2, 1], vertical_alignment="bottom")
        u1.file_uploader("baseline.json (approved)", type="json", key="up_base")
        u2.file_uploader("current.json (observed)", type="json", key="up_cur")
        u3.button("Compare files", type="primary", on_click=do_upload, key="do_upload")
        if ss.upload_msg:
            st.error(ss.upload_msg)


def page_server():
    s = next((x for x in A if x["id"] == ss.sid), None)
    if not s:
        H('<div class="card">' + empty("Server not found", "Go back to the Servers page and pick one.") + "</div>")
        st.button("← All servers", on_click=go, args=("servers",), key="back_nf")
        return
    st.button("← All servers", on_click=go, args=("servers",), key="back")
    n = len(s["findings"])
    H(f'<div class="card" style="margin:6px 0 14px"><div class="server-head"><h1>{esc(s["name"])} {risk_badge(s["highest"])}</h1>'
      f'<div class="muted">{n} drift{"" if n == 1 else "s"} · score {s["score"]}/100</div></div>'
      '<dl class="meta">'
      f'<div><dt>Environment</dt><dd style="text-transform:capitalize">{esc(s["environment"])}</dd></div>'
      f'<div><dt>Operating system</dt><dd>{esc(s["os"])}</dd></div>'
      f'<div><dt>Location</dt><dd>{esc(s["location"])}</dd></div>'
      f'<div><dt>Status</dt><dd>{status_dot(s["status"])}</dd></div>'
      f'<div><dt>Last scan</dt><dd>{fmt_date(s["last_scan"])} ({time_ago(s["last_scan"])})</dd></div></dl></div>')

    t_explorer, t_summary, t_raw = st.tabs(["Drift explorer", "Summary", "Raw JSON"])

    with t_explorer:
        e1, e2, e3, _ = st.columns([1, 1, 1.6, 2], vertical_alignment="bottom")
        xr = e1.selectbox("Risk", ["All", "High", "Medium", "Low"], key="x_risk")
        xt = e2.selectbox("Change", ["All", "Modified", "Added", "Removed"], key="x_type")
        xu = e3.checkbox("Show unchanged settings", key="x_unch")
        keys = list(dict.fromkeys(list(s["baseline"]) + list(s["current"])))
        fmap = {f["setting"]: f for f in s["findings"]}
        rows = []
        for k in keys:
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
                  ["Setting", "Baseline (approved)", "Current (observed)", "Change", "Risk", "Review", ""], rows)
        elif not s["findings"] and xr == "All" and xt == "All":
            H('<div class="card">' + empty_clean("This server matches its approved baseline.") + "</div>")
        else:
            H('<div class="card">' + empty("No settings match these filters") + "</div>")

    with t_summary:
        c = {r: sum(1 for f in s["findings"] if f["risk"] == r) for r in ("High", "Medium", "Low")}
        mini = "".join(f'<div class="mini"><span class="dot" style="background:{DOT[r]}"></span><b>{c[r]}</b>'
                       f'<span class="muted">{r}</span></div>' for r in c)
        H(f'<div class="mini-row">{mini}<div class="mini"><span class="muted">Posture score</span>'
          f'<b>{s["score"]}</b><span class="muted">/ 100</span></div></div>')
        if not s["findings"]:
            H('<div class="card">' + empty_clean("This server matches its approved baseline.") + "</div>")
        else:
            table("summary", [1, 5, 1.2, 1], ["Risk", "Finding", "Review", ""],
                  [[risk_badge(f["risk"]),
                    f'<div><div class="cell-title">{esc(summary(f))}</div><div class="cell-sub">{TYPE_LABEL[f["type"]]} setting · '
                    f'<span class="mono">{esc(f["setting"])}</span></div></div>',
                    status_badge(dstatus(f["id"])), review_btn(f["id"], "sm")] for f in s["findings"]])

    with t_raw:
        r1, r2 = st.columns(2)
        r1.markdown('<div class="code-title">baseline.json <span class="muted">· approved</span></div>' +
                    raw_json(s["baseline"], s["findings"]), unsafe_allow_html=True)
        r2.markdown('<div class="code-title">current.json <span class="muted">· observed</span></div>' +
                    raw_json(s["current"], s["findings"]), unsafe_allow_html=True)
        H('<p class="hint">Highlighted lines differ from the baseline.</p>')


def page_remediation():
    H(page_head("Remediation", "Review proposed fixes. Approving records your decision only; nothing is changed on any server."))
    n = {"Pending": 0, "Approved": 0, "Rejected": 0}
    for f in T["all"]:
        n[dstatus(f["id"])] += 1
    H('<div class="mini-row">' + "".join(f'<div class="mini"><b>{v}</b><span class="muted">{k}</span></div>'
                                          for k, v in n.items()) + "</div>")
    flt = st.selectbox("Status", ["All", "Pending", "Approved", "Rejected"], key="f_rem")
    order = {"Pending": 0, "Approved": 1, "Rejected": 2}
    rows = [(f, s) for f in T["all"] for s in [BY_ID[f["id"]][1]] if flt == "All" or dstatus(f["id"]) == flt]
    rows.sort(key=lambda fs: (order[dstatus(fs[0]["id"])], RISK_ORDER[fs[0]["risk"]]))
    if not rows:
        H('<div class="card">' + empty("Nothing to show", "No findings match this status.") + "</div>")
        return
    out = []
    for f, s in rows:
        d = ss.decisions.get(f["id"], {})
        out.append([link_btn(s["name"], f"rem_{f['id']}", "server", s["id"]),
                    f'{esc(label(f["setting"]))}<span class="key">{esc(f_expected(f))} → {esc(f_actual(f))}</span>',
                    risk_badge(f["risk"]), status_badge(dstatus(f["id"])), esc(d.get("by", "—")),
                    fmt_date(d["at"]) if d.get("at") else "—",
                    f'<span class="muted">{esc(d.get("note") or "—")}</span>', review_btn(f["id"], "rem")])
    table("rem", [1.6, 2.2, 1, 1.1, 0.9, 1.4, 2, 1],
          ["Server", "Setting", "Risk", "Status", "Decided by", "When", "Note", ""], out)


def print_report_html() -> str:
    parts = [f'<div class="print-report"><h1>Configuration Drift Report</h1><p>Generated {datetime.now():%d %b %Y, %I:%M %p} · '
             f'{len(A)} servers · {T["total"]} drifts (High {T["c"]["High"]}, Medium {T["c"]["Medium"]}, Low {T["c"]["Low"]}) '
             f'· posture {T["posture"]}/100</p>']
    for s in A:
        parts.append(f'<h2>{esc(s["name"])} · {esc(s["environment"])} · {"Clean" if s["highest"] == "None" else s["highest"]}</h2>')
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
    H(page_head("Reports & history", "Export the current findings and compare with earlier scans."))
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
    pts = history_points(ss.history, A)
    left, right = st.columns(2)
    with left:
        H('<div class="card"><div class="card-title">Drift trend <small>Total drifts per scan</small></div>' + trend(pts) + "</div>")
    with right:
        body = "".join(
            f'<tr><td>{fmt_date(p["time"])}{' <span class="badge s-Approved">Current</span>' if i == 0 else ""}</td>'
            f'<td class="num">{p["servers"]}</td><td class="num"><b>{p["drifts"]}</b></td><td class="num">{p["high"]}</td></tr>'
            for i, p in enumerate(reversed(pts)))
        H('<div class="card"><div class="card-title">Scan history</div><div class="table-wrap" style="box-shadow:none"><table>'
          '<thead><tr><th>Scan time</th><th class="num">Servers</th><th class="num">Drifts</th><th class="num">High</th></tr></thead>'
          f"<tbody>{body}</tbody></table></div></div>")
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
{"overview": page_overview, "servers": page_servers, "server": page_server,
 "remediation": page_remediation, "reports": page_reports}.get(ss.page, page_overview)()
H(FOOTER)

rid = ss.pop("review_id", None)
if rid:
    review_dialog(rid)
