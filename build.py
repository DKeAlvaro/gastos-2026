#!/usr/bin/env python3
"""gastos-2026 — a one-page reading of a year of bank statements.

Design constraints, after the critique:
- six series, not thirteen; charts carry their own labels
- one sentence per block; numbers over adjectives
- the page must answer "where does the money go" above the fold
"""
import sys, html, collections, datetime, importlib.util, os, pathlib, statistics

SCRATCH = ("/data/data/com.termux/files/usr/tmp/claude-10572/"
           "-data-data-com-termux-files-home/b7014fd9-800d-4730-9b7d-a416f0eacad8/scratchpad")
spec = importlib.util.spec_from_file_location("g", SCRATCH + "/gen_report.py")
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)
load, classify = G.load, G.classify

HERE = pathlib.Path(__file__).resolve().parent
FONTS = HERE / ".fonts" / "embedded2.css"

MONTHS = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
          "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
ABBR = ["", "ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
WD = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

GROUP = {
    "Vivienda": "Vivienda", "Universidad": "Universidad",
    "Supermercado": "Comida", "Comidas y bares": "Comida",
    "Transporte": "Moverse", "Viajes": "Moverse",
    "Seguros y salud": "Recibos", "Suscripciones": "Recibos", "Multas e impuestos": "Recibos",
    "Compras": "Vida", "Ocio": "Vida", "Transferencias": "Vida", "Otros": "Vida",
}
G_ORDER = ["Vivienda", "Comida", "Universidad", "Moverse", "Recibos", "Vida"]
G_COLOR = {"Vivienda": "#1F4E9C", "Comida": "#C4661F", "Universidad": "#6B4FA1",
           "Moverse": "#2C7C79", "Recibos": "#8A7A1F", "Vida": "#B0455A"}
CAT_COLOR = {
    "Vivienda": "#1F4E9C", "Universidad": "#6B4FA1", "Supermercado": "#2F7D45",
    "Comidas y bares": "#D07A2E", "Transporte": "#2C7C79", "Compras": "#B0455A",
    "Seguros y salud": "#8A7A1F", "Suscripciones": "#4F6C86", "Ocio": "#8A4468",
    "Viajes": "#3D7FA8", "Multas e impuestos": "#9B2C2C", "Transferencias": "#7C8175",
    "Otros": "#5C6152",
}
DISPLAY = {
    "to payments.holland2stay.com via rabo smart pay": "Holland2Stay",
    "to holland2stay b.v. via stichting mollie payments": "Holland2Stay",
    "to eindhoven university of technology": "TU/e",
    "to technische universiteit eindhoven via stichting mollie payments": "TU/e",
    "to cjib verkeersboetes": "CJIB · multas",
    "to esky.pl s.a.": "ESKY.pl · vuelos",
    "to ns reizigers b.v.": "NS · trenes",
    "ns groep iz ns reizigers": "NS · trenes",
    "to ns internationaal b.v.": "NS International",
    "to marktplaats via online payments stichting": "Marktplaats",
}

def eur(v, dec=0, sign=False):
    s = f"{abs(v):,.{dec}f}".replace(",", "#").replace(".", ",").replace("#", ".")
    if v < 0:
        s = "−" + s
    elif sign and v > 0:
        s = "+" + s
    return s + " €"

def clean(desc):
    d = desc.strip()
    if d.lower() in DISPLAY:
        return DISPLAY[d.lower()]
    low = d.lower()
    if low.startswith(("transfer to", "to hr ", "to mw ")) or "via tikkie" in low \
       or "betaalverzoek" in low or low.startswith("transfer from"):
        return "Traspaso a un particular"
    if "menendez" in low:
        return "Traspaso propio"
    return d

def inc_cat(desc):
    low = desc.lower()
    if "menendez ros alvaro" in low or "hr a menendez ros" in low:
        return "Traspasos propios"
    if "duo" in low:
        return "Beca DUO"
    if any(k in low for k in ("tempo-team", "asml", "bernhard", "mpa vastgoed")):
        return "Nómina"
    if "tikkie" in low or "global collect" in low or "google payment" in low:
        return "Tikkies"
    if "refund" in low or "chargeback" in low or "blablacar" in low or "amovens" in low \
       or "mediamarkt" in low:
        return "Devoluciones"
    if "transfer from" in low:
        return "Familia y amigos"
    return "Otros"

# ------------------------------------------------------------------ charts
def yaxis(o, L, R, T, ph, sc, top, step):
    g = 0
    while g <= top:
        y = T + ph - g * sc
        o.append(f'<line x1="{L}" y1="{y:.1f}" x2="{R}" y2="{y:.1f}" class="gl"/>')
        lbl = f"{g//1000}k" if g and g % 1000 == 0 else f"{g}"
        o.append(f'<text x="{L-8}" y="{y+3.8:.1f}" text-anchor="end" class="ax">{lbl}</text>')
        g += step

def chart_stack(months, bym, small=False):
    W, H = (400, 250) if small else (1000, 330)
    L, R, T, B = (34, 6, 14, 30) if small else (52, 8, 26, 38)
    pw, ph = W - L - R, H - T - B
    peak = max(m["spend"] for m in bym.values())
    steps = [250, 500, 1000, 1500, 2000]
    step = next(c for c in steps if c >= peak / (4 if small else 5))
    top = -(-peak // step) * step
    sc = ph / top
    slot = pw / len(months)
    bw = min(slot * (0.56 if small else 0.52), 54)
    o = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="Gasto por mes y grupo">']
    yaxis(o, L, W - R, T, ph, sc, top, step)
    for i, (ym, m) in enumerate(bym.items()):
        cx = L + slot * i + slot / 2
        x, base = cx - bw / 2, T + ph
        for gname in G_ORDER:
            val = m["groups"].get(gname, 0)
            if not val:
                continue
            h = val * sc
            base -= h
            o.append(f'<rect x="{x:.1f}" y="{base:.1f}" width="{bw:.1f}" height="{max(h-1.4,0.6):.1f}" '
                     f'fill="{G_COLOR[gname]}"><title>{MONTHS[ym[1]]}: {gname} {eur(val)}</title></rect>')
            if not small and h > 22:
                o.append(f'<text x="{cx:.1f}" y="{base+h/2+4:.1f}" text-anchor="middle" class="inbar">{eur(val)}</text>')
        if not small:
            o.append(f'<text x="{cx:.1f}" y="{base-9:.1f}" text-anchor="middle" class="vl">{eur(m["spend"])}</text>')
        o.append(f'<text x="{cx:.1f}" y="{H-9}" text-anchor="middle" class="ax">{ABBR[ym[1]]}</text>')
    o.append(f'<line x1="{L}" y1="{T+ph}" x2="{W-R}" y2="{T+ph}" class="base"/>')
    o.append("</svg>")
    return "".join(o)

def chart_comp(groups, total, small=False):
    W, H = (400, 92) if small else (1000, 54)
    bh = 34 if small else 26
    o = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="Reparto del año">']
    x = 0
    for gname in G_ORDER:
        v = groups.get(gname, 0)
        if not v:
            continue
        w = v / total * W
        o.append(f'<rect x="{x:.1f}" y="0" width="{w:.1f}" height="{bh}" fill="{G_COLOR[gname]}">'
                 f'<title>{gname}: {eur(v)}</title></rect>')
        if w > W * (0.075 if small else 0.09):
            o.append(f'<text x="{x+w/2:.1f}" y="{bh/2+5:.1f}" text-anchor="middle" class="inbar big">{v/total*100:.0f}%</text>')
        x += w
    x = 0
    for gname in G_ORDER:
        v = groups.get(gname, 0)
        if not v:
            continue
        w = v / total * W
        thr = 0.20 if small else 0.09
        if w > W * thr:
            o.append(f'<text x="{x+w/2:.1f}" y="{bh+18:.1f}" text-anchor="middle" class="cl">{gname}</text>')
        x += w
    o.append("</svg>")
    return "".join(o)

def chart_bullet(months, bym, small=False):
    W, H = (400, 250) if small else (1000, 280)
    L, R, T, B = (34, 6, 14, 30) if small else (52, 8, 22, 40)
    pw, ph = W - L - R, H - T - B
    peak = max(max(m["spend"], m["income"]) for m in bym.values())
    steps = [250, 500, 1000, 1500, 2000, 2500]
    step = next(c for c in steps if c >= peak * 1.15 / 4)
    top = -(-peak * 1.15 // step) * step
    sc = ph / top
    slot = pw / len(months)
    bw = min(slot * (0.5 if small else 0.44), 40)
    o = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="Gasto e ingresos por mes">']
    yaxis(o, L, W - R, T, ph, sc, top, step)
    for i, (ym, m) in enumerate(bym.items()):
        cx = L + slot * i + slot / 2
        h = m["spend"] * sc
        o.append(f'<rect x="{cx-bw/2:.1f}" y="{T+ph-h:.1f}" width="{bw:.1f}" height="{max(h,0.6):.1f}" '
                 f'fill="#1F4E9C" fill-opacity=".85"><title>{MONTHS[ym[1]]}: gasto {eur(m["spend"])}</title></rect>')
        yi = T + ph - m["income"] * sc
        o.append(f'<line x1="{cx-slot*0.30:.1f}" y1="{yi:.1f}" x2="{cx+slot*0.30:.1f}" y2="{yi:.1f}" '
                 f'stroke="#1F7A4D" stroke-width="2.6" stroke-linecap="round">'
                 f'<title>{MONTHS[ym[1]]}: ingreso {eur(m["income"])}</title></line>')
        o.append(f'<text x="{cx:.1f}" y="{H-9}" text-anchor="middle" class="ax">{ABBR[ym[1]]}</text>')
    o.append(f'<line x1="{L}" y1="{T+ph}" x2="{W-R}" y2="{T+ph}" class="base"/>')
    o.append("</svg>")
    return "".join(o)

def chart_hbars(items, small=False):
    W = 400 if small else 1000
    row_h = 30 if small else 34
    H = len(items) * row_h + 4
    L, R = (104, 62) if small else (180, 96)
    pw = W - L - R
    mx = max(v for _, v in items)
    o = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="Comercios que más cobran">']
    for i, (name, v) in enumerate(items):
        y = i * row_h
        w = v / mx * pw
        short = name if len(name) <= (14 if small else 26) else name[: (13 if small else 25)] + "…"
        o.append(f'<text x="{L-9}" y="{y+row_h/2+4:.1f}" text-anchor="end" class="lbl">{html.escape(short)}</text>')
        o.append(f'<rect x="{L}" y="{y+8:.1f}" width="{w:.1f}" height="15" rx="2" fill="#1F4E9C"/>')
        o.append(f'<text x="{L+w+7:.1f}" y="{y+row_h/2+4:.1f}" class="vl">{eur(v)}</text>')
    o.append("</svg>")
    return "".join(o)

def chart_weekday(vals, counts, small=False):
    W, H = (400, 230) if small else (1000, 250)
    L, R, T, B = (34, 6, 16, 28) if small else (48, 8, 28, 34)
    pw, ph = W - L - R, H - T - B
    mx = max(vals)
    steps = [250, 500, 1000, 1500]
    step = next(c for c in steps if c >= mx * 1.12 / 4)
    top = -(-mx * 1.12 // step) * step
    sc = ph / top
    slot = pw / 7
    bw = min(slot * (0.52 if small else 0.46), 62)
    o = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="Gasto por día de la semana">']
    yaxis(o, L, W - R, T, ph, sc, top, step)
    for i, v in enumerate(vals):
        cx = L + slot * i + slot / 2
        h = v * sc
        o.append(f'<rect x="{cx-bw/2:.1f}" y="{T+ph-h:.1f}" width="{bw:.1f}" height="{max(h,0.6):.1f}" '
                 f'fill="#1F4E9C"><title>{WD[i]}: {eur(v)} en {counts[i]} cargos</title></rect>')
        if not small:
            o.append(f'<text x="{cx:.1f}" y="{T+ph-h-8:.1f}" text-anchor="middle" class="vl">{eur(v)}</text>')
        o.append(f'<text x="{cx:.1f}" y="{H-9}" text-anchor="middle" class="ax">{WD[i][:3].lower()}</text>')
    o.append(f'<line x1="{L}" y1="{T+ph}" x2="{W-R}" y2="{T+ph}" class="base"/>')
    o.append("</svg>")
    return "".join(o)

# ------------------------------------------------------------------ build
def build(csv_path, outdir="."):
    txs = load(csv_path)
    spend = [t for t in txs if t["amount"] < 0]
    income = [t for t in txs if t["amount"] > 0]
    for t in spend:
        t["cat"] = classify(t["desc"], t["raw"])
        t["grp"] = GROUP.get(t["cat"], "Vida")
    for t in income:
        t["icat"] = inc_cat(t["desc"])
    mkey = lambda t: (t["date"].year, t["date"].month)
    months = sorted({mkey(t) for t in txs})
    today = datetime.date.today()
    first, last = min(t["date"] for t in txs), max(t["date"] for t in txs)
    days = (last - first).days + 1

    bym = collections.OrderedDict()
    for ym in months:
        ms = [t for t in spend if mkey(t) == ym]
        mi = [t for t in income if mkey(t) == ym and t["icat"] != "Traspasos propios"]
        groups = collections.Counter()
        for t in ms:
            groups[t["grp"]] += -t["amount"]
        bym[ym] = {"spend": -sum(t["amount"] for t in ms),
                   "income": sum(t["amount"] for t in mi),
                   "n": len(ms), "groups": groups}

    total = sum(-t["amount"] for t in spend)
    ext_income = sum(t["amount"] for t in income if t["icat"] != "Traspasos propios")
    own = sum(t["amount"] for t in income if t["icat"] == "Traspasos propios")
    gap = ext_income - total

    gt = collections.Counter()
    for t in spend:
        gt[t["grp"]] += -t["amount"]
    ct = collections.Counter()
    for t in spend:
        ct[t["cat"]] += -t["amount"]
    it = collections.Counter()
    for t in income:
        it[t["icat"]] += t["amount"]

    fixed = gt["Vivienda"] + gt["Universidad"] + gt["Recibos"]
    food = gt["Comida"]

    mer = collections.defaultdict(lambda: [0, 0.0, set()])
    for t in spend:
        mer[clean(t["desc"])][0] += 1
        mer[clean(t["desc"])][1] += -t["amount"]
        mer[clean(t["desc"])][2].add(mkey(t))
    top_mer = sorted(mer.items(), key=lambda kv: -kv[1][1])[:8]
    top_mer_rows = [(n, v[1]) for n, v in top_mer]
    duo = sum(v[1] for n, v in top_mer[:2])

    NO_RECUR = ("Supermercado", "Comidas y bares", "Transferencias", "Compras")
    recurring = []
    for name, (n, tot, mons) in mer.items():
        src = [t for t in spend if clean(t["desc"]) == name]
        if len({mkey(t) for t in src}) < 6:
            continue
        if classify(src[0]["desc"], src[0]["raw"]) in NO_RECUR:
            continue
        med = statistics.median([-t["amount"] for t in src])
        if med >= 2:
            recurring.append((name, med, len({mkey(t) for t in src}), tot))
    recurring.sort(key=lambda r: -r[1])
    fixed_monthly = sum(r[1] for r in recurring)

    wd = collections.Counter(); wdn = collections.Counter()
    for t in spend:
        wd[t["date"].weekday()] += -t["amount"]; wdn[t["date"].weekday()] += 1
    tickets = sorted(-t["amount"] for t in spend)
    median_ticket = tickets[len(tickets)//2]
    small = sum(1 for v in tickets if v < 5)
    small_sum = sum(v for v in tickets if v < 5)

    stack, stack_s = chart_stack(months, bym), chart_stack(months, bym, small=True)
    comp, comp_s = chart_comp(gt, total), chart_comp(gt, total, small=True)
    bullet, bullet_s = chart_bullet(months, bym), chart_bullet(months, bym, small=True)
    mer_chart, mer_chart_s = chart_hbars(top_mer_rows), chart_hbars(top_mer_rows, small=True)
    wdv = [wd[i] for i in range(7)]; wdc = [wdn[i] for i in range(7)]
    wd_chart, wd_chart_s = chart_weekday(wdv, wdc), chart_weekday(wdv, wdc, small=True)

    # category table (compact, 13 rows)
    cat_rows = "".join(
        f'<tr><th scope="row"><span class="dot" style="background:{CAT_COLOR.get(c)}"></span>{c}</th>'
        f'<td class="num">{sum(1 for t in spend if t["cat"] == c)}</td>'
        f'<td class="num strong">{eur(ct[c])}</td>'
        f'<td class="num dim">{ct[c]/total*100:.0f}&thinsp;%</td></tr>'
        for c in sorted(ct, key=lambda c: -ct[c]))

    mon_rows2 = "".join(
        f'<tr><th scope="row">{MONTHS[ym[1]]}{" <em>parcial</em>" if (ym[0], ym[1]) == (today.year, today.month) else ""}</th>'
        f'<td class="num strong">{eur(m["spend"])}</td>'
        f'<td class="num dim">{eur(m["income"])}</td>'
        f'<td class="num {"neg" if m["income"] - m["spend"] < 0 else "pos"}">{eur(m["income"]-m["spend"], sign=True)}</td></tr>'
        for ym, m in bym.items())
    mon_rows = "".join(
        f'<tr><th scope="row">{MONTHS[ym[1]]}{" <em>parcial</em>" if (ym[0], ym[1]) == (today.year, today.month) else ""}</th>'
        f'<td class="num">{m["n"]}</td><td class="num strong">{eur(m["spend"])}</td>'
        f'<td class="num dim">{eur(m["income"])}</td>'
        f'<td class="num {"neg" if m["income"] - m["spend"] < 0 else "pos"}">{eur(m["income"]-m["spend"], sign=True)}</td></tr>'
        for ym, m in bym.items())

    rec_rows = "".join(
        f'<tr><th scope="row">{html.escape(n)}</th><td class="num dim">{nm}</td>'
        f'<td class="num strong">{eur(med, 2)}</td><td class="num dim">{eur(tot)}</td></tr>'
        for n, med, nm, tot in recurring)

    fontcss = FONTS.read_text(encoding="utf-8") if FONTS.exists() else ""
    mon_mx = max(months, key=lambda k: bym[k]["spend"])
    mon_mn = min(months, key=lambda k: bym[k]["spend"])
    m10 = bym.get((2026, 10), bym[months[-1]])
    m9 = bym.get((2026, 9), bym[months[-2]])

    doc = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gastos 2026 · Álvaro Menéndez</title>
<meta name="description" content="Un año de extractos en una página: 19.614 € de gasto, 16.368 € de ingresos, seis grupos y qué se repite cada mes.">
<style>
{fontcss}
:root {{ --bg:#F6F7F9; --ink:#0D1117; --muted:#5B6572; --line:#E3E6EC;
        --blue:#1F4E9C; --green:#1F7A4D; --red:#9B2C2C; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink);
  font:400 17px/1.55 "Inter", -apple-system, "Segoe UI", system-ui, sans-serif;
  font-feature-settings:"tnum" 1; -webkit-text-size-adjust:100%; }}
h1,h2,h3,p,ul,ol {{ margin:0; }}
a {{ color:var(--blue); text-underline-offset:3px; }}
.wrap {{ max-width:980px; margin:0 auto; padding:0 28px; }}
@media (max-width:640px) {{ .wrap {{ padding:0 18px; }} }}

nav {{ position:sticky; top:0; z-index:20; background:#F6F7F9EE; backdrop-filter:blur(8px);
  border-bottom:1px solid var(--line); }}
nav .wrap {{ display:flex; gap:20px; overflow-x:auto; padding:11px 28px; font-size:13px;
  scrollbar-width:none; }}
nav .wrap::-webkit-scrollbar {{ display:none; }}
nav a {{ color:var(--muted); text-decoration:none; white-space:nowrap; }}
nav a:hover {{ color:var(--ink); }}
nav .brand {{ color:var(--ink); font-weight:600; margin-right:auto;
  font-family:"Bricolage Grotesque",sans-serif; }}

header {{ padding:68px 0 30px; }}
h1 {{ font-family:"Bricolage Grotesque",sans-serif; font-weight:600;
  font-size:clamp(36px,5.6vw,60px); line-height:1.02; letter-spacing:-.035em; max-width:24ch; }}
h1 span {{ color:var(--blue); }}
.dek {{ margin-top:18px; font-size:clamp(16px,1.9vw,19px); color:#2A3138; max-width:60ch; }}
.kpis {{ display:grid; grid-template-columns:repeat(4,1fr); margin-top:34px; border-top:1px solid var(--ink); }}
.kpis div {{ padding:16px 16px 0 0; }}
.kpis div + div {{ border-left:1px solid var(--line); padding-left:18px; }}
.kpis b {{ display:block; font-family:"Bricolage Grotesque",sans-serif; font-weight:600;
  font-size:clamp(23px,3vw,32px); letter-spacing:-.03em; line-height:1.1; }}
.kpis span {{ display:block; margin-top:5px; font-size:12.5px; color:var(--muted); }}
@media (max-width:720px) {{ .kpis {{ grid-template-columns:1fr 1fr; }}
  .kpis div:nth-child(3) {{ border-left:0; padding-left:0; }}
  .kpis div:nth-child(n+3) {{ border-top:1px solid var(--line); margin-top:14px; }} }}

section {{ padding:46px 0 6px; border-top:1px solid var(--line); scroll-margin-top:56px; }}
h2 {{ font-family:"Bricolage Grotesque",sans-serif; font-weight:600; font-size:clamp(23px,2.8vw,29px);
  letter-spacing:-.02em; }}
.note {{ margin-top:8px; font-size:15.5px; color:#3A424B; max-width:72ch; }}
h3 {{ font-family:"Bricolage Grotesque",sans-serif; font-weight:600; font-size:17px; margin:26px 0 4px; }}

figure {{ margin:22px 0 6px; }}
figcaption {{ margin-top:10px; font-size:13px; color:var(--muted); }}
.chart {{ width:100%; height:auto; display:block; overflow:visible; }}
.gl {{ stroke:#E7EAEF; stroke-width:1; }}
.base {{ stroke:#0D1117; stroke-width:1.2; }}
text.ax {{ font-family:"Inter",sans-serif; font-size:11px; fill:#77808D; }}
text.vl {{ font-family:"Inter",sans-serif; font-size:11.5px; font-weight:600; fill:#20262D; }}
text.lbl {{ font-family:"Inter",sans-serif; font-size:13px; fill:#20262D; }}
text.inbar {{ font-family:"Inter",sans-serif; font-size:11px; font-weight:600; fill:#fff; }}
text.inbar.big {{ font-size:13px; }}
text.cl {{ font-family:"Inter",sans-serif; font-size:12.5px; fill:#4A5461; }}
.cn {{ display:none; }}
@media (max-width:640px) {{ .cw {{ display:none; }} .cn {{ display:block; }} }}
.legend {{ display:flex; flex-wrap:wrap; gap:6px 16px; margin-top:10px; }}
.lg {{ font-size:12.5px; color:var(--muted); display:inline-flex; align-items:center; gap:6px; }}
.lg i {{ width:10px; height:10px; border-radius:2px; display:block; }}

table {{ width:100%; border-collapse:collapse; margin-top:8px; }}
thead th {{ font-size:12px; font-weight:500; color:var(--muted); text-align:left;
  padding:0 0 7px; border-bottom:1px solid var(--ink); }}
tbody th, tbody td {{ padding:9px 0; border-bottom:1px solid var(--line); font-size:14px; }}
tbody th {{ font-weight:500; text-align:left; }}
.num {{ text-align:right; white-space:nowrap; font-variant-numeric:tabular-nums; padding-left:12px; }}
.strong {{ font-weight:600; }} .dim {{ color:var(--muted); }}
.pos {{ color:var(--green); }} .neg {{ color:var(--red); }}
.dot {{ display:inline-block; width:8px; height:8px; border-radius:2px; margin-right:8px; }}
tbody tr em {{ font-style:normal; color:var(--blue); font-size:11.5px; }}
@media (max-width:640px) {{ .num {{ font-size:13px; padding-left:8px; }} }}

.split {{ display:grid; grid-template-columns:1.15fr .85fr; gap:38px; margin-top:22px; }}
@media (max-width:820px) {{ .split {{ grid-template-columns:1fr; gap:16px; }} }}
.sub {{ font-size:13.5px; color:var(--muted); }}

.notes {{ padding:38px 0 64px; }}
.notes li {{ font-size:13.5px; color:#3A424B; margin-bottom:8px; max-width:80ch; }}
.notes ul {{ padding-left:18px; }}
footer {{ border-top:1px solid var(--line); padding:20px 0 44px; font-size:12.5px; color:var(--muted);
  display:flex; justify-content:space-between; gap:16px; }}
:focus-visible {{ outline:2px solid var(--blue); outline-offset:3px; }}
@media (prefers-reduced-motion:reduce) {{ * {{ transition:none !important; }} }}
</style>
</head>
<body>
<nav><div class="wrap">
  <span class="brand">Gastos 2026</span>
  <a href="#donde">Dónde</a><a href="#ingresos">Ingresos</a><a href="#meses">Meses</a>
  <a href="#comercios">Comercios</a><a href="#cuando">Cuándo</a><a href="#metodo">Método</a>
</div></nav>

<header><div class="wrap">
  <h1>El {fixed/total*100:.0f}&thinsp;% de mi gasto <span>no lo decido yo</span></h1>
  <p class="dek">Alquiler, matrícula, seguro y recibos: {eur(fixed)} de {eur(total)} en {days} días.
    El resto —comida, viajes, vida— son {eur(total-fixed)}.</p>
  <div class="kpis">
    <div><b>{eur(total)}</b><span>gasto en {days} días</span></div>
    <div><b>{eur(ext_income)}</b><span>ingresos externos</span></div>
    <div><b>{eur(gap, sign=True)}</b><span>ingresos − gasto</span></div>
    <div><b>{eur(total/len(bym))}</b><span>media al mes</span></div>
  </div>
</div></header>

<section id="donde"><div class="wrap">
  <h2>Dónde se va</h2>
  <p class="note">Seis grupos. Vivienda y universidad son {eur(gt['Vivienda']+gt['Universidad'])}:
    el {(gt['Vivienda']+gt['Universidad'])/total*100:.0f}&thinsp;% del año se paga solo.</p>
  <figure><div class="cw">{comp}</div><div class="cn">{comp_s}</div></figure>
  <figure><div class="cw">{stack}</div><div class="cn">{stack_s}</div>
    <figcaption>Cada barra es un mes. La base azul es el alquiler: {eur(gt['Vivienda']/len(bym))} al mes
      que aparecen siempre en el mismo sitio.</figcaption>
    <div class="legend">{''.join(f'<span class="lg"><i style="background:{G_COLOR[g]}"></i>{g}</span>' for g in G_ORDER)}</div>
  </figure>
  <h3>Las trece categorías</h3>
  <table><thead><tr><th>Categoría</th><th class="num">Cargos</th><th class="num">Total</th>
    <th class="num">Peso</th></tr></thead><tbody>{cat_rows}</tbody></table>
</div></section>

<section id="ingresos"><div class="wrap">
  <h2>Ingresos</h2>
  <p class="note">{eur(ext_income)} de ingresos externos frente a {eur(total)} de gasto.</p>
  <figure>
    <div class="legend" style="margin:0 0 10px">
      <span class="lg"><i style="background:#1F4E9C"></i>gasto</span>
      <span class="lg"><i style="background:#1F7A4D;height:3px;border-radius:2px"></i>ingreso</span>
    </div>
    <div class="cw">{bullet}</div><div class="cn">{bullet_s}</div>
    <figcaption>Barra: gasto. Línea verde: ingresos. Cuando la línea cae dentro de la barra,
      ese mes se pagó con ahorro.</figcaption>
  </figure>
  <div class="split">
    <div>
      <h3>De dónde viene</h3>
      <table><tbody>
        <tr><th scope="row">Nómina</th><td class="num strong">{eur(it['Nómina'])}</td><td class="num dim">{it['Nómina']/ext_income*100:.0f}&thinsp;%</td></tr>
        <tr><th scope="row">Beca DUO</th><td class="num strong">{eur(it['Beca DUO'])}</td><td class="num dim">{it['Beca DUO']/ext_income*100:.0f}&thinsp;%</td></tr>
        <tr><th scope="row">Familia y amigos</th><td class="num strong">{eur(it['Familia y amigos'])}</td><td class="num dim">{it['Familia y amigos']/ext_income*100:.0f}&thinsp;%</td></tr>
        <tr><th scope="row">Devoluciones</th><td class="num strong">{eur(it['Devoluciones'])}</td><td class="num dim">{it['Devoluciones']/ext_income*100:.0f}&thinsp;%</td></tr>
      </tbody></table>
    </div>
    <div>
      <h3>El hueco</h3>
      <p class="sub">La diferencia, {eur(-gap)}, la cubrieron {eur(own)} movidos desde mis otras
        cuentas. Con todo contado, el año cierra en {eur(ext_income-total+own, sign=True)}.</p>
    </div>
  </div>
</div></section>

<section id="meses"><div class="wrap">
  <h2>Mes a mes</h2>
  <p class="note">{MONTHS[mon_mx[1]]} ({eur(bym[mon_mx]['spend'])}) y {MONTHS[mon_mn[1]].lower()}
    ({eur(bym[mon_mn]['spend'])}) se llevan {bym[mon_mx]['spend']/bym[mon_mn]['spend']:.1f}× de diferencia.
    En octubre pesa el alquiler cobrado dos veces ({eur(643.58)} el día 6 y otro el 30).</p>
  <table><thead><tr><th>Mes</th><th class="num">Gasto</th>
    <th class="num">Ingreso</th><th class="num">Neto</th></tr></thead><tbody>{mon_rows2}</tbody></table>
</div></section>

<section id="comercios"><div class="wrap">
  <h2>Quién cobra</h2>
  <p class="note">Ocho comercios se llevan {sum(v for _, v in top_mer_rows)/total*100:.0f}&thinsp;% del gasto.
    El casero y la universidad, {eur(duo)}.</p>
  <figure><div class="cw">{mer_chart}</div><div class="cn">{mer_chart_s}</div>
  </figure>
  <h3>Lo que se repite</h3>
  <table><thead><tr><th>Comercio</th><th class="num">Meses</th><th class="num">Importe típico</th>
    <th class="num">Total</th></tr></thead><tbody>{rec_rows}</tbody></table>
  <p class="sub" style="margin-top:10px">{eur(fixed_monthly)} al mes en cargos que se repiten
    ({eur(fixed_monthly*12)} al año).</p>
</div></section>

<section id="cuando"><div class="wrap">
  <h2>Cuándo</h2>
  <p class="note">Martes y viernes se llevan el {(wd[1]+wd[4])/total*100:.0f}&thinsp;% del gasto.
    El {small/len(spend)*100:.0f}&thinsp;% de los cargos no llega a 5&nbsp;€; la mediana es {eur(median_ticket,2)}.</p>
  <figure><div class="cw">{wd_chart}</div><div class="cn">{wd_chart_s}</div>
    <figcaption>Gasto por día de la semana. El sábado es el más barato: {eur(wd[5])}.</figcaption>
  </figure>
</div></section>

<section id="metodo" class="notes"><div class="wrap">
  <h2>Método</h2>
  <ul>
    <li>Extracto consolidado de Revolut, 01/01/2026–{last.strftime('%d/%m/%Y')}: {len(txs)} apuntes.</li>
    <li>Categorías por reglas propias sobre el comercio, no las del banco.</li>
    <li>Traspasos entre cuentas a mi nombre ({eur(own)}) fuera de los ingresos. Transferencias a personas,
      sin nombre. Noviembre, parcial (día {today.day}).</li>
  </ul>
</div></section>

<div class="wrap"><footer>
  <span>Álvaro Menéndez · {today.strftime('%d/%m/%Y')}</span>
  <span><a href="https://dkealvaro.github.io/">dkealvaro.github.io</a></span>
</footer></div>
</body>
</html>"""
    path = os.path.join(outdir, "index.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(doc)
    print(f"wrote {path} ({len(doc)/1024:.1f} kB) · fixed {fixed:.0f} · total {total:.0f}")

if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ".")
