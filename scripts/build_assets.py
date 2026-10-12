"""
Generates the animated SVGs used by the profile README (assets/*.svg).

    pip install fonttools brotli
    python scripts/build_assets.py

Fonts (Space Grotesk, JetBrains Mono — SIL OFL) are downloaded once into
scripts/.fonts/, instanced to static weights, subset to the glyphs each SVG uses
and embedded as WOFF2, so every image renders identically on any machine.
Text is measured with the real font metrics, so wrapping never overflows.

Edit PROJECTS / TERMINAL / IMPACT below and re-run to update the profile.
"""

from __future__ import annotations

import base64
import html
import io
import urllib.request
from functools import lru_cache
from pathlib import Path

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
FONT_DIR = Path(__file__).resolve().parent / ".fonts"
FONT_SRC = {
    "SpaceGrotesk": "https://github.com/google/fonts/raw/main/ofl/spacegrotesk/SpaceGrotesk%5Bwght%5D.ttf",
    "JetBrainsMono": "https://github.com/google/fonts/raw/main/ofl/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf",
}

BG = "#080808"
FG = "#F5F5F5"
MUTED = "#8A8A8A"
DIM = "#5A5A5A"
LINE = "#222222"
ACCENT = "#3DF2A6"
BLUE = "#5AB8FF"
WARN = "#F2C94C"
DANGER = "#FF5C5C"

PORTFOLIO = "https://my-portfolio-nine-pied-83.vercel.app"

# ── content ──────────────────────────────────────────────────────────────────

PROJECTS = [
    dict(id="pycodeatlas", n="001", title="PyCodeAtlas", status="PUBLISHED · PYPI", live=False, motif="graph",
         repo="avkad3/CodeAtlas",
         tagline="Static analysis CLI that maps a codebase's dependency graph, classifies dead code and shows what breaks if you delete a function or module.",
         stack=["Python", "AST", "NetworkX", "D3.js", "SQLite"], metric=("pip", "install pycodeatlas")),
    dict(id="gmci", n="002", title="Maps Competitor Intelligence", status="SHIPPED", live=False, motif="flow",
         repo="avkad3/Google_Maps_Competitor_Update_Intelligence",
         tagline="Scrapes competitors' Google Maps updates, de-duplicates them by fingerprint, classifies them with LLMs and drafts new posts.",
         stack=["Flask", "Selenium", "SQLite", "Gemini", "Groq", "Docker"], metric=None),
    dict(id="cmpis", n="003", title="CMPIS", status="SHIPPED", live=False, motif="spark",
         repo="avkad3/CMPIS-Construction-Material-Price-Intelligence-System",
         tagline="Construction material price intelligence: vendor quotes vs six months of history, flagged green, yellow or red.",
         stack=["FastAPI", "Streamlit", "SQLAlchemy", "RapidFuzz", "Plotly"], metric=None),
    dict(id="ascii", n="004", title="ASCII Lab", status="LIVE", live=True, motif="ascii",
         repo="avkad3/ASCII-Lab",
         tagline="Images, video and live webcam rendered as ASCII with 5 modes, 3 dithering algorithms and per-character colour.",
         stack=["FastAPI", "OpenCV", "NumPy", "Pillow", "pytest", "Docker"], metric=None),
    dict(id="mofs", n="005", title="Mini Order Fulfillment", status="SHIPPED", live=False, motif="steps",
         repo="avkad3/mini-order-fulfillment-system",
         tagline="SAP Order-to-Cash in miniature: PO upload, approve / reject / partial, sales orders and inventory reservation.",
         stack=["React", "TypeScript", "FastAPI", "SQLAlchemy", "JWT"], metric=None),
    dict(id="loan", n="006", title="Loan Eligibility Prediction", status="LIVE", live=True, motif="bars",
         repo="avkad3/loan-eligibility-prediction",
         tagline="MLOps around a Random Forest: MLflow, DVC, SHAP + LIME explanations, a Fairlearn audit, FastAPI and CI.",
         stack=["scikit-learn", "MLflow", "DVC", "SHAP", "FastAPI"], metric=None),
    dict(id="rcae", n="007", title="RCAE", status="PUBLISHED · ZENODO", live=False, motif="gauge",
         repo="avkad3/RCAE-Reservation-Conflict-Anticipation-Engine",
         tagline="Reservation Conflict Anticipation Engine: scores bookings on turnover, cascade risk, kitchen load and dead time.",
         stack=["Python", "FastAPI", "React", "SQLite"], metric=("30%", "fewer overbookings")),
    dict(id="waste", n="008", title="Waste Image Classifier", status="SHIPPED", live=False, motif="scan",
         repo="avkad3/Waste-Image-Classifier",
         tagline="Computer vision that sorts waste photos into six classes, from a custom CNN to MobileNetV2 transfer learning.",
         stack=["TensorFlow", "MobileNetV2", "scikit-learn", "Streamlit"], metric=None),
]

TERMINAL = [
    ("whoami", ["Aditya Vijay Kumar — AI/ML + backend engineer · Mumbai, India"]),
    ("cat focus.txt", ["LLMs · RAG · machine learning · forecasting · backend systems · developer tooling"]),
    ("ls ~/published", ["pycodeatlas   PyPI", "rcae          Zenodo (CERN) · doi:10.5281/zenodo.21477811"]),
    ("cat education.txt", ["B.E. Computer Engineering (AI & ML) · Pillai College of Engineering · 2023–2027"]),
]

IMPACT = [
    ("34,000", "+", "PRODUCT-PLANT SERIES", "multi-horizon forecasting"),
    ("22", "%", "STOCK-OUT REDUCTION", "TFT + LightGBM"),
    ("94", "%", "SEMANTIC ACCURACY", "RAG reconciliation agent"),
    ("30", "%", "FEWER OVERBOOKINGS", "RCAE conflict engine"),
]

SECTIONS = [("01", "whoami", "IDENTITY"), ("02", "impact", "OUTPUT"), ("03", "systems", "SYSTEMS I'VE BUILT"),
            ("04", "experience", "EXPERIENCE"), ("05", "stack", "STACK.EXE"), ("06", "published", "PUBLICATIONS")]

# ── fonts ────────────────────────────────────────────────────────────────────

FACES = {"display": ("SpaceGrotesk", 700), "display5": ("SpaceGrotesk", 500), "mono": ("JetBrainsMono", 400), "monob": ("JetBrainsMono", 700)}


@lru_cache(None)
def static_font(key: str) -> TTFont:
    family, weight = FACES[key]
    FONT_DIR.mkdir(exist_ok=True)
    src = FONT_DIR / f"{family}.ttf"
    if not src.exists():
        urllib.request.urlretrieve(FONT_SRC[family], src)
    return instancer.instantiateVariableFont(TTFont(src), {"wght": weight})


def measure(text: str, key: str, size: float, spacing: float = 0) -> float:
    f = static_font(key)
    cmap, hmtx, upm = f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm
    w = 0.0
    for ch in text:
        g = cmap.get(ord(ch))
        w += (hmtx[g][0] / upm * size) if g else size * 0.6
        w += spacing
    return w - spacing if text else 0


def wrap(text: str, key: str, size: float, width: float, max_lines: int = 3) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        cand = f"{cur} {w}".strip()
        if measure(cand, key, size) <= width:
            cur = cand
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        while measure(lines[-1] + "…", key, size) > width:
            lines[-1] = lines[-1].rsplit(" ", 1)[0]
        lines[-1] += "…"
    return lines


def font_css(used: dict[str, str]) -> str:
    """@font-face rules with WOFF2 subsets containing only the characters used."""
    out = []
    for key, chars in used.items():
        f = static_font(key)
        buf = io.BytesIO()
        f.save(buf)
        sub = TTFont(io.BytesIO(buf.getvalue()))
        opts = Options()
        opts.flavor = "woff2"
        opts.layout_features = ["kern", "liga"]
        s = Subsetter(opts)
        s.populate(text=chars + " ")
        s.subset(sub)
        b = io.BytesIO()
        sub.flavor = "woff2"
        sub.save(b)
        data = base64.b64encode(b.getvalue()).decode()
        out.append(f"@font-face{{font-family:'{key}';src:url(data:font/woff2;base64,{data}) format('woff2');}}")
    return "".join(out)


class Doc:
    """Collects SVG markup and the characters used per font face."""

    def __init__(self, w: int, h: int, title: str):
        self.w, self.h, self.title = w, h, title
        self.parts: list[str] = []
        self.defs: list[str] = []
        self.css: list[str] = []
        self.used: dict[str, str] = {}

    def text(self, x, y, s, key="mono", size=14, fill=FG, spacing=0, anchor="start", cls="", extra=""):
        self.used[key] = self.used.get(key, "") + s
        a = f' text-anchor="{anchor}"' if anchor != "start" else ""
        c = f' class="{cls}"' if cls else ""
        ls = f' letter-spacing="{spacing}"' if spacing else ""
        self.parts.append(f'<text xml:space="preserve" x="{x:.1f}" y="{y:.1f}" font-family="{key}" font-size="{size}" fill="{fill}"{ls}{a}{c}{extra}>{html.escape(s)}</text>')

    def add(self, s: str):
        self.parts.append(s)

    def render(self) -> str:
        fonts = font_css(self.used)
        css = fonts + "".join(self.css) + "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{html.escape(self.title)}">'
            f"<title>{html.escape(self.title)}</title><defs><style>{css}</style>{''.join(self.defs)}</defs>{''.join(self.parts)}</svg>"
        )


def frame(d: Doc, rx=16, glow=True):
    d.defs.append(
        '<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="#fff" stroke-opacity=".035"/></pattern>'
    )
    d.add(f'<rect width="{d.w}" height="{d.h}" rx="{rx}" fill="{BG}"/>')
    if glow:
        d.add(f'<rect width="{d.w}" height="{d.h}" rx="{rx}" fill="url(#grid)"/>')
    d.add(f'<rect x=".5" y=".5" width="{d.w - 1}" height="{d.h - 1}" rx="{rx - .5}" fill="none" stroke="{LINE}"/>')


def border_sweep(d: Doc, rx=16, dur=6, delay=0.0, color=ACCENT):
    """A short highlight that travels around the card border."""
    per = 2 * (d.w + d.h)
    d.css.append(f"@keyframes sweep{{to{{stroke-dashoffset:-{per}}}}}")
    d.defs.append(
        f'<linearGradient id="sw" x1="0" x2="1"><stop offset="0" stop-color="{color}" stop-opacity="0"/><stop offset=".5" stop-color="{color}"/><stop offset="1" stop-color="{BLUE}" stop-opacity=".2"/></linearGradient>'
    )
    d.add(
        f'<rect x="1" y="1" width="{d.w - 2}" height="{d.h - 2}" rx="{rx - 1}" fill="none" stroke="{color}" stroke-width="1.6" '
        f'stroke-dasharray="{per * 0.12:.0f} {per * 0.88:.0f}" style="animation:sweep {dur}s linear {delay}s infinite" stroke-linecap="round" opacity=".85"/>'
    )


# ── header ───────────────────────────────────────────────────────────────────


def header():
    d = Doc(1200, 450, "Aditya Vijay Kumar — I build intelligent systems. AI/ML engineer, backend engineer, GenAI developer. Mumbai, India.")
    d.defs.append(
        '<filter id="blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="60"/></filter>'
        f'<radialGradient id="gfade" cx="78%" cy="40%" r="65%"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>'
        '<mask id="gm"><rect width="1200" height="450" fill="url(#gfade)"/></mask>'
        f'<linearGradient id="shine" x1="0" x2="1"><stop offset="0" stop-color="{FG}"/><stop offset=".45" stop-color="{FG}"/><stop offset=".5" stop-color="{ACCENT}"/><stop offset=".55" stop-color="{FG}"/><stop offset="1" stop-color="{FG}"/><animateTransform attributeName="gradientTransform" type="translate" values="-1 0;1 0" dur="4.5s" begin="3.5s" repeatCount="indefinite"/></linearGradient>'
        f'<linearGradient id="edge" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="{ACCENT}" stop-opacity=".7"/><stop offset="1" stop-color="{BLUE}" stop-opacity=".5"/></linearGradient>'
        '<clipPath id="card"><rect width="1200" height="450" rx="16"/></clipPath>'
    )
    d.css.append(
        "@keyframes breathe{0%,100%{opacity:.16}50%{opacity:.32}}"
        "@keyframes drift{0%,100%{transform:translate(0,0)}50%{transform:translate(-40px,25px)}}"
        "@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}"
        "@keyframes rise{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:none}}"
        "@keyframes draw{from{stroke-dashoffset:1600}to{stroke-dashoffset:0}}"
        "@keyframes fillin{to{fill-opacity:1}}"
        "@keyframes scan{from{transform:translateY(-40px)}to{transform:translateY(470px)}}"
        "@keyframes flash{0%,100%{stroke:#2c2c2c}10%,25%{stroke:#3DF2A6}}"
        "@keyframes blink{50%{opacity:0}}"
        ".r{opacity:0;animation:rise 1s cubic-bezier(.16,1,.3,1) forwards}"
    )
    d.add('<g clip-path="url(#card)">')
    frame(d)
    d.parts[-2] = f'<rect width="1200" height="450" fill="url(#grid)" mask="url(#gm)"/>'
    # ambient glow
    d.add(f'<g style="animation:drift 14s ease-in-out infinite"><circle cx="940" cy="170" r="150" fill="{ACCENT}" filter="url(#blur)" style="animation:breathe 7s ease-in-out infinite"/>'
          f'<circle cx="1060" cy="320" r="120" fill="{BLUE}" filter="url(#blur)" style="animation:breathe 9s ease-in-out 2s infinite"/></g>')
    # scanline
    d.add(f'<rect width="1200" height="2" fill="{ACCENT}" opacity=".06" style="animation:scan 7s linear infinite"/>')

    # top bar
    d.add(f'<circle cx="52" cy="46" r="5" fill="{ACCENT}" style="animation:pulse 2.2s ease-in-out infinite"/>')
    d.text(68, 51, "ADITYA", "monob", 15, FG, 2.6)
    x = 68 + measure("ADITYA", "monob", 15, 2.6) + 2.6
    d.text(x, 51, ".", "monob", 15, ACCENT, 2.6)
    d.text(x + measure(".", "monob", 15) + 2.6, 51, "OS", "monob", 15, FG, 2.6)
    for i, (lab, val, dot) in enumerate([("SYSTEM STATUS", "ONLINE", True), ("LOCATION", "MUMBAI, INDIA", False)]):
        bx = 840 + i * 170
        d.text(bx, 42, lab, "mono", 10.5, DIM, 1.8)
        if dot:
            d.add(f'<circle cx="{bx + 4}" cy="56" r="3.2" fill="{ACCENT}" style="animation:pulse 2.2s ease-in-out infinite"/>')
        d.text(bx + (14 if dot else 0), 60, val, "monob", 11, FG, 1.6)

    # headline
    size = 86
    lines = [("I BUILD", "solid"), ("INTELLIGENT", "outline"), ("SYSTEMS", "solid")]
    for i, (word, kind) in enumerate(lines):
        y = 168 + i * 88
        delay = 0.15 + i * 0.12
        d.used["display"] = d.used.get("display", "") + word + "."
        if kind == "outline":
            d.add(f'<text x="48" y="{y}" font-family="display" font-size="{size}" letter-spacing="-2.5" fill="none" stroke="url(#shine)" stroke-width="1.5" '
                  f'stroke-dasharray="1600" stroke-dashoffset="1600" style="animation:draw 2.6s cubic-bezier(.6,0,.2,1) .5s forwards">{word}</text>')
        else:
            dot = f'<tspan fill="{ACCENT}">.</tspan>' if word == "SYSTEMS" else ""
            d.add(f'<text x="48" y="{y}" font-family="display" font-size="{size}" letter-spacing="-2.5" fill="{FG}" class="r" style="animation-delay:{delay}s">{word}{dot}</text>')

    # diagram
    nodes = {"model": (960, 132, "MODEL"), "rag": (848, 202, "RAG"), "ml": (960, 202, "ML"), "api": (1072, 202, "API"),
             "vdb": (848, 274, "VECTOR DB"), "fc": (960, 274, "FORECASTING"), "be": (1072, 274, "BACKEND"), "dep": (960, 344, "DEPLOYED")}
    edges = [("model", "rag"), ("model", "ml"), ("model", "api"), ("rag", "vdb"), ("ml", "fc"), ("api", "be"), ("vdb", "dep"), ("fc", "dep"), ("be", "dep")]
    d.text(960, 104, "AI SYSTEM", "mono", 10, DIM, 3.2, "middle")
    for i, (a, b) in enumerate(edges):
        (x1, y1, _), (x2, y2, _) = nodes[a], nodes[b]
        mid = (y1 + y2) / 2
        p = f"M{x1},{y1 + 13} V{mid} H{x2} V{y2 - 13}"
        d.add(f'<path d="{p}" fill="none" stroke="url(#edge)" stroke-opacity=".55"/>')
        dur = 2.4 + (i % 3) * 0.5
        d.add(f'<circle r="2.6" fill="{ACCENT}"><animateMotion dur="{dur}s" begin="{1 + i * 0.3:.1f}s" repeatCount="indefinite" path="{p}"/>'
              f'<animate attributeName="opacity" values="0;1;1;0" dur="{dur}s" begin="{1 + i * 0.3:.1f}s" repeatCount="indefinite"/></circle>')
    for i, (k, (x, y, lab)) in enumerate(nodes.items()):
        w = max(62, measure(lab, "mono", 10.5, 1.6) + 28)
        hot = k == "dep"
        d.add(f'<rect x="{x - w / 2:.1f}" y="{y - 13}" width="{w:.1f}" height="26" rx="4" fill="#0b0b0b" stroke="{ACCENT if hot else "#2c2c2c"}" '
              f'style="animation:flash 5s ease {i * 0.55:.2f}s infinite"/>')
        if hot:
            d.add(f'<circle cx="{x - w / 2 + 13:.1f}" cy="{y}" r="3" fill="{ACCENT}" style="animation:pulse 1.6s ease-in-out infinite"/>')
        d.text(x + (7 if hot else 0), y + 4, lab, "monob" if hot else "mono", 10.5, FG if hot else MUTED, 1.6, "middle")

    # bottom bar with typing role ticker
    d.add(f'<rect x="1" y="384" width="1198" height="65" fill="#0a0a0a"/><line x1="0" x2="1200" y1="384" y2="384" stroke="{LINE}"/>')
    d.text(48, 422, "ADITYA VIJAY KUMAR", "monob", 13.5, FG, 1.8)
    tx = 48 + measure("ADITYA VIJAY KUMAR", "monob", 13.5, 1.8) + 30
    d.text(tx, 422, ">", "monob", 13.5, ACCENT)
    tx += 22
    roles = ["AI/ML ENGINEER", "BACKEND ENGINEER", "GENAI DEVELOPER", "BUILDING INTELLIGENT SYSTEMS"]
    cyc = 3.2 * len(roles)
    for i, role in enumerate(roles):
        rw = measure(role, "mono", 13.5, 1.8)
        st = i * 3.2
        a, b = st / cyc * 100, (st + 3.2) / cyc * 100
        t_end = (st + 1.0) / cyc * 100
        name = f"role{i}"
        d.css.append(
            f"@keyframes {name}{{0%,{max(a - .01, 0):.2f}%{{opacity:0}}{a:.2f}%,{b - .01:.2f}%{{opacity:1}}{b:.2f}%,100%{{opacity:0}}}}"
            f"@keyframes {name}t{{0%,{a:.2f}%{{transform:translateX(0)}}{t_end:.2f}%,100%{{transform:translateX({rw + 4:.0f}px)}}}}"
        )
        steps = len(role)
        d.add(f'<g style="opacity:0;animation:{name} {cyc}s linear infinite">')
        d.text(tx, 422, role, "mono", 13.5, MUTED if i < 3 else FG, 1.8)
        d.add(f'<g style="animation:{name}t {cyc}s steps({steps}) infinite">'
              f'<rect x="{tx:.1f}" y="406" width="{rw + 30:.0f}" height="22" fill="#0a0a0a"/>'
              f'<rect x="{tx:.1f}" y="408" width="9" height="18" fill="{ACCENT}" style="animation:blink 1s step-end infinite"/></g></g>')
    d.text(1152, 422, "github.com/avkad3", "mono", 12.5, DIM, 1.4, "end")
    d.add("</g>")
    return d.render()


# ── terminal ─────────────────────────────────────────────────────────────────


def terminal():
    lh = 28
    rows = sum(1 + len(out) + 0.6 for _, out in TERMINAL) + 1.4
    h = int(64 + rows * lh + 20)
    d = Doc(1200, h, "Terminal: whoami — Aditya Vijay Kumar, AI/ML and backend engineer in Mumbai. Published pycodeatlas on PyPI and RCAE on Zenodo.")
    frame(d, glow=False)
    d.css.append(
        "@keyframes show{to{opacity:1}}@keyframes blink{50%{opacity:0}}@keyframes hide{to{opacity:0}}"
        ".o{opacity:0;animation:show .35s ease forwards}"
    )
    d.add(f'<line x1="0" x2="1200" y1="44" y2="44" stroke="{LINE}"/>')
    for i, c in enumerate(["#FF5F57", "#FEBC2E", "#28C840"]):
        d.add(f'<circle cx="{28 + i * 20}" cy="22" r="6" fill="{c}" opacity=".85"/>')
    d.text(600, 27, "aditya@os: ~ — zsh", "mono", 12, DIM, 0.5, "middle")

    y = 84
    t = 0.4
    for cmd, out in TERMINAL:
        d.text(40, y, "$", "monob", 16, ACCENT)
        cw = measure(cmd, "mono", 16)
        steps = len(cmd)
        dur = steps * 0.055
        d.text(62, y, cmd, "mono", 16, FG)
        d.css.append(f"@keyframes ty{int(y)}{{from{{transform:translateX(0)}}to{{transform:translateX({cw + 2:.0f}px)}}}}")
        d.add(f'<g style="animation:ty{int(y)} {dur:.2f}s steps({steps}) {t:.2f}s forwards">'
              f'<rect x="60" y="{y - 18}" width="{cw + 24:.0f}" height="26" fill="{BG}"/>'
              f'<rect x="61" y="{y - 16}" width="9" height="20" fill="{ACCENT}" opacity=".9" style="animation:hide 0s {t + dur + 0.2:.2f}s forwards"/></g>')
        t += dur + 0.25
        for line in out:
            y += lh
            d.add(f'<g class="o" style="animation-delay:{t:.2f}s">')
            d.text(62, y, line, "mono", 15.5, "#c9c9c9" if line == out[0] else MUTED)
            d.add("</g>")
            t += 0.12
        t += 0.35
        y += lh * 1.6
    d.add(f'<g class="o" style="animation-delay:{t:.2f}s">')
    d.text(40, y, "$", "monob", 16, ACCENT)
    d.add(f'<rect x="62" y="{y - 16}" width="9" height="20" fill="{ACCENT}" style="animation:blink 1.05s step-end infinite"/></g>')
    return d.render()


# ── impact ───────────────────────────────────────────────────────────────────


def impact():
    d = Doc(1200, 210, "Impact at SAVIC Technologies: 34,000+ product-plant series, 22% stock-out reduction, 94% semantic accuracy, 30% fewer overbooking incidents.")
    frame(d, glow=False)
    d.css.append(
        "@keyframes up{from{transform:translateY(70px)}to{transform:none}}"
        "@keyframes bar{from{transform:scaleX(0)}to{transform:scaleX(1)}}"
    )
    for i, (num, suf, label, sub) in enumerate(IMPACT):
        x0 = i * 300
        if i:
            d.add(f'<line x1="{x0}" x2="{x0}" y1="0" y2="210" stroke="{LINE}"/>')
        d.text(x0 + 30, 40, f"[0{i + 1}]", "mono", 11.5, DIM)
        d.defs.append(f'<clipPath id="c{i}"><rect x="{x0}" y="60" width="300" height="70"/></clipPath>')
        d.add(f'<g clip-path="url(#c{i})"><g style="animation:up 1.1s cubic-bezier(.16,1,.3,1) {0.15 + i * 0.12:.2f}s backwards">')
        d.text(x0 + 30, 120, num, "display", 60, FG, -2.5)
        d.text(x0 + 32 + measure(num, "display", 60, -2.5), 120, suf, "display", 60, ACCENT)
        d.add("</g></g>")
        d.add(f'<rect x="{x0 + 30}" y="138" width="60" height="2" fill="{ACCENT}" style="transform-origin:{x0 + 30}px 0;animation:bar 1s ease {0.5 + i * 0.12:.2f}s backwards"/>')
        d.text(x0 + 30, 166, label, "monob", 12, FG, 1.6)
        d.text(x0 + 30, 188, sub, "mono", 12, MUTED)
    return d.render()


# ── section headers ──────────────────────────────────────────────────────────


def section(idx: str, title: str):
    d = Doc(1200, 84, f"Section {idx}: {title}")
    d.css.append("@keyframes ln{from{transform:scaleX(0)}to{transform:scaleX(1)}}@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}")
    d.text(0, 56, idx, "monob", 14, ACCENT, 2.4)
    d.text(44, 56, "//", "mono", 14, DIM)
    tw = measure(title, "display", 40, -1.2)
    d.text(76, 60, title, "display", 40, FG, -1.2)
    lx = 76 + tw + 26
    d.add(f'<line x1="{lx:.0f}" x2="1192" y1="46" y2="46" stroke="{LINE}" style="transform-origin:{lx:.0f}px 0;animation:ln 1.4s cubic-bezier(.16,1,.3,1) .2s backwards"/>')
    d.add(f'<circle cx="1192" cy="46" r="4" fill="{ACCENT}" style="animation:pulse 2.2s ease-in-out infinite"/>')
    return d.render()


# ── project cards ────────────────────────────────────────────────────────────


def motif(d: Doc, kind: str, x: float, y: float):
    """Small animated glyph in the card's top-right corner (120×70)."""
    g = []
    if kind == "graph":
        pts = [(10, 35), (45, 12), (45, 58), (85, 22), (85, 50), (115, 35)]
        ed = [(0, 1), (0, 2), (1, 3), (2, 4), (3, 5), (4, 5), (1, 4)]
        for a, b in ed:
            g.append(f'<line x1="{pts[a][0]}" y1="{pts[a][1]}" x2="{pts[b][0]}" y2="{pts[b][1]}" stroke="#333"/>')
        for i, (px, py) in enumerate(pts):
            col = DANGER if i == 4 else ACCENT if i == 0 else MUTED
            anim = "animation:pulse 1.4s ease-in-out infinite" if i == 4 else ""
            g.append(f'<circle cx="{px}" cy="{py}" r="{5 if i in (0, 4) else 4}" fill="#0b0b0b" stroke="{col}" stroke-width="1.6" style="{anim}"/>')
    elif kind == "spark":
        path = "M0,48 L15,40 L30,44 L45,30 L60,34 L75,22 L90,28 L105,14 L120,18"
        g.append(f'<line x1="0" x2="120" y1="32" y2="32" stroke="{MUTED}" stroke-dasharray="3 4" opacity=".6"/>')
        g.append(f'<path d="{path}" fill="none" stroke="{ACCENT}" stroke-width="2" stroke-dasharray="200" style="animation:drawl 3s ease-in-out infinite alternate"/>')
        for i, c in enumerate([ACCENT, WARN, DANGER]):
            g.append(f'<circle cx="{84 + i * 14}" cy="62" r="4" fill="{c}" style="opacity:.25;animation:lamp 3s steps(1) {i}s infinite"/>')
    elif kind == "ascii":
        for r, row in enumerate(["@%#*+=-:.", ".:-=+*#%@", "@%#*+=-:."]):
            d.used["monob"] = d.used.get("monob", "") + row
            g.append(f'<text x="0" y="{18 + r * 22}" font-family="monob" font-size="18" letter-spacing="3" fill="{ACCENT}" style="animation:pulse 1.8s ease-in-out {r * 0.3}s infinite">{row}</text>')
    elif kind == "steps":
        for i in range(5):
            cx = 8 + i * 26
            g.append(f'<circle cx="{cx}" cy="35" r="7" fill="#0b0b0b" stroke="#333" stroke-width="1.6" style="animation:stepon 5s ease {i * 0.5}s infinite"/>')
            if i < 4:
                g.append(f'<line x1="{cx + 7}" x2="{cx + 19}" y1="35" y2="35" stroke="#333"/>')
    elif kind == "flow":
        p = "M0,52 C30,52 30,18 60,18 S90,52 120,52"
        g.append(f'<path d="{p}" fill="none" stroke="#333"/>')
        for i in range(3):
            g.append(f'<circle r="4" fill="{ACCENT if i else WARN}"><animateMotion dur="3s" begin="{i}s" repeatCount="indefinite" path="{p}"/></circle>')
        g.append(f'<rect x="48" y="0" width="24" height="12" rx="2" fill="none" stroke="{MUTED}"/>')
    elif kind == "bars":
        for i, hgt in enumerate([46, 34, 26, 18, 12, 8]):
            g.append(f'<rect x="{i * 20}" y="{60 - hgt}" width="12" height="{hgt}" rx="2" fill="{ACCENT if i < 2 else "#3a3a3a"}" '
                     f'style="transform-origin:{i * 20}px 60px;animation:grow 2.4s ease {i * 0.12:.2f}s infinite alternate"/>')
    elif kind == "gauge":
        g.append('<path d="M10,60 A50,50 0 0 1 110,60" fill="none" stroke="#2a2a2a" stroke-width="7" stroke-linecap="round"/>')
        g.append(f'<path d="M10,60 A50,50 0 0 1 110,60" fill="none" stroke="{ACCENT}" stroke-width="7" stroke-linecap="round" stroke-dasharray="157" '
                 f'style="animation:gauge 4s ease-in-out infinite alternate"/>')
    elif kind == "scan":
        for r in range(3):
            for c in range(5):
                g.append(f'<rect x="{c * 24}" y="{r * 22}" width="18" height="16" rx="2" fill="#1c1c1c"/>')
        g.append(f'<rect x="0" y="0" width="42" height="38" rx="3" fill="none" stroke="{ACCENT}" stroke-width="1.8" style="animation:scanbox 4s steps(4) infinite"/>')
    d.add(f'<g transform="translate({x},{y})">{"".join(g)}</g>')


def card(p: dict):
    W, H = 800, 400
    d = Doc(W, H, f"{p['title']} — {p['tagline']} Built with {', '.join(p['stack'])}.")
    frame(d, glow=False)
    d.css.append(
        "@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}"
        "@keyframes drawl{from{stroke-dashoffset:200}to{stroke-dashoffset:0}}"
        "@keyframes lamp{0%{opacity:1}33%,100%{opacity:.2}}"
        "@keyframes stepon{0%,10%{stroke:#333;fill:#0b0b0b}15%,60%{stroke:#3DF2A6;fill:#3DF2A6}70%,100%{stroke:#333;fill:#0b0b0b}}"
        "@keyframes grow{from{transform:scaleY(.35)}to{transform:scaleY(1)}}"
        "@keyframes gauge{from{stroke-dashoffset:157}to{stroke-dashoffset:30}}"
        "@keyframes scanbox{0%{transform:translate(0,0)}25%{transform:translate(72px,0)}50%{transform:translate(72px,22px)}75%{transform:translate(24px,22px)}100%{transform:translate(0,0)}}"
    )
    d.defs.append(f'<radialGradient id="cg" cx="100%" cy="0%" r="70%"><stop offset="0" stop-color="{ACCENT}" stop-opacity=".10"/><stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></radialGradient>')
    d.add(f'<rect width="{W}" height="{H}" rx="16" fill="url(#cg)"/>')
    border_sweep(d, dur=7, delay=-int(p["n"]) * 0.9)

    # top row
    d.text(40, 58, p["n"], "monob", 15, ACCENT, 2)
    d.add(f'<line x1="86" x2="118" y1="53" y2="53" stroke="#333"/>')
    if p["live"]:
        d.add(f'<circle cx="134" cy="53" r="4.5" fill="{ACCENT}" style="animation:pulse 1.6s ease-in-out infinite"/>')
        d.text(146, 58, p["status"], "monob", 14, ACCENT, 2.2)
    else:
        d.text(130, 58, p["status"], "mono", 14, MUTED, 2.2)
    motif(d, p["motif"], W - 40 - 120, 34)

    # title + tagline
    y = 150
    ts = 50
    while measure(p["title"], "display", ts, -1.6) > W - 80 and ts > 34:
        ts -= 1
    d.text(40, y, p["title"], "display", ts, FG, -1.6)
    y += 50
    for i, line in enumerate(wrap(p["tagline"], "display5", 22, W - 80, 3)):
        d.text(40, y + i * 32, line, "display5", 22, "#a8a8a8")

    # chips
    cx, cy = 40, H - 104
    for s in p["stack"]:
        w = measure(s, "mono", 15.5) + 28
        if cx + w > W - 40:
            break
        d.add(f'<rect x="{cx}" y="{cy}" width="{w:.0f}" height="34" rx="17" fill="#0f0f0f" stroke="#2a2a2a"/>')
        d.text(cx + 14, cy + 22.5, s, "mono", 15.5, "#bdbdbd")
        cx += w + 10

    # footer
    d.add(f'<line x1="40" x2="{W - 40}" y1="{H - 50}" y2="{H - 50}" stroke="{LINE}"/>')
    path = "↗ github.com/" + p["repo"]
    limit = (W - 80) - (measure("30% fewer overbookings", "monob", 14) + 24 if p["metric"] else 0)
    while measure(path, "mono", 14) > limit:
        path = path[:-2] + "…" if not path.endswith("…") else path[:-2] + "…"
    d.text(40, H - 21, path, "mono", 14, DIM)
    if p["metric"]:
        a, b = p["metric"]
        txt = f"$ {a} {b}" if a == "pip" else f"{a} {b}"
        d.text(W - 40, H - 21, txt, "monob", 14, ACCENT, 0, "end")
    return d.render()


# ── footer ───────────────────────────────────────────────────────────────────


def footer():
    d = Doc(1200, 190, "$ sudo hire aditya — request accepted, opening contact channel: avkad3@gmail.com")
    frame(d, glow=False)
    d.css.append("@keyframes show{to{opacity:1}}@keyframes hide{to{opacity:0}}@keyframes blink{50%{opacity:0}}@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}"
                 ".o{opacity:0;animation:show .3s ease forwards}")
    cmd = "sudo hire aditya"
    cw = measure(cmd, "mono", 22)
    d.text(44, 66, "$", "monob", 22, ACCENT)
    d.text(74, 66, cmd, "mono", 22, FG)
    d.css.append(f"@keyframes tyf{{from{{transform:translateX(0)}}to{{transform:translateX({cw + 2:.0f}px)}}}}")
    d.add(f'<g style="animation:tyf 1s steps({len(cmd)}) .5s forwards"><rect x="72" y="40" width="{cw + 30:.0f}" height="34" fill="{BG}"/>'
          f'<rect x="73" y="44" width="12" height="27" fill="{ACCENT}" style="animation:hide 0s 1.7s forwards"/></g>')
    d.add('<g class="o" style="animation-delay:1.8s">')
    d.text(44, 108, "[sudo] verifying credentials ...", "mono", 17, MUTED)
    d.add('</g><g class="o" style="animation-delay:2.6s">')
    d.text(44, 140, "[ OK ]", "monob", 17, ACCENT)
    d.text(44 + measure("[ OK ] ", "monob", 17), 140, "Request accepted. Opening contact channel → avkad3@gmail.com", "mono", 17, FG)
    d.add('</g><g class="o" style="animation-delay:3.2s">')
    d.add(f'<rect x="44" y="156" width="11" height="21" fill="{ACCENT}" style="animation:blink 1.05s step-end infinite"/></g>')
    d.add(f'<circle cx="1150" cy="40" r="5" fill="{ACCENT}" style="animation:pulse 2.2s ease-in-out infinite"/>')
    d.text(1136, 45, "CONTACT CHANNEL OPEN", "monob", 11, DIM, 2, "end")
    return d.render()


def main():
    ASSETS.mkdir(exist_ok=True)
    out = {"header.svg": header(), "terminal.svg": terminal(), "impact.svg": impact(), "footer.svg": footer()}
    for idx, slug, title in SECTIONS:
        out[f"section-{slug}.svg"] = section(idx, title)
    for p in PROJECTS:
        out[f"card-{p['id']}.svg"] = card(p)
    for name, svg in out.items():
        (ASSETS / name).write_text(svg, encoding="utf-8")
        print(f"{name:28} {len(svg) / 1024:6.1f} KB")


if __name__ == "__main__":
    main()
