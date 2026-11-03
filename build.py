#!/usr/bin/env python3
"""gastos-2026 — a month-first reading of a year of bank statements.

The question the page answers: how does one spend ~1,950 € a month?
So: the typical month broken into six groups, then eleven months side by side.
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
DISPLAY = {
    "to payments.holland2stay.com via rabo smart pay": "Holland2Stay",
    "to holland2stay b.v. via stichting mollie payments": "Holland2Stay",
    "to eindhoven university of technology": "TU/e",
    "to technische universiteit eindhoven via stichting mollie payments": "TU/e",
    "to cjib verkeersboetes": "CJIB · multas",
    "to esky.pl s.a.": "ESKY.pl · vuelos",
    "to ns reizigers b.v.": "NS",
    "ns groep iz ns reizigers": "NS",
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
    if "refund" in low or "chargeback" in low or "blablacar" in low or "amoviles" in low \
       or "amovens" in low or "mediamarkt" in low:
        return "Devoluciones"
    if "transfer from" in low:
        return "Familia y amigos"
    return "Otros"

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
    partial = (today.year, today.month)
    import calendar as _cal
    _last_full = max((y_, mo) for (y_, mo) in months if (y_, mo) != partial)
    _end = datetime.date(_last_full[0], _last_full[1],
                         _cal.monthrange(_last_full[0], _last_full[1])[1])
    days_full = (_end - first).days + 1


    bym = collections.OrderedDict()
    for ym in months:
        ms = [t for t in spend if mkey(t) == ym]
        mi = [t for t in income if mkey(t) == ym and t["icat"] != "Traspasos propios"]
        groups = collections.Counter()
        for t in ms:
            groups[t["grp"]] += -t["amount"]
        bym[ym] = {"spend": -sum(t["amount"] for t in ms),
                   "income": sum(t["amount"] for t in mi),
                   "n": len(ms), "groups": groups,
                   "top": sorted(ms, key=lambda t: t["amount"])[:3]}

    complete = [ym for ym in months if ym != partial]
    ncomp = len(complete)
    total = sum(-t["amount"] for t in spend)
    total_comp = sum(bym[ym]["spend"] for ym in complete)
    avg_month = total_comp / ncomp
    avg_groups = collections.Counter()
    for ym in complete:
        for g, v in bym[ym]["groups"].items():
            avg_groups[g] += v / ncomp
    ext_income = sum(t["amount"] for t in income if t["icat"] != "Traspasos propios")
    own = sum(t["amount"] for t in income if t["icat"] == "Traspasos propios")
    gap = ext_income - total
    fixed_avg = avg_groups["Vivienda"] + avg_groups["Universidad"] + avg_groups["Recibos"]

    mer = collections.defaultdict(lambda: [0, 0.0, set(), "Vida"])
    for t in spend:
        k = clean(t["desc"])
        mer[k][0] += 1
        mer[k][1] += -t["amount"]
        mer[k][2].add(mkey(t))
        mer[k][3] = t["grp"]
    recurring = []
    for name, (n, tot, mons, grp) in mer.items():
        src = [t for t in spend if clean(t["desc"]) == name]
        if len({mkey(t) for t in src}) < 6:
            continue
        if classify(src[0]["desc"], src[0]["raw"]) in ("Supermercado", "Comidas y bares",
                                                       "Transferencias", "Compras"):
            continue
        med = statistics.median([-t["amount"] for t in src])
        if med >= 2:
            recurring.append((name, med, len({mkey(t) for t in src}), tot))
    recurring.sort(key=lambda r: -r[1])

    wd = collections.Counter(); wdn = collections.Counter()
    for t in spend:
        wd[t["date"].weekday()] += -t["amount"]; wdn[t["date"].weekday()] += 1
    tickets = sorted(-t["amount"] for t in spend)
    median_ticket = tickets[len(tickets)//2]

    fontcss = FONTS.read_text(encoding="utf-8") if FONTS.exists() else ""
    mon_mx = max(complete, key=lambda k: bym[k]["spend"])
    mon_mn = min(complete, key=lambda k: bym[k]["spend"])
    max_month_spend = bym[mon_mx]["spend"]

    # ---- typical month bar (CSS segments)
    seg = "".join(
        f'<span style="width:{avg_groups[g]/avg_month*100:.2f}%;background:{G_COLOR[g]}" '
        f'title="{g}: {eur(avg_groups[g])}">'
        f'{"<b>" + eur(avg_groups[g]) + "</b>" if avg_groups[g]/avg_month > 0.14 else ""}</span>'
        for g in G_ORDER)
    avg_rows = "".join(
        f'<tr><th scope="row"><span class="dot" style="background:{G_COLOR[g]}"></span>{g}</th>'
        f'<td class="num strong">{eur(avg_groups[g])}</td>'
        f'<td class="num dim">{avg_groups[g]/avg_month*100:.0f}&thinsp;%</td>'
        f'<td class="num dim">{eur(avg_groups[g]/30.4,1)}/día</td></tr>'
        for g in G_ORDER)

    # ---- monthly chart (replaces the per-month recount)
    def months_chart(small=False):
        W, H = (400, 260) if small else (1000, 300)
        L, R, T, B = (32, 6, 22, 30) if small else (50, 10, 26, 34)
        pw, ph = W - L - R, H - T - B
        peak = max(bym[m]["spend"] for m in months)
        step = next(c for c in [250, 500, 1000, 1500] if c >= peak / (4 if small else 5))
        top = -(-peak // step) * step
        sc = ph / top
        slot = pw / len(months)
        bw = min(slot * (0.56 if small else 0.5), 46)
        o = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="Gasto de cada mes">']
        g = 0
        while g <= top:
            y = T + ph - g * sc
            o.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W-R}" y2="{y:.1f}" class="gl"/>')
            o.append(f'<text x="{L-8}" y="{y+3.8:.1f}" text-anchor="end" class="ax">'
                     f'{g//1000}k</text>' if g and g % 1000 == 0 else
                     f'<text x="{L-8}" y="{y+3.8:.1f}" text-anchor="end" class="ax">{g}</text>')
            g += step
        ya = T + ph - avg_month * sc
        o.append(f'<line x1="{L}" y1="{ya:.1f}" x2="{W-R}" y2="{ya:.1f}" stroke="#0D1117" '
                 f'stroke-width="1.3" stroke-dasharray="5 4"/>')
        o.append(f'<text x="{L+8}" y="{T+2:.1f}" class="avl">— media {eur(avg_month)}</text>')
        for i, ym in enumerate(months):
            m = bym[ym]
            cx = L + slot * i + slot / 2
            h = m["spend"] * sc
            col = "#1F4E9C" if ym != partial else "#B9C2CE"
            o.append(f'<rect x="{cx-bw/2:.1f}" y="{T+ph-h:.1f}" width="{bw:.1f}" height="{max(h,0.6):.1f}" '
                     f'fill="{col}" rx="2"><title>{MONTHS[ym[1]]}: {eur(m["spend"])}</title></rect>')
            if not small or ym in (mon_mx, mon_mn):
                o.append(f'<text x="{cx:.1f}" y="{T+ph-h-8:.1f}" text-anchor="middle" class="vl">{eur(m["spend"])}</text>')
            o.append(f'<text x="{cx:.1f}" y="{H-9}" text-anchor="middle" class="ax">{ABBR[ym[1]]}</text>')
        o.append(f'<line x1="{L}" y1="{T+ph}" x2="{W-R}" y2="{T+ph}" class="base"/>')
        o.append("</svg>")
        return "".join(o)

    mchart, mchart_s = months_chart(), months_chart(small=True)
    rec_rows = "".join(
        f'<tr><th scope="row">{html.escape(n)}</th><td class="num dim">{nm} de 11</td>'
        f'<td class="num strong">{eur(med,2)}</td><td class="num dim">{eur(med*12)}/año</td></tr>'
        for n, med, nm, tot in recurring)
    fixed_monthly = sum(r[1] for r in recurring)

    doc = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>1.956 € al mes · gastos 2026</title>
<meta name="description" content="Cómo se gasta una media de 1.956 € al mes: el mes tipo desglosado y los once meses del año, uno a uno.">
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
.wrap {{ max-width:1000px; margin:0 auto; padding:0 28px; }}
@media (max-width:640px) {{
  .wrap {{ padding:0 18px; }}
  nav .wrap {{ padding:10px 18px; gap:16px; }}
  h1 {{ letter-spacing:-.03em; }}
  .num {{ font-size:12.5px; padding-left:8px; }}
  tbody th, tbody td {{ font-size:13.5px; padding:9px 0; }}
  .avgbar {{ height:38px; }}
  .avgbar b {{ font-size:11.5px; }}
}}

nav {{ position:sticky; top:0; z-index:20; background:#F6F7F9EE; backdrop-filter:blur(8px);
  border-bottom:1px solid var(--line); }}
nav .wrap {{ display:flex; gap:20px; overflow-x:auto; padding:11px 28px; font-size:13px;
  scrollbar-width:none; }}
nav .wrap::-webkit-scrollbar {{ display:none; }}
nav a {{ color:var(--muted); text-decoration:none; white-space:nowrap; }}
nav .brand {{ color:var(--ink); font-weight:600; margin-right:auto; font-family:"Bricolage Grotesque",sans-serif; }}

header.hero {{ padding:64px 0 30px; }}
h1 {{ font-family:"Bricolage Grotesque",sans-serif; font-weight:600;
  font-size:clamp(40px,7vw,74px); line-height:0.98; letter-spacing:-.04em; }}
h1 span {{ color:var(--blue); }}
.dek {{ margin-top:16px; font-size:clamp(16px,1.9vw,19px); color:#2A3138; max-width:56ch; }}

section {{ padding:44px 0 8px; border-top:1px solid var(--line); scroll-margin-top:56px; }}
h2 {{ font-family:"Bricolage Grotesque",sans-serif; font-weight:600; font-size:clamp(23px,2.8vw,30px);
  letter-spacing:-.02em; }}
.note {{ margin-top:8px; font-size:15.5px; color:#3A424B; max-width:70ch; }}
h3 {{ font-family:"Bricolage Grotesque",sans-serif; font-weight:600; font-size:17px; }}

/* typical month */
.avgbar {{ display:flex; height:46px; margin:22px 0 6px; gap:1.5px; }}
.avgbar span {{ display:flex; align-items:center; justify-content:center; }}
.avgbar b {{ color:#fff; font-size:13px; font-weight:600; }}
.avgbar span:first-child {{ border-radius:3px 0 0 3px; }}
.avgbar span:last-child {{ border-radius:0 3px 3px 0; }}
.avglabels {{ display:flex; flex-wrap:wrap; gap:6px 18px; margin-bottom:20px; }}
.al {{ font-size:12.5px; color:var(--muted); display:inline-flex; align-items:center; gap:6px; }}
.al i {{ width:10px; height:10px; border-radius:2px; display:block; }}

table {{ width:100%; border-collapse:collapse; margin-top:6px; }}
thead th {{ font-size:12px; font-weight:500; color:var(--muted); text-align:left;
  padding:0 0 7px; border-bottom:1px solid var(--ink); }}
tbody th, tbody td {{ padding:10px 0; border-bottom:1px solid var(--line); font-size:14.5px; }}
tbody th {{ font-weight:500; text-align:left; }}
.num {{ text-align:right; white-space:nowrap; font-variant-numeric:tabular-nums; padding-left:12px; }}
.strong {{ font-weight:600; }} .dim {{ color:var(--muted); }}
.pos {{ color:var(--green); }} .neg {{ color:var(--red); }}
.dot {{ display:inline-block; width:9px; height:9px; border-radius:2px; margin-right:9px; }}

/* charts */
figure {{ margin:18px 0 6px; }}
.chart {{ width:100%; height:auto; display:block; overflow:visible; }}
.gl {{ stroke:#E7EAEF; stroke-width:1; }}
.base {{ stroke:#0D1117; stroke-width:1.2; }}
text.ax {{ font-family:"Inter",sans-serif; font-size:11px; fill:#77808D; }}
text.vl {{ font-family:"Inter",sans-serif; font-size:11px; font-weight:600; fill:#20262D; }}
text.avl {{ font-family:"Inter",sans-serif; font-size:11px; fill:#0D1117; font-weight:500; }}
.cn {{ display:none; }}
@media (max-width:640px) {{ .cw {{ display:none; }} .cn {{ display:block; }} }}

/* month grid */
.months {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-top:22px; }}

.m {{ background:#fff; border:1px solid var(--line); border-radius:14px; padding:16px 16px 12px; }}
.m header {{ display:flex; justify-content:space-between; align-items:baseline; }}
.m h3 {{ font-size:19px; }}
.m .yr {{ font-size:12px; color:var(--muted); margin-left:6px; font-family:"Inter",sans-serif; font-weight:400; }}
.m .tot {{ font-family:"Bricolage Grotesque",sans-serif; font-weight:600; font-size:21px;
  letter-spacing:-.02em; }}
.m.partial .tot {{ color:var(--muted); }}
.scale {{ height:3px; background:var(--line); border-radius:2px; margin:12px 0 5px; }}
.scale i {{ display:block; height:3px; background:#C9CFD8; border-radius:2px; }}
.bar {{ display:flex; height:12px; gap:1px; margin-bottom:10px; }}
.cats {{ font-size:12.5px; color:#3E4650; line-height:1.5; }}
.net {{ font-size:12.5px; color:var(--muted); margin-top:6px; }}
.net b {{ font-weight:600; }}
ul.top {{ list-style:none; padding:10px 0 0; margin-top:8px; border-top:1px dashed var(--line); }}
ul.top li {{ display:flex; gap:8px; font-size:12.5px; color:#333B44; padding:2px 0; }}
ul.top .d {{ color:var(--muted); width:16px; text-align:right; }}
ul.top .t {{ flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
ul.top .a {{ font-variant-numeric:tabular-nums; }}

.notes {{ padding:36px 0 60px; }}
.notes li {{ font-size:13.5px; color:#3A424B; margin-bottom:8px; max-width:80ch; }}
.notes ul {{ padding-left:18px; }}
footer {{ border-top:1px solid var(--line); padding:20px 0 44px; font-size:12.5px; color:var(--muted);
  display:flex; justify-content:space-between; gap:16px; }}
:focus-visible {{ outline:2px solid var(--blue); outline-offset:3px; }}
</style>
</head>
<body>
<nav><div class="wrap">
  <span class="brand">Gastos 2026</span>
  <a href="#tipo">El mes tipo</a><a href="#meses">Cómo varían</a>
  <a href="#fijo">Lo fijo</a><a href="#metodo">Método</a>
</div></nav>

<header class="hero"><div class="wrap">
  <h1>1.956&nbsp;€ al mes<span>.</span></h1>
  <p class="dek">Es la media de los diez meses completos: {eur(total_comp)} en {days_full} días.
    Así se compone un mes normal, y así se desviaron los otros.</p>
</div></header>

<section id="tipo"><div class="wrap">
  <h2>El mes tipo</h2>
  <p class="note">Si cada mes fuera igual, sería esta barra. Seis grupos, {eur(avg_month)} al mes,
    {eur(avg_month/30.4)} al día.</p>
  <div class="avgbar">{seg}</div>
  <div class="avglabels">{''.join(f'<span class="al"><i style="background:{G_COLOR[g]}"></i>{g}</span>' for g in G_ORDER)}</div>
  <table><thead><tr><th>Grupo</th><th class="num">Al mes</th><th class="num">Peso</th>
    <th class="num">Al día</th></tr></thead><tbody>{avg_rows}</tbody></table>
  <p class="note" style="margin-top:16px"><strong>{eur(fixed_avg)} fijos</strong> —vivienda, universidad
    y recibos, el {fixed_avg/avg_month*100:.0f}&thinsp;%— y {eur(avg_month-fixed_avg)} que sí depende de mí.
    Los tres primeros grupos ({eur(avg_groups['Vivienda']+avg_groups['Comida']+avg_groups['Universidad'])})
    ya son el {(avg_groups['Vivienda']+avg_groups['Comida']+avg_groups['Universidad'])/avg_month*100:.0f}&thinsp;%
    de cualquier mes.</p>
</div></section>

<section id="meses"><div class="wrap">
  <h2>Cómo varían</h2>
  <p class="note">Siete de los diez meses completos caen entre 1.500 y 2.100 €.
    {MONTHS[mon_mx[1]]} se va a {eur(bym[mon_mx]['spend'])} por el alquiler cobrado dos veces (6 y 30);
    {MONTHS[mon_mn[1]].lower()}, a {eur(bym[mon_mn]['spend'])} por no tener matrícula.</p>
  <figure><div class="cw">{mchart}</div><div class="cn">{mchart_s}</div></figure>
</div></section>

<section id="fijo"><div class="wrap">
  <h2>Lo que no cambia</h2>
  <p class="note">Cargos que aparecen al menos seis meses: {eur(fixed_monthly)} al mes,
    {eur(fixed_monthly*12)} al año. Esta es la parte del presupuesto que no se negocia mes a mes.</p>
  <table><thead><tr><th>Comercio</th><th class="num">Meses</th><th class="num">Importe</th>
    <th class="num">Al año</th></tr></thead><tbody>{rec_rows}</tbody></table>
</div></section>

<section id="metodo" class="notes"><div class="wrap">
  <h2>Método</h2>
  <ul>
    <li>Extracto consolidado de Revolut, 01/01/2026–{last.strftime('%d/%m/%Y')}: {len(txs)} apuntes.
      Las medias usan los diez meses completos; noviembre ({eur(bym[partial]['spend'])}, 3 días) queda
      fuera.</li>
    <li>Seis grupos a partir de trece categorías propias (reglas sobre el comercio, no las del banco).</li>
    <li>Traspasos entre cuentas a mi nombre ({eur(own)}) fuera de los ingresos. Transferencias a personas,
      sin nombre.</li>
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
    print(f"wrote {path} ({len(doc)/1024:.1f} kB) · avg {avg_month:.0f} · total {total:.0f}")

if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ".")
