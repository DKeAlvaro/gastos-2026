# gastos-2026

One year of personal spending, read from a Revolut consolidated statement: where the money of a
master's student in Eindhoven actually goes, month by month.

Page: https://dkealvaro.github.io/gastos-2026/

## Build

```sh
python build.py path/to/consolidated-statement.csv .
```

`build.py` parses the statement, classifies each merchant with keyword rules (see `RULES` in the
shared parser), strips personal names from peer-to-peer transfers and writes a single
self-contained `index.html` (fonts embedded as base64, no external requests).

The statement CSV is never committed — only the generated page is.
