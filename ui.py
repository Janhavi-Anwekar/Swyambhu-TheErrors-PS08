"""UI helpers: HTML snippets, SVG charts and CSS (Apple-inspired look).

Everything here returns SINGLE-LINE html strings (no blank lines / indentation), because
st.markdown would otherwise treat indented lines as code blocks.
"""
import html
import json
import math
from datetime import datetime

from core import DOT, TYPE_LABEL, label, plain, RISK_RULES, STANDARD_BASELINE


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


def kind_label(kind: str) -> str:
    return {"json": "JSON", "ssh": "SSH config", "standard": "Standard"}.get(kind, kind)


def risk_badge(r: str) -> str:
    return f'<span class="badge {r}"><i></i>{"Clean" if r == "None" else r}</span>'


def type_badge(t: str) -> str:
    return f'<span class="badge t-{t}">{TYPE_LABEL[t]}</span>'


def status_badge(s: str) -> str:
    return f'<span class="badge s-{s}">{s}</span>'


def chip(value, cls: str = "", present: bool = True) -> str:
    if not present:
        return '<span class="chip none">not set</span>'
    return f'<span class="chip {cls}">{esc(plain(value))}</span>'


def finding_chips(f):
    """(expected_chip, actual_chip) for a finding."""
    return (chip(f["expected"], "", f["type"] != "added"),
            chip(f["actual"], "t-" + f["type"], f["type"] != "removed"))


def pill(text: str, cls: str = "") -> str:
    return f'<span class="pill {cls}">{esc(text)}</span>'


# ---------------------------------------------------------------- blocks
_ICON = ('<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" '
         'stroke-linecap="round" stroke-linejoin="round">{}</svg>')


def hero() -> str:
    return ('<div class="hero"><div class="hero-eyebrow">Configuration drift</div>'
            '<h1>See what changed.<br><span class="grad">Know what matters.</span></h1>'
            '<p class="hero-sub">Upload a configuration, compare it with a baseline, and get a clear, '
            'risk-rated report in seconds.</p></div>')


def step_head(n: str, title: str, tag: str, tag_cls: str, desc: str) -> str:
    return (f'<div class="step"><div class="step-top"><span class="step-n">{n}</span>'
            f'<span class="tag-pill {tag_cls}">{tag}</span></div><h3>{esc(title)}</h3><p>{esc(desc)}</p>'
            '<div class="fmt"><span>JSON</span><span>sshd_config</span></div></div>')


def ready_line(msg_html: str, ok: bool) -> str:
    return f'<div class="ready {"ok" if ok else ""}"><i></i><span>{msg_html}</span></div>'


def features() -> str:
    items = [
        (_ICON.format('<path d="M4 6h16M4 12h16M4 18h10"/>'), "Rules decide",
         "Every change is found and rated by fixed rules. Nothing is guessed."),
        (_ICON.format('<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/>'), "AI explains",
         "Plain-language reasons and safe fixes for each verified finding."),
        (_ICON.format('<circle cx="12" cy="12" r="9"/><path d="M8.5 12.5l2.5 2.5 4.5-5"/>'), "You approve",
         "Every fix is your decision. The tool never touches a server."),
    ]
    return ('<div class="features">' + "".join(
        f'<div class="feat"><div class="feat-ic">{ic}</div><h4>{t}</h4><p>{d}</p></div>' for ic, t, d in items) + "</div>")


def baseline_table() -> str:
    rows = "".join(
        f'<tr><td>{esc(label(k))}<span class="key">{esc(k)}</span></td><td>{chip(v)}</td>'
        f'<td>{risk_badge(RISK_RULES.get(k, "Medium"))}</td></tr>' for k, v in STANDARD_BASELINE.items())
    return ('<div class="table-wrap"><table><thead><tr><th>Setting</th><th>Expected value</th><th>If it differs</th>'
            f'</tr></thead><tbody>{rows}</tbody></table></div>')


def empty_state(title: str, msg: str) -> str:
    return ('<div class="empty-state"><div class="big"><svg width="30" height="30" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M5 4h10l4 4v12H5z"/><path d="M15 4v4h4"/><path d="M9 13h6M9 17h4"/></svg></div>'
            f'<h3>{esc(title)}</h3><p>{esc(msg)}</p></div>')


def empty_clean(msg: str) -> str:
    return ('<div class="empty-state ok"><div class="big"><svg width="30" height="30" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
            '<circle cx="12" cy="12" r="9"/><path d="M8.5 12.5l2.5 2.5 4.5-5"/></svg></div>'
            f'<h3>No drift detected</h3><p>{esc(msg)}</p></div>')


def empty(title: str, msg: str = "") -> str:
    return f'<div class="empty-state"><h3>{esc(title)}</h3><p>{esc(msg)}</p></div>'


def result_head(name: str, kind: str, base_label: str, when: str) -> str:
    return ('<div class="res-head"><div class="eyebrow">Comparison result</div>'
            f'<h1>{esc(name)}</h1><div class="res-meta">{pill(kind_label(kind))}'
            f'<span class="vs">compared with</span>{pill(base_label, "accent")}'
            f'<span class="vs">· {esc(when)}</span></div></div>')


def verdict(findings: list, checked: int) -> str:
    n = len(findings)
    high = sum(1 for f in findings if f["risk"] == "High")
    if not n:
        title, sub = "All clear.", f"All {checked} checked settings match the baseline."
    elif high:
        title = f"{high} critical change{'' if high == 1 else 's'} need attention."
        sub = f"{n} difference{'' if n == 1 else 's'} found across {checked} checked settings."
    else:
        title = f"{n} change{'' if n == 1 else 's'} found."
        sub = f"None are high risk. {checked} settings were checked."
    counts = {r: sum(1 for f in findings if f["risk"] == r) for r in ("High", "Medium", "Low")}
    stats = "".join(f'<div class="stat"><div class="stat-n">{counts[r]}</div>'
                    f'<div class="stat-l"><i style="background:{DOT[r]}"></i>{r}</div></div>' for r in counts)
    return (f'<div class="verdict"><h2>{esc(title)}</h2><p>{esc(sub)}</p><div class="stats">{stats}</div></div>')


# ---------------------------------------------------------------- SVG charts
def ring(score: int) -> str:
    C = 2 * math.pi * 56
    col = DOT["Low"] if score >= 80 else DOT["Medium"] if score >= 50 else DOT["High"]
    return (f'<svg class="ring" viewBox="0 0 140 140" role="img" aria-label="Posture score {score} out of 100">'
            '<circle cx="70" cy="70" r="56" fill="none" stroke="#E8E8ED" stroke-width="10"/>'
            f'<circle cx="70" cy="70" r="56" fill="none" stroke="{col}" stroke-width="10" stroke-linecap="round" '
            f'stroke-dasharray="{C * score / 100:.2f} {C:.2f}" transform="rotate(-90 70 70)"/>'
            f'<text x="70" y="77" text-anchor="middle" class="r-num">{score}</text>'
            '<text x="70" y="96" text-anchor="middle" class="r-lbl">out of 100</text></svg>')


def trend(points: list[dict]) -> str:
    W, H, P = 460, 150, 28
    mx = max([1] + [p["drifts"] for p in points])
    n = len(points)
    x = lambda i: P + (W - 2 * P) * (0.5 if n == 1 else i / (n - 1))
    y = lambda v: H - P - (H - 2 * P) * v / mx
    line = " ".join(f"{x(i):.1f},{y(p['drifts']):.1f}" for i, p in enumerate(points))
    dots = "".join(
        f'<circle cx="{x(i):.1f}" cy="{y(p["drifts"]):.1f}" r="4" fill="#0071E3"/>'
        f'<text x="{x(i):.1f}" y="{y(p["drifts"]) - 10:.1f}" text-anchor="middle" font-size="11" fill="#1D1D1F" font-weight="600">{p["drifts"]}</text>'
        for i, p in enumerate(points))
    labels = "".join(
        f'<text x="{x(i):.1f}" y="{H - 6}" text-anchor="middle" font-size="10" fill="#6E6E73">{esc(p["time"].strftime("%H:%M"))}</text>'
        for i, p in enumerate(points))
    return (f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Drift count across comparisons">'
            f'<line x1="{P}" y1="{H - P}" x2="{W - P}" y2="{H - P}" stroke="#E8E8ED"/>'
            f'<polyline points="{line}" fill="none" stroke="#0071E3" stroke-width="2.5" stroke-linejoin="round"/>'
            f'{dots}{labels}</svg>')


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
BRAND = ('<div class="brand"><span class="logo"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" '
         'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
         '<path d="M12 3l8 3v6c0 4.5-3.2 8.2-8 9-4.8-.8-8-4.5-8-9V6z"/><path d="M9 12l2 2 4-4"/></svg></span>'
         '<span class="brand-name">Drift</span></div>')

FOOTER = ('<div class="foot">Detection and risk are rule-based. AI only explains verified findings. '
          'A person approves every fix.</div>')

# ---------------------------------------------------------------- CSS
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root{color-scheme:light;--bg:#fff;--alt:#F5F5F7;--ink:#1D1D1F;--ink-2:#424245;--muted:#6E6E73;--line:#D2D2D7;--line-2:#E8E8ED;
--accent:#0071E3;--accent-h:#0077ED;--accent-50:#EAF3FE;--accent-ink:#0058B0;
--high:#D70015;--high-bg:#FFF1F0;--high-line:#FFD3CF;--medium:#B25000;--medium-bg:#FFF6E5;--medium-line:#FFE0A6;--low:#1D7A34;--low-bg:#EDFAF1;--low-line:#BDEBCB;
--t-modified:#0058B0;--t-modified-bg:#EAF3FE;--t-added:#0B7A6F;--t-added-bg:#E8F8F5;--t-removed:#6E3AB5;--t-removed-bg:#F4EEFC;
--radius:20px;--radius-sm:12px;--shadow:0 1px 2px rgba(0,0,0,.04),0 4px 16px rgba(0,0,0,.04);
--mono:ui-monospace,'SF Mono',SFMono-Regular,Menlo,Consolas,monospace;
--sans:-apple-system,BlinkMacSystemFont,'SF Pro Display','SF Pro Text','Inter','Helvetica Neue',Arial,sans-serif}
html,body,[class*="st-"],.stApp{font-family:var(--sans);-webkit-font-smoothing:antialiased}
[data-testid="stIconMaterial"],span[class*="material"]{font-family:'Material Symbols Rounded','Material Symbols Outlined'!important}
.stApp{background:var(--bg);color:var(--ink)}
[data-testid="stMainBlockContainer"]{max-width:1120px;padding:0 28px 4rem}
header[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"],.stDeployButton,#MainMenu,footer,
section[data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"]{display:none!important}
h1,h2,h3,h4,p{margin:0;padding:0}
code{font-family:var(--mono)}
.muted{color:var(--muted)}

/* ---------- top navigation ---------- */
.st-key-topnav{position:sticky;top:0;z-index:100;background:rgba(255,255,255,.82);backdrop-filter:saturate(180%) blur(20px);
 -webkit-backdrop-filter:saturate(180%) blur(20px);border-bottom:1px solid rgba(0,0,0,.08);padding:10px 0;margin:0 -28px 0;padding-left:28px;padding-right:28px}
.brand{display:flex;align-items:center;gap:9px}
.logo{width:28px;height:28px;border-radius:8px;background:var(--ink);color:#fff;display:grid;place-items:center}
.brand-name{font-weight:650;font-size:1.05rem;letter-spacing:-.02em}
.st-key-topnav .stButton>button{border:0;background:transparent;color:var(--ink-2);font-weight:500;font-size:.88rem;border-radius:999px;padding:.3rem .9rem;min-height:0}
.st-key-topnav .stButton>button:hover{background:var(--alt);color:var(--ink)}
.st-key-topnav .stButton>button p{font-size:.88rem}
.nav-right{text-align:right;color:var(--muted);font-size:.8rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}

/* ---------- hero ---------- */
.hero{text-align:center;padding:76px 0 44px}
.hero-eyebrow{color:var(--accent);font-weight:600;font-size:1.05rem;margin-bottom:14px}
.stApp .hero h1{font-size:clamp(2.5rem,6vw,4.1rem);line-height:1.04;letter-spacing:-.035em;font-weight:700;color:var(--ink)}
.hero .grad{background:linear-gradient(90deg,#0071E3,#7B5CFA 60%,#C04BD6);-webkit-background-clip:text;background-clip:text;color:transparent}
.stApp .hero-sub{font-size:1.3rem;line-height:1.4;color:var(--muted);max-width:620px;margin:20px auto 0;font-weight:400}

/* ---------- upload cards ---------- */
[class*="st-key-card_"]{background:var(--alt);border-radius:24px;padding:28px 28px 24px!important;gap:.8rem;border:0}
.step-top{display:flex;align-items:center;gap:10px;margin-bottom:12px}
.step-n{width:26px;height:26px;border-radius:50%;background:var(--ink);color:#fff;font-size:.8rem;font-weight:600;display:grid;place-items:center}
.tag-pill{font-size:.72rem;font-weight:600;padding:3px 10px;border-radius:999px}
.tag-pill.req{background:var(--accent-50);color:var(--accent-ink)}
.tag-pill.opt{background:#fff;color:var(--muted);border:1px solid var(--line)}
.stApp .step h3{font-size:1.45rem;letter-spacing:-.02em;font-weight:650}
.stApp .step p{color:var(--muted);margin-top:6px;line-height:1.5;font-size:.95rem}
.fmt{display:flex;gap:6px;margin-top:12px}
.fmt span{font-family:var(--mono);font-size:.72rem;background:#fff;border:1px solid var(--line-2);color:var(--ink-2);padding:2px 9px;border-radius:999px}
[data-testid="stFileUploaderDropzone"]{background:#fff;border:1.5px dashed var(--line);border-radius:16px;padding:20px}
[data-testid="stFileUploaderDropzone"]:hover{border-color:var(--accent)}
[data-testid="stFileUploaderFile"]{background:#fff;border-radius:12px;padding:6px 10px}

.ready{display:flex;align-items:center;justify-content:center;gap:10px;margin:26px auto 16px;color:var(--muted);font-size:1rem;text-align:center}
.ready i{width:9px;height:9px;border-radius:50%;background:var(--line);display:inline-block;flex:none}
.ready.ok i{background:var(--low-line);box-shadow:0 0 0 3px var(--low-bg);background:#34C759}
.ready b{color:var(--ink);font-weight:600}

.features{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin:64px 0 8px}
.feat{text-align:center;padding:0 12px}
.feat-ic{width:48px;height:48px;border-radius:14px;background:var(--alt);display:grid;place-items:center;margin:0 auto 14px;color:var(--ink)}
.stApp .feat h4{font-size:1.05rem;font-weight:650;letter-spacing:-.01em}
.stApp .feat p{color:var(--muted);font-size:.92rem;line-height:1.5;margin-top:5px}
[data-testid="stExpander"]{border:0!important;background:var(--alt);border-radius:16px}
[data-testid="stExpander"] summary{font-weight:600}

/* ---------- result head / verdict ---------- */
.res-head{padding:44px 0 24px}
.eyebrow{color:var(--accent);font-weight:600;font-size:.9rem;margin-bottom:6px}
.stApp .res-head h1{font-family:var(--mono);font-size:2.2rem;letter-spacing:-.03em;font-weight:650;word-break:break-all}
.res-meta{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:12px;color:var(--muted)}
.vs{font-size:.9rem}
.pill{display:inline-block;padding:3px 11px;border-radius:999px;font-size:.78rem;font-weight:600;background:var(--alt);color:var(--ink-2)}
.pill.accent{background:var(--accent-50);color:var(--accent-ink)}
.verdict{padding:6px 0}
.stApp .verdict h2{font-size:2.1rem;letter-spacing:-.03em;font-weight:700;line-height:1.1}
.stApp .verdict p{color:var(--muted);font-size:1.05rem;margin-top:8px}
.stats{display:flex;gap:34px;margin-top:22px;flex-wrap:wrap}
.stat-n{font-size:2.6rem;font-weight:700;letter-spacing:-.04em;line-height:1}
.stat-l{display:flex;align-items:center;gap:7px;color:var(--muted);font-size:.9rem;margin-top:6px}
.stat-l i{width:9px;height:9px;border-radius:50%;display:inline-block}
.card-title{font-size:1rem;font-weight:650;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;gap:10px}
.card-title small{color:var(--muted);font-weight:500;font-size:.8rem}
.center{display:flex;flex-direction:column;align-items:center;text-align:center}
.ring{width:150px;height:150px}
.ring text.r-num{font-size:38px;font-weight:700;fill:var(--ink);letter-spacing:-.04em}
.ring text.r-lbl{font-size:11px;fill:var(--muted)}
.stApp .formula{color:var(--muted);font-size:.78rem;margin-top:8px}
.note{background:var(--alt);border-radius:16px;padding:16px 20px;color:var(--ink-2);font-size:.92rem;line-height:1.55}
.note b{color:var(--ink)}
.note code{background:#fff;padding:1px 6px;border-radius:6px;font-size:.82em}

/* ---------- badges / chips ---------- */
.badge{display:inline-flex;align-items:center;gap:6px;padding:3px 11px;border-radius:999px;font-size:.76rem;font-weight:600;border:1px solid transparent;white-space:nowrap}
.badge i{width:7px;height:7px;border-radius:50%;display:inline-block}
.badge.High{background:var(--high-bg);color:var(--high);border-color:var(--high-line)}.badge.High i{background:#FF3B30}
.badge.Medium{background:var(--medium-bg);color:var(--medium);border-color:var(--medium-line)}.badge.Medium i{background:#FF9F0A}
.badge.Low,.badge.None{background:var(--low-bg);color:var(--low);border-color:var(--low-line)}.badge.Low i,.badge.None i{background:#34C759}
.badge.t-modified{background:var(--t-modified-bg);color:var(--t-modified)}
.badge.t-added{background:var(--t-added-bg);color:var(--t-added)}
.badge.t-removed{background:var(--t-removed-bg);color:var(--t-removed)}
.badge.t-same{background:var(--alt);color:var(--muted)}
.badge.s-Pending{background:var(--alt);color:var(--ink-2)}
.badge.s-Approved{background:var(--accent-50);color:var(--accent-ink)}
.badge.s-Rejected{background:#F1F1F3;color:#6E6E73}
.chip{font-family:var(--mono);font-size:.8rem;padding:3px 10px;border-radius:8px;background:var(--alt);color:var(--ink-2);display:inline-block}
.chip.none{background:transparent;border:1px dashed var(--line);color:var(--muted);font-style:italic}
.chip.t-modified{background:var(--t-modified-bg);color:var(--t-modified)}
.chip.t-added{background:var(--t-added-bg);color:var(--t-added)}
.chip.t-removed{background:var(--t-removed-bg);color:var(--t-removed)}
.tag{font-size:.68rem;font-weight:700;letter-spacing:.05em;text-transform:uppercase;padding:2px 8px;border-radius:6px;margin-left:8px;vertical-align:2px}
.tag-rule{background:var(--alt);color:var(--ink-2)}
.tag-ai{background:var(--accent-50);color:var(--accent-ink)}
.key{display:block;font-family:var(--mono);font-size:.72rem;color:var(--muted)}
.stApp .cell-title{font-weight:600;color:var(--ink)}
.stApp .cell-sub{color:var(--muted);font-size:.82rem}
.mono{font-family:var(--mono)}
.empty-state{text-align:center;padding:70px 20px;color:var(--muted);background:var(--alt);border-radius:24px}
.stApp .empty-state h3{color:var(--ink);font-size:1.5rem;letter-spacing:-.02em;margin-bottom:6px}
.empty-state .big{width:64px;height:64px;border-radius:50%;background:#fff;color:var(--muted);display:grid;place-items:center;margin:0 auto 18px}
.empty-state.ok .big{background:var(--low-bg);color:#34A853}
.stApp .foot{text-align:center;color:var(--muted);font-size:.8rem;padding:48px 0 0}
.mini-row{display:flex;gap:12px;flex-wrap:wrap;margin:6px 0 16px}
.mini{background:var(--alt);border-radius:14px;padding:12px 20px;display:flex;align-items:center;gap:10px}
.mini b{font-size:1.3rem;letter-spacing:-.02em}

/* ---------- tables built from columns ---------- */
[class*="st-key-tbl_"]{background:#fff;border:1px solid var(--line-2);border-radius:var(--radius);overflow:hidden;gap:0!important;margin-top:6px}
[class*="st-key-thead_"]{background:var(--alt);padding:12px 20px}
.th{font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:600;white-space:nowrap}
[class*="st-key-trow_"]{border-top:1px solid var(--line-2);padding:12px 20px}
[class*="st-key-trow_"]:hover{background:#FAFAFC}
[class*="st-key-trow_"] [data-testid="stVerticalBlock"]{gap:.15rem}
.table-wrap{overflow-x:auto;border:1px solid var(--line-2);border-radius:var(--radius);background:#fff}
.table-wrap table{width:100%;border-collapse:collapse}
.table-wrap th{text-align:left;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:600;padding:12px 18px;background:var(--alt)}
.table-wrap td{padding:12px 18px;border-top:1px solid var(--line-2)}
.table-wrap .num{text-align:right}

/* ---------- code view ---------- */
.code{background:#1D1D1F;color:#D2D2D7;border-radius:var(--radius);padding:16px 0;font-family:var(--mono);font-size:.8rem;overflow-x:auto}
.code .ln{display:block;padding:0 18px;white-space:pre;border-left:3px solid transparent}
.code .ln.d-modified{background:rgba(10,132,255,.2);border-left-color:#64A8FF;color:#fff}
.code .ln.d-added{background:rgba(48,209,88,.18);border-left-color:#5DDB82;color:#fff}
.code .ln.d-removed{background:rgba(191,90,242,.2);border-left-color:#D18AF7;color:#fff}
.code-title{font-weight:600;margin-bottom:8px}
.stApp .hint{color:var(--muted);font-size:.82rem;margin-top:8px}
button[data-baseweb="tab"]{font-weight:600}

/* ---------- buttons ---------- */
.stButton>button,.stDownloadButton>button{border-radius:999px;font-weight:600;transition:background .15s,color .15s,border-color .15s}
.stButton>button[data-testid="stBaseButton-primary"]{background:var(--accent);border:1px solid var(--accent);color:#fff;padding:.55rem 1.7rem}
.stButton>button[data-testid="stBaseButton-primary"]:hover{background:var(--accent-h);border-color:var(--accent-h)}
.stButton>button[data-testid="stBaseButton-primary"]:disabled{background:#D2D2D7;border-color:#D2D2D7;color:#fff}
.stButton>button[data-testid="stBaseButton-secondary"],.stDownloadButton>button{background:#fff;border:1px solid var(--line);color:var(--ink)}
.stButton>button[data-testid="stBaseButton-secondary"]:hover,.stDownloadButton>button:hover{border-color:var(--accent);color:var(--accent);background:#fff}
.stButton>button[data-testid="stBaseButton-tertiary"]{color:var(--accent)}
.stButton>button[data-testid="stBaseButton-tertiary"]:hover{background:var(--accent-50)}
div[data-testid="stDialog"] .stButton>button{width:100%}
[class*="st-key-rev_"] button{padding:.25rem .9rem;min-height:0;font-size:.82rem;width:100%}

/* ---------- review drawer (st.dialog styled as a side panel) ---------- */
div[data-testid="stDialog"]>div{position:fixed!important;inset:0!important;width:100vw!important;max-width:none!important;height:100vh!important;margin:0!important;padding:0!important;background:rgba(0,0,0,.25)!important;border-radius:0!important;align-items:stretch!important;justify-content:flex-end!important}
div[data-testid="stDialog"] section[role="dialog"]{width:min(560px,100vw)!important;max-width:560px!important;height:100vh!important;max-height:100vh!important;
 margin:0 0 0 auto!important;border-radius:0!important;background:#fff!important;box-shadow:-20px 0 40px rgba(0,0,0,.12);overflow-y:auto}
.drawer-head{padding:0 0 14px;border-bottom:1px solid var(--line-2);margin-bottom:16px}
.stApp .drawer-head .eyebrow{font-family:var(--mono);font-size:.75rem;color:var(--muted);font-weight:500}
.stApp .drawer-head h2{font-size:1.5rem;letter-spacing:-.02em;margin:2px 0;padding:0}
.drawer-head code{font-size:.78rem;color:var(--muted)}
.badges{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:18px}
.sec{font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:700;margin:18px 0 10px}
.evidence{display:grid;grid-template-columns:1fr auto 1fr;gap:12px;align-items:center}
.evidence .box{border-radius:var(--radius-sm);padding:12px 14px;background:var(--alt)}
.evidence .box .lbl{font-size:.72rem;color:var(--muted);font-weight:600;margin-bottom:6px}
.arr{color:var(--muted);font-size:1.2rem}
.exp-block{margin-bottom:14px}
.stApp .exp-block h4{font-size:.85rem;font-weight:650;margin-bottom:3px;color:var(--ink)}
.stApp .exp-block p{color:var(--ink-2);line-height:1.6}
.exp-block code,.fixbox code{background:#fff;color:var(--accent-ink);padding:1px 6px;border-radius:5px;font-size:.84em}
.fixbox{background:var(--alt);border-left:3px solid var(--accent);border-radius:var(--radius-sm);padding:10px 14px;color:var(--ink-2)}
.decided{background:var(--alt);border-radius:var(--radius-sm);padding:12px 14px}

/* ---------- print ---------- */
.print-report{display:none}
@media print{
  .st-key-topnav,header[data-testid="stHeader"]{display:none!important}
  [data-testid="stMainBlockContainer"]>[data-testid="stVerticalBlock"]>*:not(:has(.print-report)){display:none!important}
  .print-report{display:block!important;color:#000}
  .print-report h1{font-size:20pt;margin-bottom:4pt}
  .print-report h2{font-size:13pt;margin:16pt 0 6pt;font-family:var(--mono)}
  .print-report table{width:100%;border-collapse:collapse;font-size:9.5pt}
  .print-report th,.print-report td{border:1px solid #CBD5E1;padding:5pt 7pt;text-align:left}
  .print-report tr{page-break-inside:avoid}
}
@media (max-width:900px){.evidence{grid-template-columns:1fr}.evidence .arr{transform:rotate(90deg);justify-self:center}.features{grid-template-columns:1fr}}
"""
