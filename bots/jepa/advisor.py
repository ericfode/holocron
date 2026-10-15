"""A stdio bot that plays jepa_bot.py but answers some kinds of prompts with another stdio bot (the advisor, e.g.
c-clock), to price each kind of decision in play: the win-rate change when only that kind is answered by the advisor.

python3 bots/jepa/advisor.py --advisor bots/c/swu-c --swap resource[,mulligan,other,window] -- <jepa_bot.py arguments>

Both bots see every protocol message, so each keeps its own game state; the advisor never gets simulations (decide is
sent to it with "sim": false). Kinds, from the prompt: mulligan (title mentions mulligan), window (an action window:
the whole move choice), resource (features.prompt_type 1), other (targets, ability choices, triggers, distribute,
initiative, ...). When windows are swapped, jepa_bot.py is also told there is no simulator, so it does not plan moves
whose answer is thrown away. Counts of swapped and kept decisions per kind go to stderr at each game's end.
"""
import argparse
import json
import os
import shlex
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import features as F  # noqa: E402


def kind(msg):
    p = msg.get("prompt") or {}
    t = F.prompt_type(p)
    if t == 8:
        return "mulligan"
    if p.get("actionWindow"):
        return "window"
    if t == 1:
        return "resource"
    return "other"


class Child:
    def __init__(self, cmd):
        self.p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1, cwd=os.path.dirname(HERE) + "/..")

    def send(self, obj):
        self.p.stdin.write(json.dumps(obj) + "\n")
        self.p.stdin.flush()

    def read(self):
        while True:
            line = self.p.stdout.readline()
            if not line:
                raise EOFError("child closed its output")
            if line.strip():
                return json.loads(line)


def main():
    if "--" not in sys.argv:
        sys.exit("usage: advisor.py --advisor <cmd> --swap kinds -- <jepa_bot.py args>")
    cut = sys.argv.index("--")
    ap = argparse.ArgumentParser()
    ap.add_argument("--advisor", required=True, help="the advisor's command line, e.g. bots/c/swu-c")
    ap.add_argument("--swap", default="", help="kinds answered by the advisor: mulligan, resource, other, window (comma list)")
    a = ap.parse_args(sys.argv[1:cut])
    swap = set(k for k in a.swap.split(",") if k)
    jepa = Child([sys.executable, os.path.join(HERE, "jepa_bot.py"), *sys.argv[cut + 1:]])
    adv = Child(shlex.split(a.advisor))
    out = lambda obj: (sys.stdout.write(json.dumps(obj) + "\n"), sys.stdout.flush())
    counts = {}
    while True:
        line = sys.stdin.readline()  # one reader for everything, simulation answers included
        if not line:
            break
        if not line.strip():
            continue
        msg = json.loads(line)
        t = msg.get("t")
        if t == "decide":
            k = kind(msg)
            use = k in swap
            adv.send({**msg, "sim": False})
            a_reply = adv.read()
            jepa.send({**msg, "sim": False} if (use and k == "window") else msg)
            while True:
                r = jepa.read()
                if r.get("t") != "sim":
                    break
                out(r)  # the planner's simulation request goes to the referee; its answer comes back on stdin
                jepa.send(json.loads(sys.stdin.readline()))
            pick = a_reply if use and a_reply.get("t") == "act" else r
            counts[(k, use)] = counts.get((k, use), 0) + 1
            out({"t": "act", "i": int(pick["i"])})
        elif t == "hello":
            jepa.send(msg)
            r = jepa.read()
            adv.send(msg)
            adv.read()
            counts = {}
            out(r)
        elif t == "bye":
            jepa.send(msg)
            adv.send(msg)
            break
        else:
            jepa.send(msg)
            r = jepa.read()
            adv.send(msg)
            adv.read()  # c-clock answers every message, an error line for the ones it does not know
            if t == "over":
                print("advisor: " + ", ".join(f"{k} {'swapped' if u else 'kept'} {n}" for (k, u), n in sorted(counts.items())), file=sys.stderr, flush=True)
            out(r)


if __name__ == "__main__":
    main()
