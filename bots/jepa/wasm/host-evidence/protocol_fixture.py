"""Standard-library-only v2 probe for interpreter overhead, not a JEPA bot."""
import json
import sys


def send(message):
    sys.stdout.write(json.dumps(message, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def receive():
    line = sys.stdin.readline()
    if not line:
        raise EOFError("referee closed stdin")
    return json.loads(line)


def simulate(operation, **fields):
    send({"t": "sim", "op": operation, **fields})
    reply = receive()
    if reply.get("t") != "simulated" or reply.get("op") != operation:
        raise ValueError("unexpected simulation reply")
    return reply


while True:
    try:
        message = receive()
    except EOFError:
        break
    if message.get("t") == "hello":
        if 2 not in message.get("versions", []):
            raise ValueError("probe requires protocol v2")
        send({"t": "ready", "v": 2, "name": "v2_interpreter_probe", "sim": True})
    elif message.get("t") == "decide":
        if message.get("sim"):
            position = simulate("begin", deal=0)
            for _ in range(2):
                if position.get("over") or position.get("error"):
                    break
                position = simulate("act", i=0)
            simulate("end")
        send({"t": "act", "i": 0})
    elif message.get("t") == "over":
        send({"t": "ok"})
    else:
        raise ValueError("unexpected referee message")
