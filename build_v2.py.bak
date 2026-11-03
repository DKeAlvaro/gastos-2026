#!/usr/bin/env python3
"""gastos-2026 — full spending analysis from a Revolut consolidated statement."""
import re, sys, html, collections, datetime, importlib.util, os, pathlib, statistics

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

CAT_ORDER = ["Vivienda", "Universidad", "Supermercado", "Comidas y bares", "Transporte",
             "Compras", "Seguros y salud", "Suscripciones", "Ocio", "Viajes",
             "Multas e impuestos", "Transferencias", "Otros"]
COLORS = {
    "Vivienda": "#1F4E9C", "Universidad": "#6B4FA1", "Supermercado": "#2F7D45",
    "Comidas y bares": "#D07A2E", "Transporte": "#2C7C79", "Compras": "#B0455A",
    "Seguros y salud": "#8A7A1F", "Suscripciones": "#4F6C86", "Ocio": "#8A4468",
    "Viajes": "#3D7FA8", "Multas e impuestos": "#9B2C2C", "Transferencias": "#7C8175",
    "Otros": "#5C6152",
}
INC_COLORS = {"Nómina": "#1F7A4D", "Beca DUO": "#2F6FBF", "Familia y amigos": "#7A5AA8",
              "Devoluciones": "#B4763F", "Tikkies y micro-ingresos": "#7C8175",
              "Traspasos propios": "#B9BDB2", "Otros": "#5C6152"}

def eur(v, dec=0, sign=False):
    s = f"{abs(v):,.{dec}f}".replace(",", "#").replace(".", ",").replace("#", ".")
    if v < 0:
        s = "−" + s
    elif sign and v > 0:
        s = "+" + s
    return s + " €"

def pct(v, t):
    return f"{v/t*100:.0f}&thinsp;%"

DISPLAY = {
    "to payments.holland2stay.com via rabo smart pay": "Holland2Stay (Rabo Smart Pay)",
    "to holland2stay b.v. via stichting mollie payments": "Holland2Stay (Mollie)",
    "to eindhoven university of technology": "TU/e (Mollie)",
    "to technische universiteit eindhoven via stichting mollie payments": "TU/e (Mollie)",
    "to cjib verkeersboetes": "CJIB · multas de tráfico",
    "to esky.pl s.a.": "ESKY.pl · vuelos",
    "to ns reizigers b.v.": "NS · trenes",
    "to ns internationaal b.v.": "NS International",
    "to marktplaats via online payments stichting": "Marktplaats",
    "to belastingdienst": "Belastingdienst",
    "to viervenues": "Fourvenues",
    "to ov-chipkaart/trans link systems": "OV-chipkaart",
    "to barbershop new look": "Barbería New Look",
    "to iwan.nl b.v.": "Iwan.nl",
    "ns groep iz ns reizigers": "NS · trenes",
}

def clean(desc):
    d = desc.strip()
    if d.lower() in DISPLAY:
        return DISPLAY[d.lower()]
    low = d.lower()
    if low.startswith(("transfer to", "to hr ", "to mw ")) or "via tikkie" in low \
       or "betaalverzoek" in low or low.startswith("transfer from"):
        return "Traspaso a un particular"
    if "menendez" in low:
        return "Traspaso a cuenta propia"
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
        return "Tikkies y micro-ingresos"
    if "refund" in low or "chargeback" in low or "blablacar" in low or "amovens" in low \
       or "mediamarkt" in low:
        return "Devoluciones"
    if "transfer from" in low:
        return "Familia y amigos"
    return "Otros"

# ---------------------------------------------------------------- charts
def svg_open(w, h, label):
    return (f'<svg viewBox="0 0 {w} {h}" class="chart" role="img" aria-label="{label}" '
            f'preserveAspectRatio="xMidYMid meet">')

def grid_lines(out, L, R, T, ph, scale, top_v, step_v, fs):
    g = 0
    while g <= top_v:
        y = T + ph - g * scale
        out.append(f'<line x1="{L}" y1="{y:.1f}" x2="{R}" y2="{y:.1f}" class="gl"/>')
        lbl = f"{g//1000}k" if g and g % 1000 == 0 else f"{g}"
        out.append(f'<text x="{L-10}" y="{y+fs*0.34:.1f}" text-anchor="end" class="ax">{lbl}</text>')
        g += step_v

def chart_stack(months, by_month, W=1000, H=340, small=False):
    L, R, T, B = 56, 10, 24, 42
    pw, ph = W - L - R, H - T - B
    peak = max(m["spend"] for m in by_month.values())
    cands = [50, 100, 200, 250, 500, 1000, 2000, 2500, 5000]
    step_v = next(c for c in cands if c >= peak / (4 if small else 6))
    top_v = -(-peak // step_v) * step_v
    scale = ph / top_v
    slot = pw / len(months)
    bw = min(slot * 0.58, 52)
    out = [svg_open(W, H, "Gasto mensual por categoría")]
    grid_lines(out, L, R, T, ph, scale, top_v, step_v, 11 if not small else 13)
    for i, (y_, mo) in enumerate(months):
        m = by_month[(y_, mo)]
        cx = L + slot * i + slot / 2
        x, base = cx - bw / 2, T + ph
        for cat, val in sorted(m["cats"].items(), key=lambda kv: -kv[1]):
            h = val * scale
            base -= h
            out.append(f'<rect x="{x:.1f}" y="{base:.1f}" width="{bw:.1f}" height="{max(h-1.2,0.6):.1f}" '
                       f'fill="{COLORS.get(cat,"#5C6152")}" rx="1.5"><title>{MONTHS[mo]}, {cat}: {eur(val)}</title></rect>')
        if not small:
            out.append(f'<text x="{cx:.1f}" y="{base-10:.1f}" text-anchor="middle" class="vl">{eur(m["spend"])}</text>')
        out.append(f'<text x="{cx:.1f}" y="{H-14}" text-anchor="middle" class="ax">{ABBR[mo]}</text>')
    out.append(f'<line x1="{L}" y1="{T+ph}" x2="{W-R}" y2="{T+ph}" class="base"/>')
    out.append("</svg>")
    return "".join(out)

def chart_income(months, by_month, W=1000, H=300):
    L, R, T, B = 56, 10, 28, 42
    pw, ph = W - L - R, H - T - B
    peak = max(max(m["spend"], m["income"] or 0) for m in by_month.values())
    cands = [50, 100, 200, 250, 500, 1000, 2000, 2500, 5000]
    step_v = next(c for c in cands if c >= peak / 5)
    top_v = -(-peak // step_v) * step_v
    scale = ph / top_v
    slot = pw / len(months)
    bw = min(slot * 0.26, 26)
    out = [svg_open(W, H, "Ingresos frente a gasto por mes")]
    grid_lines(out, L, R, T, ph, scale, top_v, step_v, 11)
    for i, (y_, mo) in enumerate(months):
        m = by_month[(y_, mo)]
        cx = L + slot * i + slot / 2
        for val, dx, col in ((m["income"], -bw - 2, "#1F7A4D"), (m["spend"], 2, "#1F4E9C")):
            h = (val or 0) * scale
            out.append(f'<rect x="{cx+dx:.1f}" y="{T+ph-h:.1f}" width="{bw:.1f}" height="{max(h,0.6):.1f}" '
                       f'fill="{col}" rx="1.5"><title>{MONTHS[mo]}: {eur(val or 0)}</title></rect>')
        out.append(f'<text x="{cx:.1f}" y="{H-14}" text-anchor="middle" class="ax">{ABBR[mo]}</text>')
    out.append(f'<line x1="{L}" y1="{T+ph}" x2="{W-R}" y2="{T+ph}" class="base"/>')
    out.append("</svg>")
    return "".join(out)

def chart_hbars(items, W=1000, row_h=30):
    H = len(items) * row_h + 8
    L, R = 190, 84
    pw = W - L - R
    mx = max(v for _, v in items)
    out = [svg_open(W, H, "Gasto por categoría")]
    for i, (name, v) in enumerate(items):
        y = i * row_h
        w = v / mx * pw
        out.append(f'<text x="{L-14}" y="{y+row_h/2+4:.1f}" text-anchor="end" class="lbl">{name}</text>')
        out.append(f'<rect x="{L}" y="{y+7:.1f}" width="{w:.1f}" height="14" rx="2" fill="{COLORS.get(name,"#5C6152")}"/>')
        out.append(f'<text x="{L+w+10:.1f}" y="{y+row_h/2+4:.1f}" class="vl">{eur(v)}</text>')
    out.append("</svg>")
    return "".join(out)

def chart_weekday(vals, counts, W=1000, H=270):
    L, R, T, B = 48, 10, 30, 36
    pw, ph = W - L - R, H - T - B
    mx = max(vals)
    cands = [50, 100, 200, 250, 500, 1000, 1500, 2000, 2500, 5000]
    step_v = next(c for c in cands if c >= mx * 1.12 / 4)
    top_v = -(-mx * 1.12 // step_v) * step_v
    scale = ph / top_v
    slot = pw / 7
    bw = min(slot * 0.5, 60)
    out = [svg_open(W, H, "Gasto por día de la semana")]
    grid_lines(out, L, R, T, ph, scale, top_v, step_v, 11)
    for i, v in enumerate(vals):
        cx = L + slot * i + slot / 2
        h = v * scale
        out.append(f'<rect x="{cx-bw/2:.1f}" y="{T+ph-h:.1f}" width="{bw:.1f}" height="{max(h,0.6):.1f}" '
                   f'fill="#1F4E9C" rx="2"><title>{WD[i]}: {eur(v)} en {counts[i]} cargos</title></rect>')
        out.append(f'<text x="{cx:.1f}" y="{T+ph-h-8:.1f}" text-anchor="middle" class="vl">{eur(v)}</text>')
        out.append(f'<text x="{cx:.1f}" y="{H-12}" text-anchor="middle" class="ax">{WD[i][:3].lower()}</text>')
    out.append(f'<line x1="{L}" y1="{T+ph}" x2="{W-R}" y2="{T+ph}" class="base"/>')
    out.append("</svg>")
    return "".join(out)

# ---------------------------------------------------------------- build
def build(csv_path, outdir="."):
    txs = load(csv_path)
    spend = [t for t in txs if t["amount"] < 0]
    income = [t for t in txs if t["amount"] > 0]
    for t in spend:
        t["cat"] = classify(t["desc"], t["raw"])
    for t in income:
        t["icat"] = inc_cat(t["desc"])
    mkey = lambda t: (t["date"].year, t["date"].month)
    months = sorted({mkey(t) for t in txs})
    today = datetime.date.today()
    first, last = min(t["date"] for t in txs), max(t["date"] for t in txs)
    days = (last - first).days + 1

    by_month = collections.OrderedDict()
    for ym in months:
        ms = [t for t in spend if mkey(t) == ym]
        mi = [t for t in income if mkey(t) == ym and t["icat"] != "Traspasos propios"]
        cats = collections.Counter()
        for t in ms:
            cats[t["cat"]] += -t["amount"]
        by_month[ym] = {"spend": -sum(t["amount"] for t in ms), "income": sum(t["amount"] for t in mi),
                        "n": len(ms), "cats": cats}

    total = sum(-t["amount"] for t in spend)
    ext_income = sum(t["amount"] for t in income if t["icat"] != "Traspasos propios")
    own_transfers = sum(t["amount"] for t in income if t["icat"] == "Traspasos propios")
    gap = ext_income - total

    cat_total = collections.Counter()
    for t in spend:
        cat_total[t["cat"]] += -t["amount"]
    inc_total = collections.Counter()
    for t in income:
        inc_total[t["icat"]] += t["amount"]

    FIXED = ("Vivienda", "Universidad", "Seguros y salud", "Suscripciones")
    fixed = sum(cat_total[c] for c in FIXED)
    variable = total - fixed

    sup, out_food = cat_total["Supermercado"], cat_total["Comidas y bares"]
    sup_n = sum(1 for t in spend if t["cat"] == "Supermercado")
    out_n = sum(1 for t in spend if t["cat"] == "Comidas y bares")

    mer = collections.defaultdict(lambda: [0, 0.0, set()])
    for t in spend:
        mer[t["desc"]][0] += 1
        mer[t["desc"]][1] += -t["amount"]
        mer[t["desc"]][2].add(mkey(t))
    top_mer = sorted(mer.items(), key=lambda kv: -kv[1][1])[:12]

    NO_RECUR = ("Supermercado", "Comidas y bares", "Transferencias", "Compras")
    recurring = []
    for name, (n, tot, mons) in mer.items():
        if len(mons) < 6:
            continue
        cat = classify(name, "Merchant")
        if cat in NO_RECUR:
            continue
        med = statistics.median([-t["amount"] for t in spend if t["desc"] == name])
        if med >= 2:
            recurring.append((name, med, len(mons), tot))
    recurring.sort(key=lambda r: -r[1])
    fixed_monthly = sum(r[1] for r in recurring)

    wd = collections.Counter(); wdn = collections.Counter()
    for t in spend:
        wd[t["date"].weekday()] += -t["amount"]; wdn[t["date"].weekday()] += 1
    tickets = sorted(-t["amount"] for t in spend)
    median_ticket = tickets[len(tickets)//2]
    small = sum(1 for v in tickets if v < 5)
    days_amt = collections.Counter()
    for t in spend:
        days_amt[t["date"]] += -t["amount"]
    big_days = days_amt.most_common(5)

    stack_chart = chart_stack(months, by_month)
    stack_chart_s = chart_stack(months, by_month, W=400, H=250, small=True)
    income_chart = chart_income(months, by_month)
    cats_chart = chart_hbars([(c, cat_total[c]) for c in CAT_ORDER if cat_total.get(c)])
    wd_chart = chart_weekday([wd[i] for i in range(7)], [wdn[i] for i in range(7)])

    legend = " ".join(f'<span class="lg"><i style="background:{COLORS[c]}"></i>{c}</span>'
                      for c in CAT_ORDER if cat_total.get(c))

    inc_rows = []
    for cat, v in inc_total.most_common():
        srcs = collections.Counter()
        for t in income:
            if t["icat"] == cat:
                srcs[clean(t["desc"]).replace("Payment from ", "").replace("Transfer from ", "").title()] += t["amount"]
        detail = " · ".join(f"{html.escape(s)} {eur(val)}" for s, val in srcs.most_common(3))
        inc_rows.append(f"""<tr><th scope="row"><span class="dot" style="background:{INC_COLORS.get(cat,'#5C6152')}"></span>{cat}
          <span class="src">{detail}</span></th>
          <td class="num strong">{eur(v)}</td><td class="num dim">{pct(v, sum(inc_total.values()))}</td></tr>""")

    cat_rows = []
    for c in CAT_ORDER:
        if not cat_total.get(c):
            continue
        n = sum(1 for t in spend if t["cat"] == c)
        cat_rows.append(f"""<tr><th scope="row"><span class="dot" style="background:{COLORS[c]}"></span>{c}</th>
          <td class="num">{n}</td><td class="num dim">{eur(cat_total[c]/n,1)}</td>
          <td class="num strong">{eur(cat_total[c])}</td><td class="num dim">{pct(cat_total[c], total)}</td></tr>""")

    mon_rows = []
    for (y_, mo), m in by_month.items():
        net = m["income"] - m["spend"]
        partial = (y_, mo) == (today.year, today.month)
        dom, domv = m["cats"].most_common(1)[0]
        mon_rows.append(f"""<tr>
          <th scope="row">{MONTHS[mo]}{' <em>parcial</em>' if partial else ''}
            <span class="src">pesa sobre todo: {dom.lower()}, {pct(domv, m['spend'])}</span></th>
          <td class="num">{m['n']}</td>
          <td class="num strong">{eur(m['spend'])}</td>
          <td class="num dim">{eur(m['income'])}</td>
          <td class="num {'neg' if net < 0 else 'pos'}">{eur(net, sign=True)}</td></tr>""")

    mer_rows = []
    for name, (n, tot, mons) in top_mer:
        mer_rows.append(f"""<tr><th scope="row">{html.escape(clean(name))}</th>
          <td class="num">{n}</td><td class="num dim">{len(mons)} meses</td>
          <td class="num dim">{eur(tot/n,1)}</td><td class="num strong">{eur(tot)}</td></tr>""")

    rec_rows = []
    for name, med, nmon, tot in recurring[:8]:
        rec_rows.append(f"""<tr><th scope="row">{html.escape(clean(name))}</th>
          <td class="num dim">{nmon}</td><td class="num strong">{eur(med,2)}</td>
          <td class="num dim">{eur(tot)}</td></tr>""")

    biggest = sorted(spend, key=lambda t: t["amount"])[:6]
    big_rows = "".join(f"""<li><span class="d">{t['date'].day} {ABBR[t['date'].month]}</span>
        <span class="t">{html.escape(clean(t['desc']))}</span>
        <span class="c">{t['cat'].lower()}</span>
        <span class="a">{eur(-t['amount'], 2)}</span></li>""" for t in biggest)

    top3 = cat_total.most_common(3)
    duo_names = [n for n, v in top_mer[:2]]
    moo = sum(v[1] for n, v in top_mer[:2])
    share_duo = moo / total
    fontcss = FONTS.read_text(encoding="utf-8") if FONTS.exists() else ""
    mon9 = by_month.get((2026, 9), by_month[months[-2]])
    mon10 = by_month.get((2026, 10), by_month[months[-1]])
    mon5 = by_month.get((2026, 5), by_month[months[len(months)//2]])
    mon8 = by_month.get((2026, 8), by_month[months[-3]])
    mon_mx = max(months, key=lambda k: by_month[k]["spend"])
    mon_mn = min(months, key=lambda k: by_month[k]["spend"])

    doc = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>2026: un año de gastos · Álvaro Menéndez</title>
<meta name="description" content="Análisis de 878 cargos y 16.000 € de ingresos durante 2026: de dónde viene el dinero, en qué se va, mes a mes, comercios recurrentes y patrones semanales.">
<style>
{fontcss}
:root {{
  --bg:#F6F7F9; --paper:#FFFFFF; --ink:#0D1117; --muted:#5B6572; --line:#E3E6EC;
  --blue:#1F4E9C; --green:#1F7A4D; --red:#9B2C2C;
}}
* {{ box-sizing:border-box; }}
html {{ scroll-behavior:smooth; }}
body {{ margin:0; background:var(--bg); color:var(--ink);
  font:400 17px/1.62 "Inter", -apple-system, "Segoe UI", system-ui, sans-serif;
  font-feature-settings:"tnum" 1; -webkit-text-size-adjust:100%; }}
h1,h2,h3,p,ul,ol,dl,dd {{ margin:0; }}
a {{ color:var(--blue); text-decoration-thickness:1px; text-underline-offset:3px; }}
.wrap {{ max-width:1040px; margin:0 auto; padding:0 28px; }}
@media (max-width:640px) {{ .wrap {{ padding:0 18px; }} }}

nav.toc {{ position:sticky; top:0; z-index:20; background:#F6F7F9ee; backdrop-filter:blur(8px);
  border-bottom:1px solid var(--line); }}
nav.toc .wrap {{ display:flex; gap:22px; overflow-x:auto; padding-top:12px; padding-bottom:12px;
  font-size:13.5px; scrollbar-width:none; }}
nav.toc .wrap::-webkit-scrollbar {{ display:none; }}
nav.toc a {{ color:var(--muted); text-decoration:none; white-space:nowrap; }}
nav.toc a:hover {{ color:var(--ink); }}
nav.toc .brand {{ color:var(--ink); font-weight:600; margin-right:auto;
  font-family:"Bricolage Grotesque",sans-serif; letter-spacing:-.01em; }}

header.hero {{ padding:76px 0 46px; }}
h1 {{ font-family:"Bricolage Grotesque",sans-serif; font-weight:600;
  font-size:clamp(38px,6.4vw,68px); line-height:1.0; letter-spacing:-.035em; }}
h1 .accent {{ color:var(--blue); }}
.lede {{ margin-top:22px; font-size:clamp(17px,2vw,20px); line-height:1.55; color:#2A3138; max-width:64ch; }}
.byline {{ margin-top:22px; font-size:13.5px; color:var(--muted); }}
.kpis {{ display:grid; grid-template-columns:repeat(4,1fr); gap:0; margin-top:42px;
  border-top:1px solid var(--ink); }}
.kpis div {{ padding:18px 18px 0 0; }}
.kpis div + div {{ border-left:1px solid var(--line); padding-left:20px; }}
.kpis b {{ display:block; font-family:"Bricolage Grotesque",sans-serif; font-weight:600;
  font-size:clamp(24px,3.2vw,34px); letter-spacing:-.03em; line-height:1.1; }}
.kpis span {{ display:block; margin-top:6px; font-size:13px; color:var(--muted); }}
@media (max-width:720px) {{ .kpis {{ grid-template-columns:1fr 1fr; }}
  .kpis div:nth-child(3) {{ border-left:0; padding-left:0; }}
  .kpis div:nth-child(n+3) {{ border-top:1px solid var(--line); margin-top:16px; }} }}

section {{ padding:56px 0 8px; border-top:1px solid var(--line); scroll-margin-top:64px; }}
h2 {{ font-family:"Bricolage Grotesque",sans-serif; font-weight:600; font-size:clamp(25px,3.2vw,33px);
  letter-spacing:-.02em; line-height:1.15; }}
.kicker {{ font-size:13px; color:var(--muted); margin-bottom:8px; }}
.intro {{ margin-top:14px; font-size:17px; color:#333B44; max-width:70ch; }}
h3 {{ font-family:"Bricolage Grotesque",sans-serif; font-weight:600; font-size:19px;
  letter-spacing:-.01em; margin:34px 0 10px; }}

.figure {{ margin:30px 0 8px; background:var(--paper); border:1px solid var(--line);
  padding:22px 22px 14px; }}
.figure figcaption {{ margin-top:12px; font-size:13px; color:var(--muted); line-height:1.5; }}
.chart {{ width:100%; height:auto; display:block; overflow:visible; }}
.gl {{ stroke:#E9ECF1; stroke-width:1; }}
.base {{ stroke:#0D1117; stroke-width:1.2; }}
text.ax {{ font-family:"Inter",sans-serif; font-size:11px; fill:#77808D; }}
text.vl {{ font-family:"Inter",sans-serif; font-size:11px; font-variant-numeric:tabular-nums; fill:#20262D; font-weight:500; }}
text.lbl {{ font-family:"Inter",sans-serif; font-size:12.5px; fill:#20262D; }}
.legend {{ display:flex; flex-wrap:wrap; gap:6px 16px; margin-top:16px; }}
.lg {{ font-size:12.5px; color:var(--muted); display:inline-flex; align-items:center; gap:6px; }}
.lg i {{ width:10px; height:10px; border-radius:2px; display:block; }}
.chart-narrow {{ display:none; }}
@media (max-width:640px) {{ .chart-wide {{ display:none; }} .chart-narrow {{ display:block; }}
  .legend {{ display:none; }} }}

table {{ width:100%; border-collapse:collapse; margin-top:10px; }}
thead th {{ font-size:12px; font-weight:500; color:var(--muted); text-align:left;
  padding:0 0 8px; border-bottom:1px solid var(--ink); }}
tbody th, tbody td {{ padding:11px 0; border-bottom:1px solid var(--line); font-size:14.5px; }}
tbody th {{ font-weight:500; text-align:left; }}
.num {{ text-align:right; white-space:nowrap; font-variant-numeric:tabular-nums; padding-left:14px; }}
.strong {{ font-weight:600; }}
.dim {{ color:var(--muted); }}
.pos {{ color:var(--green); }} .neg {{ color:var(--red); }}
.dot {{ display:inline-block; width:9px; height:9px; border-radius:2px; margin-right:9px; vertical-align:1px; }}
.src {{ display:block; font-size:12.5px; color:var(--muted); font-weight:400; margin-top:3px; }}
tbody tr em {{ font-style:normal; color:var(--blue); font-size:12px; }}
@media (max-width:640px) {{ .num {{ font-size:13px; padding-left:8px; }}
  tbody th .src {{ display:none; }} }}

.grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:34px; margin-top:26px; }}
@media (max-width:820px) {{ .grid2 {{ grid-template-columns:1fr; gap:20px; }} }}

.finding {{ display:grid; grid-template-columns:34px 1fr; gap:14px; padding:16px 0;
  border-bottom:1px solid var(--line); }}
.finding .n {{ font-family:"Bricolage Grotesque",sans-serif; font-size:14px; color:var(--muted); padding-top:3px; }}
.finding p {{ font-size:16px; color:#2A3138; max-width:74ch; }}
.finding b {{ font-weight:600; color:var(--ink); }}

.prose {{ max-width:70ch; font-size:16.5px; color:#333B44; }}
.prose p + p {{ margin-top:14px; }}
.prose strong {{ color:var(--ink); font-weight:600; }}

ol.big {{ list-style:none; padding:0; margin-top:8px; max-width:760px; }}
ol.big li {{ display:flex; gap:14px; align-items:baseline; padding:9px 0; border-bottom:1px solid var(--line); font-size:14.5px; }}
ol.big .d {{ color:var(--muted); font-size:13px; width:56px; }}
ol.big .t {{ flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
ol.big .c {{ color:var(--muted); font-size:12.5px; }}
ol.big .a {{ font-weight:600; font-variant-numeric:tabular-nums; width:94px; text-align:right; }}
@media (max-width:640px) {{ ol.big .c {{ display:none; }} }}

.notes {{ padding:40px 0 70px; }}
.notes li {{ font-size:14px; color:#3A424B; margin-bottom:10px; max-width:80ch; }}
.notes ul {{ padding-left:18px; }}
footer {{ border-top:1px solid var(--line); padding:22px 0 50px; font-size:13px; color:var(--muted);
  display:flex; justify-content:space-between; gap:16px; }}
:focus-visible {{ outline:2px solid var(--blue); outline-offset:3px; }}
@media (prefers-reduced-motion:reduce) {{ html {{ scroll-behavior:auto; }} * {{ transition:none !important; }} }}
</style>
</head>
<body>
<nav class="toc"><div class="wrap">
  <span class="brand">Gastos 2026</span>
  <a href="#resumen">Resumen</a><a href="#ingresos">Ingresos</a><a href="#gastos">Gastos</a>
  <a href="#meses">Mes a mes</a><a href="#comercios">Comercios</a><a href="#patrones">Patrones</a>
  <a href="#metodo">Método</a>
</div></nav>

<header class="hero"><div class="wrap">
  <h1>Un año de dinero,<br><span class="accent">mirado de cerca</span></h1>
  <p class="lede">Del 1 de enero al {last.strftime('%d/%m/%Y')}, mi cuenta corriente registró
    {len(spend)} cargos y {len(income)} abonos. Esto es lo que dicen: de dónde viene el dinero,
    dónde se va y qué meses no cuadran.</p>
  <p class="byline">Datos: extracto consolidado de Revolut · Cuenta personal EUR · Categorización propia</p>
  <div class="kpis">
    <div><b>{eur(total)}</b><span>gastados en {days} días</span></div>
    <div><b>{eur(ext_income)}</b><span>ingresos externos</span></div>
    <div><b>{eur(gap, sign=True)}</b><span>balance del año</span></div>
    <div><b>{eur(total/len(by_month))}</b><span>media mensual</span></div>
  </div>
</div></header>

<section id="resumen"><div class="wrap">
  <p class="kicker">Resumen</p>
  <h2>Seis cosas que no esperaba</h2>
  <div class="findings">
    <div class="finding"><span class="n">01</span><p><b>El gasto fijo manda.</b> Vivienda, matrícula,
      seguro y suscripciones suman {eur(fixed)}, el {fixed/total*100:.0f}&thinsp;% del total. Solo el
      alquiler son {eur(cat_total['Vivienda'])}: {eur(cat_total['Vivienda']/days,1)} al día, todos los días.</p></div>
    <div class="finding"><span class="n">02</span><p><b>Los ingresos no cubren el gasto.</b> Entraron
      {eur(ext_income)} de fuera (nómina, beca, familia y devoluciones) frente a {eur(total)} gastados:
      un déficit de {eur(-gap)} que taparon {eur(own_transfers)} traspasados desde mis otras cuentas.</p></div>
    <div class="finding"><span class="n">03</span><p><b>Comer fuera pesa casi tanto como el supermercado,
      pero en menos dinero por vez.</b> {eur(sup)} en {sup_n} compras ({eur(sup/sup_n,1)} de media) contra
      {eur(out_food)} en {out_n} salidas ({eur(out_food/out_n,1)} por ticket): dos tercios del gasto de
      comida son compra de despensa.</p></div>
    <div class="finding"><span class="n">04</span><p><b>Octubre se dispara.</b> {eur(mon10['spend'])}
      frente a {eur(mon9['spend'])} de septiembre: el mismo alquiler cobrado dos veces (6 y 30 de octubre)
      explica {eur(643.58)} de la diferencia.</p></div>
    <div class="finding"><span class="n">05</span><p><b>Martes y viernes son los días caros.</b> Entre
      los dos se llevan {eur(wd[1]+wd[4])}, el {(wd[1]+wd[4])/total*100:.0f}&thinsp;% del gasto, con
      {wdn[1]+wdn[4]} cargos. El sábado, en cambio, es el más barato: {eur(wd[5])}.</p></div>
    <div class="finding"><span class="n">06</span><p><b>Casi la mitad de los cargos son minucias.</b>
      La mediana es de {eur(median_ticket,2)} y {small} de los {len(spend)} cargos
      ({small/len(spend)*100:.0f}&thinsp;%) no llegan a 5&nbsp;€: cafés, pan, transporte suelto.</p></div>
  </div>
</div></section>

<section id="ingresos"><div class="wrap">
  <p class="kicker">Ingresos</p>
  <h2>De dónde viene el dinero</h2>
  <p class="intro">El extracto mezcla dinero que entra de verdad con movimientos entre mis propias
    cuentas. Separando lo uno de lo otro: {eur(ext_income)} son ingresos externos reales y
    {eur(own_transfers)} son traspasos desde mi cuenta de ahorro o de otro banco.</p>
  <figure class="figure">
    {income_chart}
    <figcaption>Verde: ingresos externos. Azul: gasto. La brecha entre ambas barras es lo que cada
      mes hubo que cubrir con ahorro o traspasos.</figcaption>
  </figure>
  <h3>Por fuente</h3>
  <table><thead><tr><th>Fuente</th><th class="num">Importe</th><th class="num">%</th></tr></thead>
    <tbody>{''.join(inc_rows)}</tbody></table>
  <div class="prose" style="margin-top:22px">
    <p>La nómina —trabajo de verano y prácticas— es la mayor fuente única, pero no llega a la mitad
      de los ingresos. La beca de la DUO aporta {eur(inc_total['Beca DUO'])} y la familia
      {eur(inc_total['Familia y amigos'])} en transferencias puntuales. Las devoluciones
      ({eur(inc_total['Devoluciones'])}) son compras canceladas y viajes compartidos que me devolvieron
      el dinero.</p>
    <p>El patrón importa: los ingresos llegan en bloques grandes y espaciados (una nómina, una beca
      trimestral, un Bizum familiar), mientras el gasto sale en gotas pequeñas. Esa asimetría explica
      que algunos meses parezca que sobra y otros que falta.</p>
  </div>
</div></section>

<section id="gastos"><div class="wrap">
  <p class="kicker">Gastos</p>
  <h2>En qué se va, categoría a categoría</h2>
  <p class="intro">Trece categorías para {eur(total)}. {top3[0][0]} ({pct(top3[0][1],total)}),
    {top3[1][0].lower()} ({pct(top3[1][1],total)}) y {top3[2][0].lower()} ({pct(top3[2][1],total)})
    concentran más de la mitad de todo.</p>
  <figure class="figure">
    <div class="chart-wide">{stack_chart}</div>
    <div class="chart-narrow">{stack_chart_s}</div>
    <div class="legend">{legend}</div>
    <figcaption>Gasto de cada mes desglosado por categoría. La base azul constante es el alquiler;
      lo que se mueve por encima es la vida.</figcaption>
  </figure>
  <table><thead><tr><th>Categoría</th><th class="num">Cargos</th><th class="num">Media</th>
    <th class="num">Total</th><th class="num">%</th></tr></thead><tbody>{''.join(cat_rows)}</tbody></table>
  <div class="grid2">
    <div>
      <h3>Fijo frente a variable</h3>
      <div class="prose"><p>Los costes que no dependen de cómo viva el mes suman <strong>{eur(fixed)}</strong>
        ({fixed/total*100:.0f}&thinsp;%): alquiler, matrícula, seguro, teléfono y suscripciones. Lo que sí
        depende de mí son <strong>{eur(variable)}</strong>, {eur(variable/len(by_month))} al mes o
        {eur(variable/days,1)} al día.</p>
        <p>Si mañana quisiera recortar, el margen real está en ese segundo bloque, y dentro de él en
        {top3[0][0].lower()} y {top3[1][0].lower()}.</p></div>
    </div>
    <div>
      <h3>Comer en casa o fuera</h3>
      <div class="prose"><p>El supermercado ({eur(sup)}, {sup_n} tickets) pesa más en euros, pero sale a
        {eur(sup/sup_n,1)} por compra. Fuera de casa: {eur(out_food)} en {out_n} cargos,
        {eur(out_food/out_n,1)} de media. Juntos son {eur(sup+out_food)}, el
        {(sup+out_food)/total*100:.0f}&thinsp;% del año.</p>
        <p>En otras palabras, comer me cuesta {eur((sup+out_food)/days,1)} al día, sin contar las
        máquinas de café ni los bares contados como ocio.</p></div>
    </div>
  </div>
  <figure class="figure" style="margin-top:34px">
    {cats_chart}
    <figcaption>Cada barra es el total anual de la categoría, ordenada de mayor a menor.</figcaption>
  </figure>
</div></section>

<section id="meses"><div class="wrap">
  <p class="kicker">Mes a mes</p>
  <h2>Once meses, once comportamientos</h2>
  <p class="intro">El gasto mensual se mueve entre {eur(by_month[mon_mn]['spend'])} y
    {eur(by_month[mon_mx]['spend'])}: un factor de
    {by_month[mon_mx]['spend']/by_month[mon_mn]['spend']:.1f}. Casi toda esa variación viene de cargos
    extraordinarios, no de haber vivido mejor o peor.</p>
  <table><thead><tr><th>Mes</th><th class="num">Cargos</th><th class="num">Gasto</th>
    <th class="num">Ingreso</th><th class="num">Neto</th></tr></thead><tbody>{''.join(mon_rows)}</tbody></table>
  <div class="prose" style="margin-top:24px">
    <p><strong>Septiembre es el mes más barato</strong> ({eur(mon9['spend'])}) y no porque viviera con
      menos: es el mes con menos cargos extraordinarios y sin matrícula. <strong>Mayo y octubre son los
      más caros</strong>: en mayo coinciden un curso de idiomas, dos vuelos y una compra grande; en
      octubre, el doble alquiler y la matrícula.</p>
    <p><strong>Agosto</strong> es el mes con menos ingresos ({eur(mon8['income'])}): la beca no llega y
      el trabajo de verano aún no había empezado. El déficit de ese mes
      ({eur(mon8['income']-mon8['spend'])}) lo cubrió el ahorro.</p>
  </div>
</div></section>

<section id="comercios"><div class="wrap">
  <p class="kicker">Comercios</p>
  <h2>Quién se lleva el dinero</h2>
  <p class="intro">Doce comercios concentran {sum(v[1] for _,v in top_mer)/total*100:.0f}&thinsp;% del
    gasto. El casero y la universidad son {eur(moo)} por sí solos, el {share_duo*100:.0f}&thinsp;% del total.</p>
  <table><thead><tr><th>Comercio</th><th class="num">Cargos</th><th class="num">Activo</th>
    <th class="num">Media</th><th class="num">Total</th></tr></thead><tbody>{''.join(mer_rows)}</tbody></table>

  <h3>Cargos recurrentes</h3>
  <p class="prose">Comercios que aparecen en al menos seis meses distintos y que no son compra corriente:
    alquiler, matrícula, seguro, teléfono y el abono deportivo. Sumando su importe típico,
    <strong>{eur(fixed_monthly)} al mes</strong> ({eur(fixed_monthly*12)} al año) se van sin que yo decida
    nada. Es la parte del presupuesto que conviene negociar, no recortar.</p>
  <table><thead><tr><th>Comercio</th><th class="num">Meses</th><th class="num">Importe típico</th>
    <th class="num">Total pagado</th></tr></thead><tbody>{''.join(rec_rows)}</tbody></table>

  <h3>Los seis cargos más grandes</h3>
  <ol class="big">{big_rows}</ol>
</div></section>

<section id="patrones"><div class="wrap">
  <p class="kicker">Patrones</p>
  <h2>Cuándo gasto</h2>
  <p class="intro">El calendario explica más que la voluntad: el gasto se concentra al final del mes
    y en dos días de la semana, y los tickets pequeños son la mayoría del volumen.</p>
  <figure class="figure">
    {wd_chart}
    <figcaption>Gasto total por día de la semana. El martes y el viernes multiplican por
      {(wd[1]+wd[4])/2/wd[5]:.1f} la media del sábado, el día más barato.</figcaption>
  </figure>
  <div class="grid2">
    <div><h3>Ticket medio</h3><div class="prose">
      <p>La media por cargo es {eur(total/len(spend),2)}, pero la mediana es {eur(median_ticket,2)}: la
        media la suben un puñado de pagos grandes (alquiler, matrícula, vuelos).</p>
      <p>{small} cargos por debajo de 5&nbsp;€ ({small/len(spend)*100:.0f}&thinsp;%) suman
        {eur(sum(v for v in tickets if v < 5))}, el {sum(v for v in tickets if v < 5)/total*100:.1f}&thinsp;%
        del gasto. La vida diaria no es cara; el mes lo es por los recibos.</p></div></div>
    <div><h3>Los días más caros</h3><div class="prose">
      {''.join(f'<p><strong>{d.day} de {MONTHS[d.month].lower()}</strong>: {eur(v)} en un solo día.</p>' for d,v in big_days[:4])}
      <p>Cuatro de los cinco coinciden con el último día del mes: alquiler y matrícula caen ahí.</p></div></div>
  </div>
</div></section>

<section id="metodo" class="notes"><div class="wrap">
  <p class="kicker">Método</p>
  <h2>Cómo se ha hecho</h2>
  <ul>
    <li><strong>Fuente.</strong> Extracto consolidado de Revolut para el periodo 01/01/2026–{last.strftime('%d/%m/%Y')},
      exportado en CSV: {len(txs)} apuntes con fecha, comercio, categoría del banco, importe y saldo.</li>
    <li><strong>Categorías.</strong> Reglas propias sobre el nombre del comercio, más específicas que las
      del banco. Puede haber cargos en la categoría vecina; los casos dudosos se ven en el listado de
      comercios, no se esconden en un agregado.</li>
    <li><strong>Ingresos.</strong> Se separan los traspasos desde cuentas a mi nombre
      ({eur(own_transfers)}) porque no son ingresos nuevos, solo dinero movido de sitio.</li>
    <li><strong>Privacidad.</strong> Las transferencias a personas van sin nombre; los traspasos propios,
      sin banco de origen.</li>
    <li><strong>Exclusiones.</strong> Cambios de divisa, redondeos de RevPoints y las cuentas en USD, DKK
      y GBP, de peso residual.</li>
    <li><strong>Noviembre</strong> está incompleto: solo los días 1 a {today.day}, marcado como parcial en
      la tabla. La media mensual se calcula sobre once meses con ese matiz.</li>
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
    print(f"wrote {path} ({len(doc)/1024:.1f} kB)")

if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ".")
