"""Card data from hello's `cards`: the engine's card JSON, one object per card, for both decks and the tokens.

The `decide` messages name cards by set code, title and internal name but carry no costs or keywords, so the bot
looks them up here. The table is built again at each hello; the bot reads no files.
"""
import re

_N_KEYWORDS = {"raid": re.compile(r"\braid (\d+)"), "restore": re.compile(r"\brestore (\d+)")}


class Card:
    """Static data of one card. Missing numbers are 0, missing lists are empty."""

    __slots__ = ("title", "subtitle", "internal", "cost", "power", "hp", "text", "deploy_text", "types", "keywords",
                 "arena", "aspects", "traits", "up_power", "up_hp", "unique", "raid", "restore")

    def __init__(self, d):
        """Raises TypeError when a field the bot reads has the wrong type (a number for a list, null in a list...)."""
        self.title = _field(d, "title", str) or ""
        self.subtitle = _field(d, "subtitle", str) or ""
        self.internal = _field(d, "internalName", str) or ""
        self.cost = _field(d, "cost", int) or 0
        self.power = _field(d, "power", int) or 0
        self.hp = _field(d, "hp", int) or 0
        self.text = (_field(d, "text", str) or "").lower()
        self.deploy_text = (_field(d, "deployBox", str) or "").lower()
        self.types = set(_strings(d, "types"))
        self.keywords = set(k.lower() for k in _strings(d, "keywords"))
        self.arena = _field(d, "arena", str)
        self.aspects = _strings(d, "aspects")
        self.traits = set(_strings(d, "traits"))
        self.up_power = _field(d, "upgradePower", int) or 0
        self.up_hp = _field(d, "upgradeHp", int) or 0
        self.unique = bool(d.get("unique"))
        text = self.text + " " + self.deploy_text
        self.raid = _first_int(_N_KEYWORDS["raid"], text) if "raid" in self.keywords else 0
        self.restore = _first_int(_N_KEYWORDS["restore"], text) if "restore" in self.keywords else 0

    def is_unit(self):
        return "unit" in self.types

    def is_event(self):
        return "event" in self.types

    def is_upgrade(self):
        return "upgrade" in self.types

    def is_leader(self):
        return "leader" in self.types

    def __repr__(self):
        return "Card(%s %d %d/%d)" % (self.internal, self.cost, self.power, self.hp)


def _field(d, key, kind):
    """d[key] when it is a `kind` (a bool is not a number); None when missing or null; anything else raises TypeError."""
    v = d.get(key)
    if v is None:
        return None
    if not isinstance(v, kind) or (isinstance(v, bool) and kind is not bool):
        raise TypeError("card %r: %s is %r" % (d.get("internalName"), key, v))
    return v


def _strings(d, key):
    """d[key] as a list of strings; empty when missing or null."""
    v = _field(d, key, list) or []
    if not all(isinstance(x, str) for x in v):
        raise TypeError("card %r: %s is %r" % (d.get("internalName"), key, v))
    return list(v)


def _first_int(rx, text):
    m = rx.search(text)
    return int(m.group(1)) if m else 1


def set_code(set_id):
    if set_id.get("set") is None or set_id.get("number") is None:
        return None
    return "%s_%03d" % (set_id["set"], set_id["number"])


class CardDb:
    def __init__(self):
        self.by_set = {}
        self.by_internal = {}
        self.by_title = {}

    def add(self, d):
        """Adds one card object; one with a field of the wrong type raises before anything is added."""
        c = Card(d)
        codes = [set_code(sid) for sid in _field(d, "setCodes", list) or ([d["setId"]] if d.get("setId") else [])]
        for code in codes:
            if code:
                self.by_set.setdefault(code, c)
        if c.internal:
            self.by_internal[c.internal] = c
        self.by_title.setdefault(c.title.lower(), c)
        return c

    @classmethod
    def from_cards(cls, cards):
        """The table of hello's `cards` (a list of card objects), in its order. Anything that does not read as a card (not
        an object, or a field of the wrong type) is skipped, so one odd card costs only itself."""
        db = cls()
        for d in cards if isinstance(cards, list) else []:
            if isinstance(d, dict):
                try:
                    db.add(d)
                except Exception:  # whatever the odd shape, skip this card and keep the others
                    pass
        return db

    def __len__(self):
        return len(self.by_internal)

    def find(self, s=None, label=None, title=None):
        """Best match for a card seen on the wire: set code, then internal name (action label), then title."""
        if s and s in self.by_set:
            return self.by_set[s]
        if label and label in self.by_internal:
            return self.by_internal[label]
        if title:
            return self.by_title.get(title.lower())
        return None


def aspect_penalty(card, have):
    """Extra cost: 2 per aspect icon on the card that the leader and base do not provide (icons count with repeats)."""
    pool = list(have)
    missing = 0
    for a in card.aspects:
        if a in pool:
            pool.remove(a)
        else:
            missing += 1
    return 2 * missing
