"""Naming system.

Why it scales: (1) only *main* people (>= main_person_min_photos photos) get a number, everyone else
goes to People/Others; (2) the page is sorted by photo count, so naming the top rows covers most
photos and you can stop anytime; (3) look-alike numbers are flagged so one person is not named
twice; (4) every name goes into the face library, so the next shoot names them automatically.

Workflow: open People/_Name these people.html -> type names -> "Download names.csv" (or copy the
text) -> `photoflow apply-names <folder> names.csv`.
"""
import base64
import csv
import html
import io
import json
import re
from pathlib import Path

import numpy as np

from .faces import PEOPLE, load_library, save_library

PAGE = "_Name these people.html"
LINE = re.compile(r"^\s*(?:#|person\s*)?0*(\d+)\s*[,:=\t\- ]\s*(.+?)\s*$", re.I)


def clean_name(n):
    n = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", n).strip().rstrip(".")
    return n[:80]


def write_page(ws, people, st):
    (ws.dir / "people.json").write_text(json.dumps(people), "utf-8")
    todo = [(lb, p) for lb, p in people.items() if not p["named"]]
    todo.sort(key=lambda x: -x[1]["photos"])
    cents = {lb: np.array(p["centroid"]) for lb, p in people.items()}
    cards = []
    for lb, p in todo:
        num = lb.split()[-1]
        sims = sorted(((float(cents[lb] @ c), o) for o, c in cents.items() if o != lb), reverse=True)
        hint = ""
        if sims and sims[0][0] >= st.merge_hint:
            other = sims[0][1]
            target = other if people[other]["named"] else "#" + other.split()[-1]
            hint = (f'<button class="hint" data-v="={html.escape(target)}">Same person as '
                    f'{html.escape(target)}?</button>')
        imgs = "".join(
            f'<img alt="" src="data:image/jpeg;base64,{base64.b64encode((ws.dir / "crops" / c).read_bytes()).decode()}">'
            for c in p["crops"] if (ws.dir / "crops" / c).exists())
        cards.append(f'<div class="card"><div class="faces">{imgs}</div><div class="meta"><b>#{num}</b>'
                     f'<span>{p["photos"]} photos</span></div><input data-n="{num}" placeholder="Name (leave blank = skip)">{hint}</div>')
    known = sorted(lb for lb, p in people.items() if p["named"])
    page = TEMPLATE.replace("{{CARDS}}", "\n".join(cards) or "<p>Everyone is already named 🎉</p>") \
        .replace("{{COUNT}}", str(len(todo))).replace("{{KNOWN}}", html.escape(", ".join(known)) or "none yet") \
        .replace("{{MIN}}", str(st.main_person_min_photos))
    out = ws.root / PEOPLE / PAGE
    out.parent.mkdir(exist_ok=True)
    out.write_text(page, "utf-8")
    return out


def parse_names(text):
    pairs = []
    rows = list(csv.reader(io.StringIO(text)))
    if rows and [c.strip().lower() for c in rows[0][:2]] == ["number", "name"]:
        pairs = [(r[0].strip().lstrip("#"), r[1]) for r in rows[1:] if len(r) >= 2 and r[1].strip()]
    else:
        for line in text.splitlines():
            m = LINE.match(line)
            if m:
                pairs.append((m.group(1), m.group(2)))
    return [(f"Person {int(n):03d}", v.strip()) for n, v in pairs if v.strip()]


def apply_names(ws, text, log=print):
    people = json.loads((ws.dir / "people.json").read_text("utf-8"))
    pairs = parse_names(text)
    final = {}
    for lb, v in pairs:  # "=#7" / "=Arjun" means "same person as"
        final[lb] = v
    def resolve(v, seen=()):
        if v.startswith("="):
            t = v[1:].strip()
            m = re.match(r"#?0*(\d+)$", t)
            if m:
                lb = f"Person {int(m.group(1)):03d}"
                return resolve(final.get(lb, lb), seen + (lb,)) if lb not in seen else lb
            return t
        return v
    lib = load_library()
    renamed = 0
    for lb, v in final.items():
        name = clean_name(resolve(v))
        if not name or lb not in people:
            continue
        for base in (PEOPLE, "360"):
            if (ws.root / base / lb).exists():
                ws.rename_folder(f"{base}/{lb}", f"{base}/{name}", "apply-names")
                renamed += 1
        embs = lib.setdefault(name, [])
        embs.extend(people[lb]["sample_embs"])
        lib[name] = embs[-60:]
        people[name] = {**people.pop(lb), "named": True}
    save_library(lib)
    (ws.dir / "people.json").write_text(json.dumps(people), "utf-8")
    ws.save()
    log(f"Named {len(final)} people ({renamed} folders renamed). Face library now knows {len(lib)} people.")


TEMPLATE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Name these people</title>
<style>
:root{--bg:#f6f5f2;--card:#fff;--ink:#1d1d1f;--mute:#6b6b70;--line:#e3e1dc;--acc:#2f5bea}
@media (prefers-color-scheme:dark){:root{--bg:#141416;--card:#1e1e22;--ink:#f2f2f4;--mute:#a0a0a8;--line:#2e2e34;--acc:#7c9bff}}
*{box-sizing:border-box}body{margin:0;font:15px/1.45 system-ui,-apple-system,Segoe UI,sans-serif;background:var(--bg);color:var(--ink)}
header{position:sticky;top:0;z-index:2;background:var(--bg);border-bottom:1px solid var(--line);padding:14px 16px;display:flex;flex-wrap:wrap;gap:10px;align-items:center}
h1{font-size:18px;margin:0 auto 0 0}header p{margin:0;color:var(--mute);width:100%;font-size:13px}
button{font:inherit;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:8px;padding:7px 12px;cursor:pointer}
button.primary{background:var(--acc);border-color:var(--acc);color:#fff}
main{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px;padding:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px;display:flex;flex-direction:column;gap:8px}
.faces{display:grid;grid-template-columns:repeat(4,1fr);gap:4px}.faces img{width:100%;aspect-ratio:1;object-fit:cover;border-radius:6px}
.meta{display:flex;justify-content:space-between;color:var(--mute)}.meta b{color:var(--ink)}
input{font:inherit;padding:8px;border:1px solid var(--line);border-radius:8px;background:transparent;color:var(--ink);width:100%}
.hint{font-size:12px;padding:4px 8px;align-self:flex-start}
textarea{width:100%;min-height:120px;font:13px ui-monospace,monospace;margin:0 16px 16px;max-width:calc(100% - 32px)}
</style></head><body>
<header><h1>Name these people ({{COUNT}})</h1>
<button onclick="copyText()">Copy as text</button><button class="primary" onclick="download()">Download names.csv</button>
<p>Sorted by how many photos each person is in. Name the top rows and stop whenever you like. Blank = skip.
Only people in at least {{MIN}} photos are listed; everyone else is in People/Others. Already known from your face library: {{KNOWN}}.</p></header>
<main>{{CARDS}}</main>
<textarea id="out" readonly placeholder="Your names appear here"></textarea>
<script>
const inputs=[...document.querySelectorAll('input[data-n]')];
const key='photoflow-names-'+document.title+location.pathname;
try{const s=JSON.parse(localStorage.getItem(key)||'{}');inputs.forEach(i=>{if(s[i.dataset.n])i.value=s[i.dataset.n]})}catch(e){}
function rows(){return inputs.filter(i=>i.value.trim()).map(i=>[i.dataset.n,i.value.trim()])}
function refresh(){document.getElementById('out').value=rows().map(r=>'#'+r[0]+' '+r[1]).join('\n');
 try{localStorage.setItem(key,JSON.stringify(Object.fromEntries(rows())))}catch(e){}}
inputs.forEach(i=>i.addEventListener('input',refresh));
document.querySelectorAll('.hint').forEach(b=>b.onclick=()=>{const i=b.parentElement.querySelector('input');i.value=b.dataset.v;refresh()});
function download(){const csv='number,name\n'+rows().map(r=>r[0]+',"'+r[1].replace(/"/g,'""')+'"').join('\n');
 const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));a.download='names.csv';a.click()}
function copyText(){refresh();const t=document.getElementById('out');t.select();navigator.clipboard&&navigator.clipboard.writeText(t.value)}
refresh();
</script></body></html>"""
