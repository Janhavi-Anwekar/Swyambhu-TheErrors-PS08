"""UI helpers: HTML snippets, SVG charts and CSS (same look as the HTML website).

Everything here returns SINGLE-LINE html strings (no blank lines / indentation), because
st.markdown would otherwise treat indented lines as code blocks.
"""
import html
import json
from datetime import datetime

from core import (DOT, TYPE_LABEL, f_actual, f_expected, label, plain)


# ---------------------------------------------------------------- small helpers
def esc(s) -> str:
    return html.escape("" if s is None else str(s), quote=True).replace("$", "&#36;")


def rich(text: str) -> str:
    """Escape, then turn `code` into <code>."""
    out, parts = [], esc(text).split("`")
    for i, p in enumerate(parts):
        out.append(f"<code>{p}</code>" if i % 2 else p)
    return "".join(out)


def time_ago(dt: datetime) -> str:
    s = (datetime.now() - dt).total_seconds()
    if s < 60:
        return "just now"
    m = s / 60
    if m < 60:
        return f"{round(m)} min ago"
    h = m / 60
    if h < 24:
        return f"{round(h)} h ago"
    return f"{round(h / 24)} d ago"


def fmt_date(dt) -> str:
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    return dt.strftime("%b %d, %I:%M %p")


def risk_badge(r: str) -> str:
    return f'<span class="badge {r}"><i></i>{"Clean" if r == "None" else r}</span>'


def type_badge(t: str) -> str:
    return f'<span class="badge t-{t}">{TYPE_LABEL[t]}</span>'


def status_badge(s: str) -> str:
    return f'<span class="badge s-{s}">{s}</span>'


def status_dot(s: str) -> str:
    return f'<span class="status {s}"><i></i>{s.capitalize()}</span>'


def chip(value, cls: str = "", present: bool = True) -> str:
    if not present:
        return '<span class="chip none">not set</span>'
    return f'<span class="chip {cls}">{esc(plain(value))}</span>'


def finding_chips(f):
    """(expected_chip, actual_chip) for a finding."""
    return (chip(f["expected"], "", f["type"] != "added"),
            chip(f["actual"], "t-" + f["type"], f["type"] != "removed"))


def page_head(title: str, sub: str) -> str:
    return f'<div class="page-head"><div><h1>{esc(title)}</h1><p class="sub">{esc(sub)}</p></div></div>'


def kpi(title: str, value: str, sub: str, dot: str = "") -> str:
    d = f'<i style="background:{dot}"></i>' if dot else ""
    return (f'<div class="kpi"><div class="kpi-k">{d}{title}</div>'
            f'<div class="kpi-v">{value}</div><div class="kpi-s">{sub}</div></div>')


def empty_clean(msg: str) -> str:
    return ('<div class="empty"><div class="big"><svg width="26" height="26" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
            '<circle cx="12" cy="12" r="9"/><path d="M9 12l2 2 4-4"/></svg></div>'
            f'<h3>No drift detected</h3><p>{esc(msg)}</p></div>')


def empty(title: str, msg: str = "") -> str:
    return f'<div class="empty"><h3>{esc(title)}</h3><p>{esc(msg)}</p></div>'


# ---------------------------------------------------------------- SVG charts
def ring(score: int) -> str:
    import math
    C = 2 * math.pi * 56
    col = DOT["Low"] if score >= 80 else DOT["Medium"] if score >= 50 else DOT["High"]
    return (f'<svg class="ring" viewBox="0 0 140 140" role="img" aria-label="Posture score {score} out of 100">'
            '<circle cx="70" cy="70" r="56" fill="none" stroke="#EEF1F6" stroke-width="12"/>'
            f'<circle cx="70" cy="70" r="56" fill="none" stroke="{col}" stroke-width="12" stroke-linecap="round" '
            f'stroke-dasharray="{C * score / 100:.2f} {C:.2f}" transform="rotate(-90 70 70)"/>'
            f'<text x="70" y="74" text-anchor="middle" class="r-num">{score}</text>'
            '<text x="70" y="94" text-anchor="middle" class="r-lbl">out of 100</text></svg>')


def donut(c: dict, total: int) -> str:
    import math
    R = 60
    C = 2 * math.pi * R
    off, segs = 0.0, ""
    for r in ("High", "Medium", "Low"):
        ln = C * c[r] / total if total else 0
        if ln:
            segs += (f'<circle cx="80" cy="80" r="{R}" fill="none" stroke="{DOT[r]}" stroke-width="20" '
                     f'stroke-dasharray="{ln:.2f} {C - ln:.2f}" stroke-dashoffset="{-off:.2f}" '
                     'transform="rotate(-90 80 80)"/>')
        off += ln
    return (f'<svg class="donut" viewBox="0 0 160 160" role="img" aria-label="{c["High"]} high, {c["Medium"]} medium, {c["Low"]} low findings">'
            '<circle cx="80" cy="80" r="60" fill="none" stroke="#EEF1F6" stroke-width="20"/>' + segs +
            f'<text x="80" y="82" text-anchor="middle" class="d-num">{total}</text>'
            '<text x="80" y="100" text-anchor="middle" class="d-lbl">findings</text></svg>')


def trend(points: list[dict]) -> str:
    W, H, P = 460, 150, 28
    mx = max([1] + [p["drifts"] for p in points])
    n = len(points)
    x = lambda i: P + (W - 2 * P) * (0.5 if n == 1 else i / (n - 1))
    y = lambda v: H - P - (H - 2 * P) * v / mx
    line = " ".join(f"{x(i):.1f},{y(p['drifts']):.1f}" for i, p in enumerate(points))
    dots = "".join(
        f'<circle cx="{x(i):.1f}" cy="{y(p["drifts"]):.1f}" r="4" fill="#4F46E5"/>'
        f'<text x="{x(i):.1f}" y="{y(p["drifts"]) - 10:.1f}" text-anchor="middle" font-size="11" fill="#334155" font-weight="600">{p["drifts"]}</text>'
        for i, p in enumerate(points))
    labels = "".join(
        f'<text x="{x(i):.1f}" y="{H - 6}" text-anchor="middle" font-size="10" fill="#64748B">'
        f'{"Now" if i == n - 1 else p["time"].strftime("%d %b")}</text>' for i, p in enumerate(points))
    return (f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Drift count over recent scans">'
            f'<line x1="{P}" y1="{H - P}" x2="{W - P}" y2="{H - P}" stroke="#E5E9F2"/>'
            f'<polyline points="{line}" fill="none" stroke="#4F46E5" stroke-width="2.5" stroke-linejoin="round"/>'
            f'{dots}{labels}</svg>')


def stacked_bar(findings: list[dict], max_n: int) -> str:
    seg = ""
    for r in ("High", "Medium", "Low"):
        n = sum(1 for f in findings if f["risk"] == r)
        if n:
            seg += f'<span style="width:{n / max_n * 100:.1f}%;background:{DOT[r]}" title="{n} {r}"></span>'
    return f'<div class="bar-track">{seg}</div>'


def raw_json(obj: dict, drifts: list[dict]) -> str:
    by = {d["setting"]: d["type"] for d in drifts}
    keys = list(obj)
    lines = ""
    for i, k in enumerate(keys):
        val = json.dumps(obj[k]).replace(",", ", ")
        txt = f'  "{k}": {val}' + ("," if i < len(keys) - 1 else "")
        cls = f" d-{by[k]}" if k in by else ""
        lines += f'<span class="ln{cls}">{esc(txt)}</span>'
    return f'<div class="code"><span class="ln">{{</span>{lines}<span class="ln">}}</span></div>'


# ---------------------------------------------------------------- brand + static blocks
BRAND = ('<div class="brand"><span class="logo"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" '
         'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
         '<path d="M12 3l8 3v6c0 4.5-3.2 8.2-8 9-4.8-.8-8-4.5-8-9V6z"/><path d="M9 12l2 2 4-4"/></svg></span>'
         '<div><div class="brand-name">Drift Detector</div><div class="brand-sub">Configuration security</div></div></div>')

SIDE_NOTE = ('<div class="side-note"><b>How it works</b><br>Rules find and rate every change. '
             'AI only explains them. You approve every fix.</div>')

FOOTER = ('<div class="foot">Detection and risk are rule-based. AI only explains verified findings. '
          'A person approves every fix.</div>')

# ---------------------------------------------------------------- CSS
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
:root{--bg:#F5F7FB;--surface:#fff;--ink:#0F172A;--ink-2:#334155;--muted:#64748B;--line:#E5E9F2;--line-2:#EEF1F6;--hover:#F8FAFC;
--accent:#4F46E5;--accent-600:#4338CA;--accent-50:#EEF2FF;--accent-100:#E0E7FF;--accent-ink:#3730A3;
--high:#B42318;--high-bg:#FEF3F2;--high-line:#FECDCA;--medium:#B54708;--medium-bg:#FFFAEB;--medium-line:#FEDF89;--low:#067647;--low-bg:#ECFDF3;--low-line:#ABEFC6;
--t-modified:#1D4ED8;--t-modified-bg:#EFF6FF;--t-added:#0F766E;--t-added-bg:#F0FDFA;--t-removed:#6D28D9;--t-removed-bg:#F5F3FF;
--radius:14px;--radius-sm:10px;--shadow:0 1px 2px rgba(16,24,40,.05),0 1px 3px rgba(16,24,40,.04);
--mono:'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;--sans:'Inter',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}
html,body,[class*="st-"],.stApp{font-family:var(--sans)}
[data-testid="stIconMaterial"],span[class*="material"],[data-testid="stSidebarCollapseButton"] span,[data-testid="stSidebarCollapsedControl"] span{font-family:'Material Symbols Rounded','Material Symbols Outlined'!important}
.stApp{background:var(--bg);color:var(--ink)}
[data-testid="stMainBlockContainer"]{max-width:1240px;padding:1.2rem 28px 3rem}
[data-testid="stToolbar"],[data-testid="stDecoration"],.stDeployButton,#MainMenu,footer{display:none!important}
header[data-testid="stHeader"]{background:transparent}
h1,h2,h3,h4,p{margin:0}
code{font-family:var(--mono)}
.muted{color:var(--muted)}

/* ---------- sidebar ---------- */
section[data-testid="stSidebar"]{background:#fff;border-right:1px solid var(--line);width:252px!important;min-width:252px!important}
section[data-testid="stSidebar"] [data-testid="stSidebarContent"]{padding:0 6px}
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"]{padding:14px 8px 20px}
.brand{display:flex;align-items:center;gap:12px;padding:6px 8px 20px}
.logo{width:38px;height:38px;border-radius:11px;background:var(--accent);color:#fff;display:grid;place-items:center}
.brand-name{font-weight:700;font-size:1rem;letter-spacing:-.01em;color:var(--ink)}
.brand-sub{color:var(--muted);font-size:.75rem}
section[data-testid="stSidebar"] .stButton>button{width:100%;justify-content:flex-start;background:transparent;border:0;box-shadow:none;
 color:var(--ink-2);font-weight:500;padding:.6rem .75rem;border-radius:var(--radius-sm);gap:.6rem}
section[data-testid="stSidebar"] .stButton>button:hover{background:var(--hover);color:var(--ink)}
section[data-testid="stSidebar"] .stButton>button p{font-size:.95rem}
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:.25rem}
.stApp .side-ai{color:var(--muted);font-size:.74rem;margin:10px 4px 0;line-height:1.45}
.stApp .side-note{margin-top:2rem;background:var(--hover);border:1px solid var(--line);border-radius:var(--radius-sm);padding:12px 14px;font-size:.78rem;color:var(--muted);line-height:1.55}
.side-note b{color:var(--ink-2)}

/* ---------- top bar ---------- */
.st-key-topbar{background:rgba(245,247,251,.95);border-bottom:1px solid var(--line);padding:6px 0 14px;margin-bottom:18px}
.st-key-topbar [data-testid="stTextInput"] input{background:#fff;border-radius:var(--radius-sm)}
.stApp .reviewer{color:var(--muted);font-size:.85rem;text-align:right}
.reviewer b{color:var(--ink-2)}

/* ---------- page heads / cards ---------- */
.page-head{margin-bottom:6px}
.stApp .page-head h1{font-size:1.6rem;letter-spacing:-.02em;font-weight:700;padding:0;color:var(--ink)}
.stApp .sub{color:var(--muted);margin-top:4px}
.card{background:#fff;border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow);padding:20px 22px;height:100%}
.card-title{font-size:.95rem;font-weight:650;margin-bottom:14px;display:flex;justify-content:space-between;align-items:center;gap:10px}
.card-title small{color:var(--muted);font-weight:500;font-size:.78rem}
[class*="st-key-card_"]{background:#fff;border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow);padding:20px 22px!important;gap:.6rem}
.kpi{background:#fff;border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow);padding:16px 18px}
.kpi-k{color:var(--muted);font-size:.72rem;font-weight:600;text-transform:uppercase;letter-spacing:.07em;display:flex;align-items:center;gap:8px}
.kpi-k i{width:8px;height:8px;border-radius:50%;display:inline-block}
.kpi-v{font-size:1.9rem;font-weight:700;letter-spacing:-.02em;margin-top:6px;line-height:1.1;color:var(--ink)}
.kpi-s{color:var(--muted);font-size:.8rem;margin-top:4px}
.card.center,.st-key-card_bars{min-height:330px}
.center{display:flex;flex-direction:column;align-items:center;text-align:center}
.center .card-title{width:100%}
.ring,.donut{width:160px;height:160px}
.ring text.r-num{font-size:34px;font-weight:700;fill:var(--ink)}
.ring text.r-lbl,.donut text.d-lbl{font-size:11px;fill:var(--muted)}
.donut text.d-num{font-size:30px;font-weight:700;fill:var(--ink)}
.legend{display:flex;gap:14px;flex-wrap:wrap;justify-content:center;margin-top:10px;color:var(--ink-2);font-size:.82rem}
.legend i{width:9px;height:9px;border-radius:50%;display:inline-block;margin-right:6px}
.stApp .formula{color:var(--muted);font-size:.75rem;margin-top:10px;max-width:220px}
.bar-track{background:var(--line-2);border-radius:999px;height:12px;display:flex;overflow:hidden}
.bar-track span{display:block;height:100%}
.stApp .bar-n{text-align:right;font-weight:600;color:var(--ink)}
.st-key-grid3 [data-testid="stHorizontalBlock"]{align-items:stretch}
.st-key-grid3 [data-testid="stColumn"]>div,.st-key-grid3 [data-testid="stColumn"] [data-testid="stVerticalBlock"],.st-key-grid3 [data-testid="stColumn"] [data-testid="stElementContainer"]{height:100%}
.st-key-grid3 [data-testid="stColumn"] [data-testid="stElementContainer"]{display:flex;flex-direction:column}

/* ---------- badges / chips ---------- */
.badge{display:inline-flex;align-items:center;gap:6px;padding:2px 10px;border-radius:999px;font-size:.74rem;font-weight:600;border:1px solid transparent;white-space:nowrap}
.badge i{width:7px;height:7px;border-radius:50%;display:inline-block}
.badge.High{background:var(--high-bg);color:var(--high);border-color:var(--high-line)}.badge.High i{background:#F04438}
.badge.Medium{background:var(--medium-bg);color:var(--medium);border-color:var(--medium-line)}.badge.Medium i{background:#F79009}
.badge.Low,.badge.None{background:var(--low-bg);color:var(--low);border-color:var(--low-line)}.badge.Low i,.badge.None i{background:#12B76A}
.badge.t-modified{background:var(--t-modified-bg);color:var(--t-modified)}
.badge.t-added{background:var(--t-added-bg);color:var(--t-added)}
.badge.t-removed{background:var(--t-removed-bg);color:var(--t-removed)}
.badge.t-same{background:var(--hover);color:var(--muted);border-color:var(--line)}
.badge.s-Pending{background:var(--hover);color:var(--ink-2);border-color:var(--line)}
.badge.s-Approved{background:var(--accent-50);color:var(--accent-ink);border-color:var(--accent-100)}
.badge.s-Rejected{background:#F1F5F9;color:#475569;border-color:#CBD5E1}
.pill{display:inline-block;padding:2px 10px;border-radius:6px;font-size:.74rem;font-weight:600;background:var(--hover);border:1px solid var(--line);color:var(--ink-2);text-transform:capitalize}
.status{display:inline-flex;align-items:center;gap:7px;color:var(--ink-2)}
.status i{width:8px;height:8px;border-radius:50%;display:inline-block}
.status.online i{background:var(--accent)}.status.offline i{background:#94A3B8}.status.unknown i{background:transparent;border:2px solid #94A3B8}
.chip{font-family:var(--mono);font-size:.8rem;padding:3px 9px;border-radius:7px;border:1px solid var(--line);background:#F1F5F9;color:var(--ink-2);display:inline-block}
.chip.none{background:transparent;border-style:dashed;color:var(--muted);font-style:italic}
.chip.t-modified{background:var(--t-modified-bg);color:var(--t-modified);border-color:#BFDBFE}
.chip.t-added{background:var(--t-added-bg);color:var(--t-added);border-color:#99F6E4}
.chip.t-removed{background:var(--t-removed-bg);color:var(--t-removed);border-color:#DDD6FE}
.tag{font-size:.68rem;font-weight:700;letter-spacing:.05em;text-transform:uppercase;padding:2px 8px;border-radius:6px;margin-left:8px;vertical-align:2px}
.tag-rule{background:var(--hover);color:var(--ink-2);border:1px solid var(--line)}
.tag-ai{background:var(--accent-50);color:var(--accent-ink);border:1px solid var(--accent-100)}
.key{display:block;font-family:var(--mono);font-size:.72rem;color:var(--muted)}
.stApp .cell-title{font-weight:600;color:var(--ink)}
.stApp .cell-sub{color:var(--muted);font-size:.82rem}
.mono{font-family:var(--mono)}
.stApp .empty{text-align:center;padding:44px 20px;color:var(--muted)}
.stApp .empty h3{color:var(--ink);font-size:1.05rem;margin-bottom:6px}
.empty .big{width:52px;height:52px;border-radius:50%;background:var(--low-bg);color:var(--low);display:grid;place-items:center;margin:0 auto 14px}
.stApp .foot{text-align:center;color:var(--muted);font-size:.78rem;padding:26px 0 0}
.mini-row{display:flex;gap:10px;flex-wrap:wrap;margin:6px 0 14px}
.mini{background:#fff;border:1px solid var(--line);border-radius:var(--radius-sm);padding:10px 16px;display:flex;align-items:center;gap:10px}
.mini b{font-size:1.2rem}.mini .dot{width:9px;height:9px;border-radius:50%;display:inline-block}

/* ---------- tables built from columns ---------- */
[class*="st-key-tbl_"]{background:#fff;border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow);overflow:hidden;gap:0!important;margin-top:6px}
[class*="st-key-thead_"]{background:var(--hover);border-bottom:1px solid var(--line);padding:11px 16px}
.th{font-size:.7rem;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);font-weight:650;white-space:nowrap}
[class*="st-key-trow_"]{border-bottom:1px solid var(--line-2);padding:10px 16px}
[class*="st-key-trow_"]:last-child{border-bottom:0}
[class*="st-key-trow_"]:hover{background:var(--hover)}
[class*="st-key-trow_"] [data-testid="stVerticalBlock"]{gap:.15rem}
[class*="st-key-rrow_"]{border-bottom:1px solid var(--line-2);padding:10px 0}
[class*="st-key-rrow_"]:last-child{border-bottom:0}
[class*="st-key-link_"] button{background:transparent!important;border:0!important;box-shadow:none!important;padding:0!important;min-height:0!important;justify-content:flex-start!important;width:auto!important}
[class*="st-key-link_"] button p{font-family:var(--mono);font-weight:600;font-size:.9rem;color:var(--ink)}
[class*="st-key-link_"] button:hover p{color:var(--accent)}
.tr-r-modified{box-shadow:inset 3px 0 0 var(--t-modified)}
.table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:var(--radius);background:#fff;box-shadow:var(--shadow)}
.table-wrap table{width:100%;border-collapse:collapse}
.table-wrap th{text-align:left;font-size:.7rem;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);font-weight:650;padding:12px 16px;background:var(--hover);border-bottom:1px solid var(--line)}
.table-wrap td{padding:12px 16px;border-bottom:1px solid var(--line-2)}
.table-wrap .num{text-align:right}
.filter-line{display:flex;gap:10px;align-items:center}
.st-key-clear_search button{background:var(--accent-50)!important;color:var(--accent-ink)!important;border:0!important;border-radius:999px!important;font-weight:600;padding:.15rem .9rem!important;width:auto!important}

/* ---------- server detail ---------- */
.server-head{display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap;align-items:flex-start}
.stApp .server-head h1{font-family:var(--mono);font-size:1.5rem;letter-spacing:-.02em;display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:0}
.meta{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px 24px;margin-top:16px}
.meta dt{color:var(--muted);font-size:.7rem;text-transform:uppercase;letter-spacing:.07em;font-weight:600}
.meta dd{margin:2px 0 0;font-weight:500}
.code{background:#0F172A;color:#CBD5E1;border-radius:var(--radius);padding:16px 0;font-family:var(--mono);font-size:.8rem;overflow-x:auto}
.code .ln{display:block;padding:0 18px;white-space:pre;border-left:3px solid transparent}
.code .ln.d-modified{background:rgba(59,130,246,.18);border-left-color:#60A5FA;color:#fff}
.code .ln.d-added{background:rgba(20,184,166,.18);border-left-color:#2DD4BF;color:#fff}
.code .ln.d-removed{background:rgba(139,92,246,.2);border-left-color:#A78BFA;color:#fff}
.code-title{font-weight:600;margin-bottom:8px}
.stApp .hint{color:var(--muted);font-size:.8rem;margin-top:8px}
button[data-baseweb="tab"]{font-weight:600}

/* ---------- buttons ---------- */
.stButton>button,.stDownloadButton>button{border-radius:var(--radius-sm);font-weight:600;transition:background .15s,border-color .15s,color .15s}
.stButton>button[kind="primary"],.stButton>button[data-testid="stBaseButton-primary"]{background:var(--accent);border:1px solid var(--accent);color:#fff}
.stButton>button[data-testid="stBaseButton-primary"]:hover{background:var(--accent-600);border-color:var(--accent-600)}
.stButton>button[data-testid="stBaseButton-secondary"],.stDownloadButton>button{background:#fff;border:1px solid #D0D5DD;color:var(--ink-2)}
.stButton>button[data-testid="stBaseButton-secondary"]:hover,.stDownloadButton>button:hover{border-color:var(--accent);color:var(--accent);background:#fff}
div[data-testid="stDialog"] .stButton>button{width:100%}
[class*="st-key-rev_"] button{padding:.25rem .8rem;min-height:0;font-size:.82rem;width:100%}

/* ---------- review drawer (st.dialog styled as a side panel) ---------- */
div[data-testid="stDialog"]>div{position:fixed!important;inset:0!important;width:100vw!important;max-width:none!important;height:100vh!important;margin:0!important;padding:0!important;background:transparent!important;border-radius:0!important;align-items:stretch!important;justify-content:flex-end!important}
div[data-testid="stDialog"] section[role="dialog"]{width:min(560px,100vw)!important;max-width:560px!important;height:100vh!important;max-height:100vh!important;
 margin:0 0 0 auto!important;border-radius:0!important;background:#fff!important;box-shadow:-20px 0 40px rgba(16,24,40,.18);overflow-y:auto}
.drawer-head{padding:0 0 14px;border-bottom:1px solid var(--line);margin-bottom:16px}
.eyebrow{font-family:var(--mono);font-size:.75rem;color:var(--muted)}
.stApp .drawer-head h2{font-size:1.3rem;letter-spacing:-.01em;margin:2px 0;padding:0}
.drawer-head code{font-size:.78rem;color:var(--muted)}
.badges{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:18px}
.sec{font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:700;margin:18px 0 10px}
.evidence{display:grid;grid-template-columns:1fr auto 1fr;gap:12px;align-items:center}
.evidence .box{border:1px solid var(--line);border-radius:var(--radius-sm);padding:12px 14px;background:var(--hover)}
.evidence .box .lbl{font-size:.72rem;color:var(--muted);font-weight:600;margin-bottom:6px}
.arr{color:var(--muted);font-size:1.2rem}
.exp-block{margin-bottom:14px}
.stApp .exp-block h4{font-size:.82rem;font-weight:650;margin-bottom:3px;color:var(--ink)}
.stApp .exp-block p{color:var(--ink-2);line-height:1.6}
.exp-block code{background:var(--accent-50);color:var(--accent-ink);padding:1px 6px;border-radius:5px;font-size:.84em}
.fixbox{background:var(--hover);border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:var(--radius-sm);padding:10px 14px;color:var(--ink-2)}
.fixbox code{background:var(--accent-50);color:var(--accent-ink);padding:1px 6px;border-radius:5px;font-size:.84em}
.decided{background:var(--hover);border:1px solid var(--line);border-radius:var(--radius-sm);padding:12px 14px}

/* ---------- print ---------- */
.print-report{display:none}
@media print{
  section[data-testid="stSidebar"],header[data-testid="stHeader"],div[data-testid="stSidebarCollapsedControl"]{display:none!important}
  [data-testid="stMainBlockContainer"]>[data-testid="stVerticalBlock"]>*:not(:has(.print-report)){display:none!important}
  .print-report{display:block!important;color:#000}
  .print-report h1{font-size:20pt;margin-bottom:4pt}
  .print-report h2{font-size:13pt;margin:16pt 0 6pt;font-family:var(--mono)}
  .print-report table{width:100%;border-collapse:collapse;font-size:9.5pt}
  .print-report th,.print-report td{border:1px solid #CBD5E1;padding:5pt 7pt;text-align:left}
  .print-report tr{page-break-inside:avoid}
}
@media (max-width:900px){.evidence{grid-template-columns:1fr}.evidence .arr{transform:rotate(90deg);justify-self:center}}
"""
