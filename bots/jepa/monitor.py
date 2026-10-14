"""Live progress page for a long JEPA run: branch data parts, training runs and their curves, with an ETA.

python bots/jepa/monitor.py --data-logs "data/branch/st-*.log" --run-logs "runs/*.txt" \
    --parts 10 --games 3000 --runs tx-s10=30000,tx-s10a=30000,pool-10=30000 [--port 8765] [--host 127.0.0.1]
then open http://localhost:8765 (it refreshes itself). Standard library only; reads the logs the scripts already
write and changes nothing:
  branches.js       "<done>/<games> games, <points> branch points, <s> s/game, ..."  (one log per part, sorted by name)
  tx_train_torch.py "step <it> <secs>s (<rate> it/s) total=..." and "  held-out ... moves_explained_*=..." (one log per
                    run, named <run>.txt or <run>.log), "wrote <run>.safetensors" when the run is done.
Progress samples are kept in --history (default monitor-history.json) so the graph survives a restart.
"""
import argparse
import glob
import json
import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

GAMES_RE = re.compile(r"^(\d+)/(\d+) games, (\d+) branch points, ([\d.]+) s/game")
WROTE_DATA_RE = re.compile(r"^wrote .* in (\d+)s: (\d+) branch points")
STEP_RE = re.compile(r"^step (\d+) (\d+)s \(([\d.]+) it/s\) total=([\d.]+)")
HELD_RE = re.compile(r"^\s+held-out (.*)")
KV_RE = re.compile(r"(\w+)=([-\d.eE+]+)")
WROTE_RUN_RE = re.compile(r"^wrote .*\.safetensors in (\d+)s")
JUDGE_RE = re.compile(r"^\s+fixed judge (\S+): top-1 ([\d.]+)")


def read_text(path):
    """A log as text, whichever way the shell wrote it (PowerShell's > writes UTF-16)."""
    with open(path, "rb") as f:
        raw = f.read()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff") or raw[1:2] == b"\x00":
        return raw.decode("utf-16", errors="replace")
    return raw.decode("utf-8", errors="replace")


def parse_part(path, games_per_part):
    st = {"name": os.path.splitext(os.path.basename(path))[0], "done": 0, "games": games_per_part, "points": 0,
          "s_per_game": None, "finished": False, "mtime": os.path.getmtime(path)}
    for line in read_text(path).replace("\r", "\n").splitlines():
        m = GAMES_RE.match(line)
        if m:
            st.update(done=int(m[1]), games=int(m[2]), points=int(m[3]), s_per_game=float(m[4]))
        m = WROTE_DATA_RE.match(line)
        if m:
            st.update(finished=True, done=st["games"], points=int(m[2]))
    return st


def parse_run(path, steps):
    st = {"name": os.path.splitext(os.path.basename(path))[0], "step": 0, "steps": steps, "rate": None, "finished": False,
          "curve": [], "held": [], "judge": {}, "mtime": os.path.getmtime(path)}
    for line in read_text(path).replace("\r", "\n").splitlines():
        m = STEP_RE.match(line)
        if m:
            st.update(step=int(m[1]), rate=float(m[3]))
            st["curve"].append([int(m[1]), float(m[4])])
            continue
        m = HELD_RE.match(line)
        if m:
            kv = {k: float(v) for k, v in KV_RE.findall(m[1])}
            st["held"].append({"step": st["step"], **{k: kv[k] for k in kv if k == "total" or k.startswith("moves_explained")}})
            continue
        m = JUDGE_RE.match(line)
        if m:
            st["judge"][m[1]] = float(m[2])
            continue
        if WROTE_RUN_RE.match(line):
            st.update(finished=True, step=st["steps"])
    return st


class Monitor:
    def __init__(self, a):
        self.a = a
        self.runs = dict(kv.split("=") for kv in a.runs.split(",") if kv) if a.runs else {}
        self.history = []
        if os.path.exists(a.history):
            try:
                self.history = json.load(open(a.history))
            except ValueError:
                self.history = []
        self.state = {}
        self.lock = threading.Lock()

    def scan(self):
        a = self.a
        parts = [parse_part(p, a.games) for p in sorted(glob.glob(a.data_logs))] if a.data_logs else []
        logs = {}
        for p in sorted(glob.glob(a.run_logs)) if a.run_logs else []:
            name = os.path.splitext(os.path.basename(p))[0]
            if name in self.runs:
                logs[name] = p
        runs = [parse_run(logs[n], int(s)) if n in logs else {"name": n, "step": 0, "steps": int(s), "rate": None, "finished": False,
                                                              "curve": [], "held": [], "judge": {}}
                for n, s in self.runs.items()]
        # time left: unfinished data at the measured pace (parts not started yet at the last part's pace), then the runs in
        # order, each at its own rate or the last measured one
        pace = next((p["s_per_game"] for p in reversed(parts) if p["s_per_game"]), None)
        n_parts = max(a.parts, len(parts))
        data_left = None
        if pace:
            left_games = sum(p["games"] - p["done"] for p in parts if not p["finished"]) + (n_parts - len(parts)) * a.games
            data_left = left_games * pace
        rate = next((r["rate"] for r in reversed(runs) if r["rate"]), None) or a.default_rate
        train_left = sum((r["steps"] - r["step"]) / (r["rate"] or rate) for r in runs if not r["finished"])
        games_done = sum(p["done"] for p in parts)
        games_all = n_parts * a.games
        steps_done = sum(r["step"] for r in runs)
        steps_all = sum(r["steps"] for r in runs) or 1
        # overall share done, weighting data and training by their measured durations
        data_total = games_all * pace if pace else None
        train_total = sum(r["steps"] / (r["rate"] or rate) for r in runs)
        if data_total:
            done = (games_done * pace + (train_total - train_left)) / (data_total + train_total)
        else:
            done = steps_done / steps_all
        left = (data_left or 0) + train_left
        now = time.time()
        with self.lock:
            if not self.history or now - self.history[-1][0] >= a.every - 1:
                self.history.append([now, round(done * 100, 2)])
                json.dump(self.history, open(a.history, "w"))
            self.state = {"now": now, "done": done, "left_s": left, "eta": now + left, "data_left_s": data_left, "train_left_s": train_left,
                          "games_done": games_done, "games_all": games_all, "points": sum(p["points"] for p in parts),
                          "parts": parts, "n_parts": n_parts, "runs": runs, "history": self.history}

    def loop(self):
        while True:
            try:
                self.scan()
            except Exception as e:  # a log half-written by a running script: try again next time
                print("scan failed:", e)
            time.sleep(self.a.every)


PAGE = r"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>JEPA run progress</title><style>
:root{--bg:#f7f7f5;--card:#fff;--ink:#1d1d1b;--mute:#6b6b66;--line:#e2e2dc;--a:#2f6fdf;--b:#d9822b;--c:#2e9e6b;--d:#9b59b6}
@media (prefers-color-scheme:dark){:root{--bg:#141413;--card:#1f1f1d;--ink:#ececea;--mute:#9a9a94;--line:#33332f;--a:#6ea0ff;--b:#f0a35a;--c:#4cc38a;--d:#c08ad8}}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:960px;margin:0 auto;padding:20px 16px 40px}
h1{font-size:20px;margin:0 0 4px}.sub{color:var(--mute);margin-bottom:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:12px 0}
.big{font-size:34px;font-weight:650}.row{display:flex;gap:24px;flex-wrap:wrap;align-items:baseline}
.k{color:var(--mute);font-size:13px}.bar{height:10px;background:var(--line);border-radius:5px;overflow:hidden}
.bar>i{display:block;height:100%;background:var(--a)}.item{display:grid;grid-template-columns:110px 1fr 150px;gap:10px;align-items:center;margin:6px 0}
.item span:last-child{color:var(--mute);font-size:13px;text-align:right}svg{width:100%;height:auto;display:block}
.legend span{margin-right:14px;font-size:13px}.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px}
</style></head><body><main>
<h1>JEPA big run</h1><div class="sub" id="sub">loading...</div>
<div class="card"><div class="row"><div><div class="big" id="pct">-</div><div class="k">done</div></div>
<div><div class="big" id="eta">-</div><div class="k">estimated finish (local time)</div></div>
<div><div class="big" id="left">-</div><div class="k">left</div></div></div>
<svg id="hist" viewBox="0 0 900 220"></svg></div>
<div class="card"><b>Branch data</b> <span class="k" id="datak"></span><div id="parts"></div></div>
<div class="card"><b>Training</b><div id="runs"></div></div>
<div class="card"><b>Training loss</b> <span class="k">(held-out total; lower is better)</span><div class="legend" id="leg"></div><svg id="loss" viewBox="0 0 900 240"></svg></div>
</main><script>
const C=['--a','--b','--c','--d'].map(v=>getComputedStyle(document.documentElement).getPropertyValue(v).trim());
const fmt=s=>{if(s==null)return'-';s=Math.max(0,s);const h=Math.floor(s/3600),m=Math.round(s%3600/60);return h?h+' h '+m+' min':m+' min'};
function chart(svg,series,opt){const W=900,H=+svg.getAttribute('viewBox').split(' ')[3],L=48,R=12,T=10,B=26;
 const pts=series.flatMap(s=>s.pts);if(!pts.length){svg.innerHTML='<text x="20" y="40" fill="currentColor" opacity=".6">no data yet</text>';return}
 let x0=Math.min(...pts.map(p=>p[0])),x1=Math.max(...pts.map(p=>p[0])),y0=opt.y0??Math.min(...pts.map(p=>p[1])),y1=opt.y1??Math.max(...pts.map(p=>p[1]));
 if(x1==x0)x1=x0+1;if(y1==y0)y1=y0+1;const X=x=>L+(x-x0)/(x1-x0)*(W-L-R),Y=y=>T+(1-(y-y0)/(y1-y0))*(H-T-B);
 let g='';for(let i=0;i<=4;i++){const v=y0+(y1-y0)*i/4;g+=`<line x1="${L}" x2="${W-R}" y1="${Y(v)}" y2="${Y(v)}" stroke="currentColor" opacity=".12"/><text x="${L-6}" y="${Y(v)+4}" font-size="11" text-anchor="end" fill="currentColor" opacity=".6">${opt.fy(v)}</text>`}
 for(let i=0;i<=4;i++){const v=x0+(x1-x0)*i/4;g+=`<text x="${X(v)}" y="${H-6}" font-size="11" text-anchor="middle" fill="currentColor" opacity=".6">${opt.fx(v)}</text>`}
 series.forEach((s,i)=>{const c=s.color||C[i%4];g+=`<polyline fill="none" stroke="${c}" stroke-width="2" points="${s.pts.map(p=>X(p[0])+','+Y(p[1])).join(' ')}"/>`;
  const q=s.pts[s.pts.length-1];if(q)g+=`<circle cx="${X(q[0])}" cy="${Y(q[1])}" r="4" fill="${c}"/>`});
 svg.innerHTML=g}
async function tick(){let d;try{d=await (await fetch('data.json',{cache:'no-store'})).json()}catch(e){document.getElementById('sub').textContent='monitor not answering';return}
 document.getElementById('sub').textContent='updated '+new Date(d.now*1000).toLocaleTimeString()+' · '+d.points.toLocaleString()+' branch points so far';
 document.getElementById('pct').textContent=(d.done*100).toFixed(1)+'%';document.getElementById('left').textContent=fmt(d.left_s);
 document.getElementById('eta').textContent=new Date(d.eta*1000).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
 const t0=d.history.length?d.history[0][0]:d.now;
 chart(document.getElementById('hist'),[{pts:d.history.map(p=>[(p[0]-t0)/3600,p[1]])}],{y0:0,y1:100,fy:v=>v.toFixed(0)+'%',fx:v=>v.toFixed(1)+' h'});
 document.getElementById('datak').textContent=d.games_done.toLocaleString()+' of '+d.games_all.toLocaleString()+' games · '+fmt(d.data_left_s)+' left';
 let ph='';for(let i=0;i<d.n_parts;i++){const p=d.parts[i];const f=p?p.done/p.games:0;
  ph+=`<div class="item"><span>${p?p.name:'part '+i}</span><div class="bar"><i style="width:${(f*100).toFixed(1)}%"></i></div><span>${p?(p.finished?'done, '+p.points.toLocaleString()+' points':p.done+' / '+p.games):'waiting'}</span></div>`}
 document.getElementById('parts').innerHTML=ph;
 document.getElementById('runs').innerHTML=d.runs.map((r,i)=>{const f=r.step/r.steps;const j=Object.entries(r.judge).map(([k,v])=>k+' '+v.toFixed(3)).join(', ');
  return `<div class="item"><span>${r.name}</span><div class="bar"><i style="width:${(f*100).toFixed(1)}%;background:${C[i%4]}"></i></div><span>${r.finished?'done':r.step?r.step.toLocaleString()+' / '+r.steps.toLocaleString()+(r.rate?' · '+r.rate+' it/s':''):'waiting'}</span></div>`+(j?`<div class="k" style="margin:-2px 0 6px 120px">fixed judge: ${j}</div>`:'')}).join('');
 document.getElementById('leg').innerHTML=d.runs.map((r,i)=>`<span><i style="background:${C[i%4]}"></i>${r.name}</span>`).join('');
 chart(document.getElementById('loss'),d.runs.map((r,i)=>({pts:r.held.map(h=>[h.step,h.total]),color:C[i%4]})),{fy:v=>v.toFixed(2),fx:v=>Math.round(v/1000)+'k'})}
tick();setInterval(tick,15000);
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-logs", default=None, help="glob of branches.js logs, one per part")
    ap.add_argument("--run-logs", default=None, help="glob of training console logs, named <run>.txt or <run>.log")
    ap.add_argument("--parts", type=int, default=10)
    ap.add_argument("--games", type=int, default=3000, help="games per part")
    ap.add_argument("--runs", default="", help="the planned runs in order, name=steps,...")
    ap.add_argument("--default-rate", type=float, default=9.0, help="it/s assumed before any run has reported")
    ap.add_argument("--every", type=float, default=30.0, help="seconds between scans")
    ap.add_argument("--history", default="monitor-history.json")
    ap.add_argument("--host", default="127.0.0.1", help="0.0.0.0 to open it from other devices on your network")
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    mon = Monitor(a)
    mon.scan()
    threading.Thread(target=mon.loop, daemon=True).start()

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/data.json"):
                with mon.lock:
                    body = json.dumps(mon.state).encode()
                ctype = "application/json"
            else:
                body, ctype = PAGE.encode(), "text/html; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    print(f"monitor on http://{'localhost' if a.host in ('127.0.0.1', '0.0.0.0') else a.host}:{a.port}", flush=True)
    ThreadingHTTPServer((a.host, a.port), H).serve_forever()


if __name__ == "__main__":
    main()
