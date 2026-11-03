#!/usr/bin/env python3
"""Build the public page 'gastos-2026' from a Revolut consolidated statement.

Usage: python build.py <statement.csv> [outdir]
Only index.html is published; the CSV stays local.
"""
import csv, re, sys, html, collections, datetime, importlib.util, os, pathlib

SCRATCH = ("/data/data/com.termux/files/usr/tmp/claude-10572/"
           "-data-data-com-termux-files-home/b7014fd9-800d-4730-9b7d-a416f0eacad8/scratchpad")
spec = importlib.util.spec_from_file_location("g", SCRATCH + "/gen_report.py")
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)
load, classify = G.load, G.classify

HERE = pathlib.Path(__file__).resolve().parent
FONTS = (HERE / ".fonts" / "embedded.css")

MONTHS = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
          "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
ABBR = ["", "ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

COLORS = {
    "Vivienda": "#28527A", "Universidad": "#5E5089", "Supermercado": "#3F6B3B",
    "Compras": "#9C5450", "Transporte": "#2F6E6B", "Seguros y salud": "#7C6E38",
    "Comidas y bares": "#B4763F", "Viajes": "#44506A", "Ocio": "#6E4560",
    "Transferencias": "#7E8479", "Suscripciones": "#546E7E",
    "Multas e impuestos": "#853434", "Otros": "#63675A",
}

def eur(v, dec=2, sign=False):
    s = f"{v:,.{dec}f}".replace(",", "#").replace(".", ",").replace("#", ".")
    if sign and v > 0:
        s = "+" + s
    return s + " €"

def clean(desc):
    d = desc.strip()
    low = d.lower()
    if low.startswith(("transfer to", "to hr ", "to mw ")) or "via tikkie" in low \
       or "betaalverzoek" in low or low.startswith("transfer from"):
        return "Traspaso a un particular"
    if "menendez" in low:
        return "Traspaso a cuenta propia"
    return d

def build(csv_path, outdir="."):
    txs = load(csv_path)
    spend = [t for t in txs if t["amount"] < 0]
    income = [t for t in txs if t["amount"] > 0]
    for t in spend:
        t["cat"] = classify(t["desc"], t["raw"])
    mkey = lambda t: (t["date"].year, t["date"].month)

    months = sorted({mkey(t) for t in txs})
    by_month = collections.OrderedDict()
    for ym in months:
        ms = [t for t in spend if mkey(t) == ym]
        cats = collections.Counter()
        for t in ms:
            cats[t["cat"]] += -t["amount"]
        by_month[ym] = {"spend": -sum(t["amount"] for t in ms),
                        "income": sum(t["amount"] for t in income if mkey(t) == ym),
                        "n": len(ms), "cats": cats,
                        "top": sorted(ms, key=lambda t: t["amount"])[:5]}

    total_cat = collections.Counter()
    for t in spend:
        total_cat[t["cat"]] += -t["amount"]
    total = sum(total_cat.values())
    inc_total = sum(t["amount"] for t in income)
    today = datetime.date.today()
    first, last = min(t["date"] for t in txs), max(t["date"] for t in txs)
    days = (last - first).days + 1
    complete = [v for (y_, mo), v in by_month.items() if not (y_ == today.year and mo == today.month)]

    # ---------------- year chart ----------------
    def chart(W, H, L, R, T, B, small):
        pw, ph = W - L - R, H - T - B
        peak = max(m["spend"] for m in by_month.values())
        cands = [50, 100, 200, 250, 500, 1000, 2000, 2500, 5000]
        step_v = next(c for c in cands if c >= peak / (4 if small else 6))
        top_v = -(-peak // step_v) * step_v
        scale = ph / top_v
        n = len(by_month)
        slot = pw / n
        bw = min(slot * (0.62 if small else 0.55), 44)
        fs = 13 if small else 10.5
        out = [f'<svg viewBox="0 0 {W} {H}" class="yearchart" role="img" '
               f'aria-label="Gasto de cada mes por categoría">']
        g = 0
        while g <= top_v:
            y = T + ph - g * scale
            out.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W-R}" y2="{y:.1f}" stroke="var(--grid)" stroke-width="1"/>')
            lbl = f"{g//1000}k" if g and g % 1000 == 0 else f"{g}"
            out.append(f'<text x="{L-8}" y="{y+fs*0.35:.1f}" text-anchor="end" class="ax" '
                       f'style="font-size:{fs}px">{lbl}</text>')
            g += step_v
        for i, ((y_, mo), m) in enumerate(by_month.items()):
            cx = L + slot * i + slot / 2
            x, base = cx - bw / 2, T + ph
            for cat, val in sorted(m["cats"].items(), key=lambda kv: -kv[1]):
                h = val * scale
                base -= h
                out.append(f'<rect x="{x:.1f}" y="{base:.1f}" width="{bw:.1f}" height="{max(h-0.9,0.5):.1f}" '
                           f'fill="{COLORS.get(cat,"#63675A")}"><title>{MONTHS[mo]}, {cat}: {eur(val,0)}</title></rect>')
            if not small:
                out.append(f'<text x="{cx:.1f}" y="{base-9:.1f}" text-anchor="middle" class="v">{eur(m["spend"],0)}</text>')
            out.append(f'<text x="{cx:.1f}" y="{H-10}" text-anchor="middle" class="ax" '
                       f'style="font-size:{fs}px">{ABBR[mo]}</text>')
        out.append(f'<line x1="{L}" y1="{T+ph}" x2="{W-R}" y2="{T+ph}" stroke="var(--ink)" stroke-width="1.4"/>')
        out.append("</svg>")
        return "".join(out)

    yearchart = chart(840, 330, 54, 12, 30, 46, False)
    yearchart_s = chart(400, 236, 34, 8, 16, 30, True)

    # ---------------- categories ----------------
    cmax = total_cat.most_common(1)[0][1]
    crows = "\n".join(f"""<tr>
      <th scope="row"><span class="sw" style="background:{COLORS.get(c)}"></span>{c}</th>
      <td class="bar"><span style="width:{v/cmax*100:.1f}%;background:{COLORS.get(c)}"></span></td>
      <td class="num strong">{eur(v)}</td>
      <td class="num dim">{v/total*100:.0f}%</td></tr>""" for c, v in total_cat.most_common())

    # ---------------- months ----------------
    mrows = []
    for (y_, mo), m in by_month.items():
        partial = (y_, mo) == (today.year, today.month)
        net = m["income"] - m["spend"]
        dom, domv = m["cats"].most_common(1)[0]
        segs = "".join(f'<i style="width:{v/m["spend"]*100:.1f}%;background:{COLORS.get(c)}" '
                       f'title="{c}: {eur(v)}"></i>' for c, v in m["cats"].most_common())
        tops = "".join(f'<li><span class="d">{t["date"].day:02d}</span>'
                       f'<span class="t">{html.escape(clean(t["desc"]))}</span>'
                       f'<span class="a">{eur(-t["amount"])}</span></li>' for t in m["top"])
        mrows.append(f"""<tr class="mrow">
      <th scope="row">{MONTHS[mo]}{' <em>hasta el día %d</em>' % today.day if partial else ''}
        <span class="sub">{dom.lower()} · {domv/m['spend']*100:.0f}%</span></th>
      <td class="num strong">{eur(m["spend"])}</td>
      <td class="num dim income">{eur(m["income"])}</td>
      <td class="num {'neg' if net < 0 else 'pos'}">{eur(net, sign=True)}</td>
      <td class="mini"><div class="stack">{segs}</div></td>
      <td class="num dim n moves">{m['n']}</td></tr>""")

    legend = " ".join(f'<span class="lg"><i style="background:{COLORS.get(c)}"></i>{c}</span>'
                      for c, _ in total_cat.most_common())
    t3 = total_cat.most_common(3)
    top10 = sorted(spend, key=lambda t: t["amount"])[:10]
    top10_html = "".join(
        f'<li><span class="d">{t["date"].strftime("%d/%m")}</span>'
        f'<span class="t">{html.escape(clean(t["desc"]))}</span>'
        f'<span class="c">{t["cat"].lower()}</span>'
        f'<span class="a">{eur(-t["amount"])}</span></li>' for t in top10)
    fixed = sum(total_cat[c] for c in ("Vivienda", "Seguros y salud", "Suscripciones", "Universidad"))
    weekly = total_cat.get("Supermercado", 0) / (len(complete) * 4.3)
    fontcss = FONTS.read_text(encoding="utf-8") if FONTS.exists() else ""

    doc = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gastos 2026 · Álvaro Menéndez</title>
<meta name="description" content="Un año de gastos personales contado con las cifras del extracto bancario: dónde se va el dinero de un estudiante de máster en Eindhoven.">
<style>
{fontcss}
:root {{
  --paper:#F3F4EE; --band:#E6EAD7; --ink:#161B15; --ink2:#4E593F; --grid:#D5DBC8;
  --rule:#C4CCB6; --blue:#1D3B6E; --pos:#2C6239; --neg:#9C3A32;
}}
* {{ box-sizing: border-box; }}
html {{ background:#E6E9DC; }}
body {{
  margin:0; background:var(--paper); color:var(--ink);
  font:400 16.5px/1.6 "Familjen Grotesk", "Helvetica Neue", Arial, sans-serif;
  font-feature-settings:"tnum" 1; -webkit-text-size-adjust:100%;
}}
.sheet {{ max-width:900px; margin:0 auto; background:var(--paper);
          border-left:1px solid var(--rule); border-right:1px solid var(--rule); }}
h1, h2, p, ul, dl, dd {{ margin:0; }}
a {{ color:var(--blue); }}

/* ---------- header ---------- */
.head {{ border-bottom:2px solid var(--ink); padding:26px 28px 24px; }}
.meta {{ display:flex; justify-content:space-between; gap:16px; flex-wrap:wrap;
         font-family:"IBM Plex Mono",monospace; font-size:11px; letter-spacing:.07em;
         text-transform:uppercase; color:var(--ink2); padding-bottom:18px;
         border-bottom:1px solid var(--rule); }}
.intro {{ display:grid; grid-template-columns:1fr auto; gap:34px; align-items:start; padding-top:26px; }}
@media (max-width:700px) {{ .intro {{ grid-template-columns:1fr; gap:18px; }} }}
h1 {{ font-size:clamp(31px,5.4vw,50px); line-height:1.02; letter-spacing:-.032em; font-weight:700; }}
h1 em {{ font-style:normal; color:var(--blue); }}
.lede {{ margin-top:16px; max-width:56ch; font-size:16.5px; line-height:1.55; color:#1B211A; }}
.lede strong {{ font-weight:600; }}
.stamp {{ border:3px solid var(--blue); color:var(--blue); padding:10px 16px 12px; min-width:190px;
          transform:rotate(-2.2deg); font-family:"IBM Plex Mono",monospace; font-size:11px;
          letter-spacing:.14em; text-transform:uppercase; }}
.stamp b {{ display:block; font-size:27px; letter-spacing:-.02em; margin-top:3px; text-transform:none; }}
@media (max-width:700px) {{ .stamp {{ transform:rotate(-1.6deg); }} }}
.fields {{ display:grid; grid-template-columns:repeat(4,1fr); margin-top:28px;
           border-top:1px solid var(--rule); }}
.fields > div {{ padding:11px 14px 3px 0; }}
.fields > div + div {{ border-left:1px solid var(--rule); padding-left:16px; }}
.fields dt {{ font-family:"IBM Plex Mono",monospace; font-size:10.5px; letter-spacing:.08em;
              text-transform:uppercase; color:var(--ink2); }}
.fields dd {{ font-family:"IBM Plex Mono",monospace; font-size:14px; margin-top:2px; }}
@media (max-width:640px) {{
  .fields {{ grid-template-columns:1fr 1fr; }}
  .fields > div:nth-child(3) {{ border-left:0; padding-left:0; }}
  .fields > div:nth-child(3), .fields > div:nth-child(4) {{ border-top:1px solid var(--rule); }}
}}

/* ---------- sections ---------- */
section {{ padding:30px 28px 34px; border-bottom:1px solid var(--rule); }}
@media (max-width:600px) {{ section, .head {{ padding-left:18px; padding-right:18px; }} }}
h2 {{ font-family:"IBM Plex Mono",monospace; font-size:11.5px; letter-spacing:.12em;
      text-transform:uppercase; color:var(--ink2); font-weight:500; margin-bottom:20px; }}
.yearchart {{ width:100%; height:auto; display:block; }}
.chart-narrow {{ display:none; }}
@media (max-width:600px) {{
  .chart-wide {{ display:none; }} .chart-narrow {{ display:block; }}
  .legend {{ display:none; }}
}}
.ax {{ font-family:"IBM Plex Mono",monospace; font-size:10.5px; fill:var(--ink2); }}
.v {{ font-family:"IBM Plex Mono",monospace; font-size:10.5px; fill:var(--ink); }}
.legend {{ display:flex; flex-wrap:wrap; gap:7px 15px; margin-top:18px; }}
.lg {{ font-size:11.5px; color:var(--ink2); display:inline-flex; align-items:center; gap:5px; }}
.lg i {{ width:9px; height:9px; display:block; }}

table {{ width:100%; border-collapse:collapse; }}
thead th {{ font-family:"IBM Plex Mono",monospace; font-size:10.5px; letter-spacing:.07em;
            text-transform:uppercase; color:var(--ink2); font-weight:500;
            border-bottom:1px solid var(--ink); padding:0 0 7px; }}
th, td {{ text-align:left; font-weight:400; font-size:14.5px; vertical-align:middle; }}
tbody th, tbody td {{ padding:9px 0; border-bottom:1px solid var(--rule); }}
tbody tr:nth-child(2n+1) th, tbody tr:nth-child(2n+1) td {{ background:var(--band); }}
.num {{ text-align:right; font-family:"IBM Plex Mono",monospace; font-size:13.5px;
        white-space:nowrap; padding-left:12px; }}
.strong {{ font-weight:600; }}
.dim {{ color:var(--ink2); }}
.pos {{ color:var(--pos); }} .neg {{ color:var(--neg); }}
.sw {{ width:8px; height:8px; display:inline-block; margin-right:9px; vertical-align:1px; }}
.bar {{ width:36%; }} .bar span {{ display:block; height:8px; }}
.mini {{ width:104px; }}
.stack {{ display:flex; height:10px; width:104px; gap:1px; }}
.stack i {{ display:block; height:100%; }}
.n {{ width:46px; }}
.mrow th {{ font-weight:500; }}
.mrow th .sub {{ display:block; font-family:"IBM Plex Mono",monospace; font-size:10.5px;
                 font-weight:400; color:var(--ink2); margin-top:2px; }}
.mrow th em {{ font-style:normal; font-family:"IBM Plex Mono",monospace; font-size:10.5px;
               color:var(--blue); margin-left:6px; }}
.top10 {{ list-style:none; padding:0; }}
.top10 li {{ display:flex; align-items:baseline; gap:12px; padding:7px 0; font-size:14px;
             border-bottom:1px solid var(--rule); }}
.top10 li:nth-child(2n+1) {{ background:var(--band); }}
.top10 .d {{ font-family:"IBM Plex Mono",monospace; color:var(--ink2); font-size:12px; width:42px; }}
.top10 .t {{ flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.top10 .c {{ font-family:"IBM Plex Mono",monospace; font-size:11px; color:var(--ink2); }}
.top10 .a {{ font-family:"IBM Plex Mono",monospace; font-size:13px; font-weight:500; width:92px; text-align:right; }}
.readout {{ margin-top:20px; font-size:15px; line-height:1.6; max-width:74ch; color:#262C24; }}
.readout strong {{ font-weight:600; }}
.notes ul {{ padding-left:20px; list-style:disc; }}
.notes li::marker {{ color:var(--ink2); }}
.notes li {{ font-size:13.5px; line-height:1.6; color:#333A2F; margin-bottom:9px; max-width:78ch; }}
footer {{ display:flex; justify-content:space-between; gap:12px; padding:22px 28px 34px;
          font-family:"IBM Plex Mono",monospace; font-size:11px; color:var(--ink2); }}
:focus-visible {{ outline:2px solid var(--blue); outline-offset:3px; }}
@media (prefers-reduced-motion:reduce) {{ * {{ transition:none !important; }} }}
@media (max-width:600px) {{
  .mini, .stack {{ width:56px; }}
  .bar {{ display:none; }}
  .num {{ font-size:12.5px; padding-left:8px; }}
  .income, .moves {{ display:none; }}
  .top10 .c {{ display:none; }}
  .top10 .a {{ width:78px; }}
}}
</style>
</head>
<body>
<div class="sheet">
  <header class="head">
    <div class="meta"><span>Extracto personal · Revolut Bank UAB</span><span>Cuenta EUR · Países Bajos</span></div>
    <div class="intro">
      <div>
        <h1>Un año de gastos,<br><em>sin adornos</em></h1>
        <p class="lede">Cada cargo de mi cuenta entre el {first.strftime('%d/%m/%Y')} y el
          {last.strftime('%d/%m/%Y')}, sacado del extracto que el banco emite para Hacienda.
          <strong>{len(spend)} cargos</strong> y una sola pregunta: ¿en qué se va el dinero de un
          estudiante de máster en Eindhoven?</p>
      </div>
      <div class="stamp">Gasto total<b>{eur(total)}</b></div>
    </div>
    <dl class="fields">
      <div><dt>Periodo</dt><dd>{days} días</dd></div>
      <div><dt>Cargos</dt><dd>{len(spend)}</dd></div>
      <div><dt>Media mensual</dt><dd>{eur(total/len(by_month),0)}</dd></div>
      <div><dt>Ingresos</dt><dd>{eur(inc_total,0)}</dd></div>
    </dl>
  </header>

  <section>
    <h2>Gasto de cada mes</h2>
    <div class="chart-wide">{yearchart}</div>
    <div class="chart-narrow">{yearchart_s}</div>
    <div class="legend">{legend}</div>
  </section>

  <section>
    <h2>Dónde se va</h2>
    <table><tbody>{crows}</tbody></table>
    <p class="readout">La vivienda sola se come un tercio del gasto. Con la universidad, el seguro y
      las suscripciones, <strong>{eur(fixed,0)}</strong> ({fixed/total*100:.0f}%) son costes fijos que
      no dependen de cómo viva el mes; el resto sí. Lo que más pesa ahí: {t3[0][0].lower()}
      ({eur(t3[0][1],0)}), {t3[1][0].lower()} ({eur(t3[1][1],0)}) y {t3[2][0].lower()} ({eur(t3[2][1],0)}).</p>
  </section>

  <section>
    <h2>Mes a mes</h2>
    <table>
      <thead><tr><th>Mes</th><th class="num">Gasto</th><th class="num income">Ingreso</th>
        <th class="num">Neto</th><th class="mini"></th><th class="num moves">Mov.</th></tr></thead>
      <tbody>{''.join(mrows)}</tbody>
    </table>
  </section>

  <section>
    <h2>Los diez cargos mayores del año</h2>
    <ol class="top10">{top10_html}</ol>
  </section>

  <section class="notes">
    <h2>Notas al pie</h2>
    <ul>
      <li>Fuente: extracto consolidado de Revolut, enero–noviembre de 2026. Fuera quedan los cambios
        de divisa, los redondeos de RevPoints y los traspasos entre cuentas propias.</li>
      <li>Las categorías salen de reglas sobre el nombre del comercio, no de la app del banco: algún
        cargo puede caer en la categoría vecina. Las transferencias a personas van sin nombre.</li>
      <li>Noviembre está incompleto (hasta el día {today.day}). Octubre cierra con dos cargos de
        alquiler, el 6 y el 30: el segundo corresponde al mes siguiente.</li>
      <li>El supermercado sale a {eur(weekly,0)} por semana, contando solo los meses completos.</li>
    </ul>
  </section>

  <footer><span>álvaro menéndez · {today.strftime('%d/%m/%Y')}</span>
    <span><a href="https://dkealvaro.github.io/">dkealvaro.github.io</a></span></footer>
</div>
</body>
</html>"""
    path = os.path.join(outdir, "index.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(doc)
    print(f"wrote {path} ({len(doc)/1024:.1f} kB) — {len(spend)} cargos, {eur(total,0)}")

if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ".")
