//! Opt-in, unordered own-pile accounting from explicitly trusted public events.
//!
//! No protocol snapshots, hidden decks, opponent hands, or engine are read here.
//! A new visible instance is NOT evidence of an original draw: callers must know
//! its provenance. The current bot protocol cannot supply that complete history,
//! so this module is intentionally not wired into JepaBot automatically.
use crate::features::Encoded;
use crate::own_deck::{normalize_code, OwnDeckContext, OwnDeckVariant, ROW_DIM};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::{BTreeMap, BTreeSet};

const MAX_SAFE: u64 = 9_007_199_254_740_991;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum Zone {
    OwnDeck,
    Hand,
    Resource,
    Ground,
    Space,
    Attached,
    Captured,
    Discard,
    Removed,
    /// A known original instance outside our pile, under another controller.
    PublicOther,
    /// Explicitly observed transfer out of our pile, without reading that zone.
    ExternalPrivate,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum Origin {
    Original,
    Generated,
    /// Publicly known card acquired from outside the original own list.
    External,
    Unknown,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Identity {
    pub id: String,
    pub code: String,
    pub origin: Origin,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Observed {
    pub id: String,
    pub code: String,
    pub zone: Zone,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Instance {
    pub code: String,
    pub origin: Origin,
    pub zone: Zone,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "kebab-case")]
pub enum Event {
    /// Initial dealt cards or a witnessed draw. Batch order is discarded.
    Draw {
        cards: Vec<Identity>,
    },
    /// A search/reveal observes identities still IN the pile; no subtraction.
    Reveal {
        cards: Vec<Identity>,
    },
    Move {
        id: String,
        from: Zone,
        to: Zone,
    },
    Create {
        id: String,
        code: String,
        to: Zone,
    },
    Acquire {
        id: String,
        code: String,
        to: Zone,
    },
    /// Reordering alone changes neither membership nor the model context.
    Shuffle,
    /// A count never supplies missing identities.
    UnobservedDraw {
        count: u64,
    },
    Gap {
        reason: String,
    },
}

#[derive(Debug, Clone, PartialEq)]
pub struct RemainingLedger {
    game: String,
    original: BTreeMap<String, u64>,
    original_context: OwnDeckContext,
    cards: Value,
    aliases: BTreeMap<String, BTreeSet<String>>,
    non_main: BTreeSet<String>,
    instances: BTreeMap<String, Instance>,
    events: BTreeMap<String, Event>,
    unknown: BTreeSet<String>,
}

fn code_of(v: &Value) -> Option<String> {
    normalize_code(&format!(
        "{}_{}",
        v.get("set")?.as_str()?,
        v.get("number")?.as_u64()?
    ))
}

impl RemainingLedger {
    /// `history_complete` is an explicit trusted seam, NEVER inferred from size.
    /// New games construct a fresh ledger; original row and public catalog freeze.
    pub fn from_original(game: &str, deck: &Value, cards: &Value, history_complete: bool) -> Self {
        let mut out = Self {
            game: game.into(),
            original: BTreeMap::new(),
            original_context: OwnDeckContext::from_original(
                OwnDeckVariant::OriginalPlusRemaining,
                deck,
                cards,
            ),
            cards: cards.clone(),
            aliases: BTreeMap::new(),
            non_main: BTreeSet::new(),
            instances: BTreeMap::new(),
            events: BTreeMap::new(),
            unknown: BTreeSet::new(),
        };
        if game.is_empty() {
            out.unknown.insert("missing-game-key".into());
        }
        if !history_complete {
            out.unknown.insert("incomplete-history".into());
        }
        for card in cards.as_array().map(Vec::as_slice).unwrap_or(&[]) {
            let mut codes: BTreeSet<String> = card
                .get("setCodes")
                .and_then(Value::as_array)
                .into_iter()
                .flatten()
                .filter_map(code_of)
                .collect();
            let preferred = card.get("setId").and_then(code_of);
            if let Some(code) = &preferred {
                codes.insert(code.clone());
            }
            let Some(canonical) = preferred.or_else(|| codes.first().cloned()) else {
                continue;
            };
            let excluded = card
                .get("types")
                .and_then(Value::as_array)
                .into_iter()
                .flatten()
                .filter_map(Value::as_str)
                .any(|t| {
                    ["leader", "base", "token"]
                        .iter()
                        .any(|k| t.to_lowercase().contains(k))
                });
            if excluded {
                out.non_main.insert(canonical.clone());
            }
            for code in codes {
                out.aliases
                    .entry(code)
                    .or_default()
                    .insert(canonical.clone());
            }
        }
        let Some(entries) = deck.get("deck").and_then(Value::as_array) else {
            out.unknown.insert("incomplete-original-roster".into());
            return out;
        };
        for entry in entries {
            let parsed = entry
                .get("id")
                .and_then(Value::as_str)
                .ok_or("missing-code")
                .and_then(|c| out.resolve(c))
                .and_then(|code| {
                    entry
                        .get("count")
                        .and_then(Value::as_u64)
                        .filter(|n| *n > 0 && *n <= MAX_SAFE)
                        .map(|n| (code, n))
                        .ok_or("invalid-count")
                });
            match parsed {
                Ok((code, n)) if !out.non_main.contains(&code) => {
                    let old = out.original.entry(code).or_default();
                    if let Some(sum) = old.checked_add(n).filter(|n| *n <= MAX_SAFE) {
                        *old = sum;
                    } else {
                        out.unknown.insert("original-count-overflow".into());
                    }
                }
                _ => {
                    out.unknown.insert("incomplete-original-roster".into());
                }
            }
        }
        if out.original.values().map(|n| u128::from(*n)).sum::<u128>() > u128::from(MAX_SAFE) {
            out.unknown.insert("original-total-overflow".into());
        }
        out
    }

    fn resolve(&self, code: &str) -> Result<String, &'static str> {
        let code = normalize_code(code).ok_or("invalid-printed-code")?;
        match self.aliases.get(&code) {
            Some(names) if names.len() == 1 => Ok(names.first().unwrap().clone()),
            Some(_) => Err("ambiguous-printed-alias"),
            None => Ok(code),
        }
    }

    pub fn game(&self) -> &str {
        &self.game
    }
    pub fn unknown_reasons(&self) -> &BTreeSet<String> {
        &self.unknown
    }
    pub fn instances(&self) -> &BTreeMap<String, Instance> {
        &self.instances
    }
    pub fn original_counts(&self) -> &BTreeMap<String, u64> {
        &self.original
    }
    pub fn checkpoint(&self) -> Self {
        self.clone()
    }

    /// Explicit branch restore; never restore a snapshot from another game/list.
    pub fn restore(&mut self, checkpoint: &Self) -> Result<(), String> {
        if self.game != checkpoint.game
            || self.original != checkpoint.original
            || self.original_context != checkpoint.original_context
            || self.cards != checkpoint.cards
        {
            return self.fail("checkpoint-game-or-roster-mismatch");
        }
        *self = checkpoint.clone();
        Ok(())
    }

    fn fail<T>(&mut self, reason: &str) -> Result<T, String> {
        self.unknown.insert(reason.into());
        Err(reason.into())
    }

    fn normalize_event(&self, event: Event) -> Result<Event, String> {
        let ident = |mut card: Identity| -> Result<Identity, String> {
            if card.id.is_empty() || card.id == "hidden" {
                return Err("missing-stable-instance".into());
            }
            card.code = self.resolve(&card.code).map_err(String::from)?;
            if card.origin == Origin::Unknown {
                return Err("unknown-instance-origin".into());
            }
            Ok(card)
        };
        let batch = |cards: Vec<Identity>| -> Result<Vec<Identity>, String> {
            let mut cards = cards
                .into_iter()
                .map(ident)
                .collect::<Result<Vec<_>, _>>()?;
            cards.sort_by(|a, b| a.id.cmp(&b.id));
            if cards.windows(2).any(|w| w[0].id == w[1].id) {
                return Err("duplicate-instance-in-batch".into());
            }
            Ok(cards)
        };
        Ok(match event {
            Event::Draw { cards } => Event::Draw {
                cards: batch(cards)?,
            },
            Event::Reveal { cards } => Event::Reveal {
                cards: batch(cards)?,
            },
            Event::Create { id, code, to } => {
                let c = ident(Identity {
                    id,
                    code,
                    origin: Origin::Generated,
                })?;
                Event::Create {
                    id: c.id,
                    code: c.code,
                    to,
                }
            }
            Event::Acquire { id, code, to } => {
                let c = ident(Identity {
                    id,
                    code,
                    origin: Origin::External,
                })?;
                Event::Acquire {
                    id: c.id,
                    code: c.code,
                    to,
                }
            }
            other => other,
        })
    }

    /// Idempotent event IDs tolerate replay; conflicts invalidate atomically.
    /// Errors preserve the last consistent instance map and make knowledge unknown.
    pub fn apply(&mut self, event_id: &str, event: Event) -> Result<bool, String> {
        if event_id.is_empty() {
            return self.fail("missing-event-id");
        }
        let event = match self.normalize_event(event) {
            Ok(e) => e,
            Err(e) => return self.fail(&e),
        };
        if let Some(old) = self.events.get(event_id) {
            return if *old == event {
                Ok(false)
            } else {
                self.fail("conflicting-event-replay")
            };
        }
        let mut next = self.clone();
        if let Err(e) = next
            .apply_inner(&event)
            .and_then(|_| next.conserved_counts().map(|_| ()))
        {
            return self.fail(&e);
        }
        next.events.insert(event_id.into(), event);
        *self = next;
        Ok(true)
    }

    fn register(&mut self, card: &Identity, zone: Zone) -> Result<(), String> {
        if self.instances.contains_key(&card.id) {
            return Err("duplicate-instance-registration".into());
        }
        if zone == Zone::OwnDeck && self.non_main.contains(&card.code) {
            return Err("non-main-card-in-draw-pile".into());
        }
        self.instances.insert(
            card.id.clone(),
            Instance {
                code: card.code.clone(),
                origin: card.origin,
                zone,
            },
        );
        Ok(())
    }

    fn apply_inner(&mut self, event: &Event) -> Result<(), String> {
        match event {
            Event::Draw { cards } | Event::Reveal { cards } => {
                let dest = if matches!(event, Event::Draw { .. }) {
                    Zone::Hand
                } else {
                    Zone::OwnDeck
                };
                for card in cards {
                    if let Some(old) = self.instances.get_mut(&card.id) {
                        if old.code != card.code
                            || old.origin != card.origin
                            || old.zone != Zone::OwnDeck
                        {
                            return Err("draw-or-reveal-instance-conflict".into());
                        }
                        old.zone = dest;
                    } else {
                        if card.origin != Origin::Original {
                            return Err("untracked-nonoriginal-deck-instance".into());
                        }
                        self.register(card, dest)?;
                    }
                }
            }
            Event::Move { id, from, to } => {
                let card = self
                    .instances
                    .get_mut(id)
                    .ok_or("untracked-instance-movement")?;
                if card.zone != *from {
                    return Err("movement-source-zone-mismatch".into());
                }
                if *to == Zone::OwnDeck && self.non_main.contains(&card.code) {
                    return Err("non-main-card-in-draw-pile".into());
                }
                card.zone = *to;
            }
            Event::Create { id, code, to } | Event::Acquire { id, code, to } => {
                let origin = if matches!(event, Event::Create { .. }) {
                    Origin::Generated
                } else {
                    Origin::External
                };
                self.register(
                    &Identity {
                        id: id.clone(),
                        code: code.clone(),
                        origin,
                    },
                    *to,
                )?;
            }
            Event::Shuffle => {}
            Event::UnobservedDraw { .. } => return Err("draw-identities-unobserved".into()),
            Event::Gap { .. } => return Err("incomplete-event-history".into()),
        }
        Ok(())
    }

    fn conserved_counts(&self) -> Result<BTreeMap<String, u64>, String> {
        let mut counts = self.original.clone();
        let mut original_seen: BTreeMap<&str, u64> = BTreeMap::new();
        for card in self.instances.values() {
            if card.origin == Origin::Unknown {
                return Err("unknown-instance-origin".into());
            }
            if card.origin == Origin::Original {
                let seen = original_seen.entry(&card.code).or_default();
                *seen += 1;
                if *seen > self.original.get(&card.code).copied().unwrap_or(0) {
                    return Err("original-instance-conservation-failed".into());
                }
                if card.zone != Zone::OwnDeck {
                    let n = counts
                        .get_mut(&card.code)
                        .ok_or("original-code-not-declared")?;
                    *n = n.checked_sub(1).ok_or("negative-remaining-count")?;
                }
            } else if card.zone == Zone::OwnDeck {
                let n = counts.entry(card.code.clone()).or_default();
                *n = n
                    .checked_add(1)
                    .filter(|n| *n <= MAX_SAFE)
                    .ok_or("remaining-count-overflow")?;
            }
        }
        counts.retain(|_, n| *n > 0);
        if counts.values().map(|n| u128::from(*n)).sum::<u128>() > u128::from(MAX_SAFE) {
            return Err("remaining-total-overflow".into());
        }
        Ok(counts)
    }

    pub fn known_counts(&self) -> Option<BTreeMap<String, u64>> {
        if self.unknown.is_empty() {
            self.conserved_counts().ok()
        } else {
            None
        }
    }

    /// Actor-visible instance reconciliation only. No unseen identities are made
    /// from deck size; missing/novel/changed instance identities fail closed.
    /// `complete_zones` applies only to zones actually fully visible to the actor.
    pub fn reconcile(
        &mut self,
        observed: &[Observed],
        complete_zones: &BTreeSet<Zone>,
        deck_size: Option<u64>,
    ) -> Result<(), String> {
        if complete_zones.contains(&Zone::OwnDeck)
            || complete_zones.contains(&Zone::ExternalPrivate)
        {
            return self.fail("private-zone-roster-forbidden");
        }
        let mut seen = BTreeSet::new();
        for card in observed {
            if matches!(card.zone, Zone::OwnDeck | Zone::ExternalPrivate) {
                return self.fail("private-zone-observation-forbidden");
            }
            if !seen.insert(card.id.clone()) {
                return self.fail("duplicate-visible-instance");
            }
            let code = match self.resolve(&card.code) {
                Ok(c) => c,
                Err(e) => return self.fail(e),
            };
            match self.instances.get(&card.id) {
                Some(old) if old.code == code && old.zone == card.zone => {}
                Some(_) => return self.fail("observed-instance-code-or-zone-mismatch"),
                None => return self.fail("new-visible-instance-origin-unproven"),
            }
        }
        if self
            .instances
            .iter()
            .any(|(id, c)| complete_zones.contains(&c.zone) && !seen.contains(id))
        {
            return self.fail("known-visible-instance-missing");
        }
        if let Some(size) = deck_size {
            if let Some(counts) = self.known_counts() {
                if counts.values().sum::<u64>() != size {
                    return self.fail("deck-size-conservation-mismatch");
                }
            }
        }
        Ok(())
    }

    /// Frozen original row plus a provenance-gated unordered remaining row.
    pub fn context(&self) -> OwnDeckContext {
        let mut out = self.original_context.clone();
        out.features[ROW_DIM..].fill(0.0);
        out.features[ROW_DIM + 1] = 1.0;
        out.features[ROW_DIM + 2] = 1.0;
        if let Some(counts) = self.known_counts() {
            let deck = json!({"deck": counts.iter().map(|(id,count)| json!({"id":id,"count":count})).collect::<Vec<_>>()});
            let remaining =
                OwnDeckContext::from_original(OwnDeckVariant::Original, &deck, &self.cards);
            out.features[ROW_DIM..].copy_from_slice(&remaining.features[..ROW_DIM]);
            out.features[ROW_DIM] = 0.0;
            out.features[ROW_DIM + 1] = 1.0;
        }
        out
    }

    pub fn attach_context(&self, encoded: &mut Encoded) {
        encoded.own_deck = Some(self.context());
    }

    /// Explicit action/future-target seam: clone first, consume only events the
    /// actor can legitimately observe. An uncertain simulated draw yields unknown.
    /// Parent/root state is untouched; restoring a root restores its event ledger.
    pub fn future(&self, events: &[(String, Event)]) -> Self {
        let mut branch = self.clone();
        for (id, event) in events {
            if branch.apply(id, event.clone()).is_err() {
                break;
            }
        }
        branch
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn cards() -> Value {
        json!([
            {"setId":{"set":"TST","number":1},"setCodes":[{"set":"ALT","number":1}],"cost":1,"power":2,"hp":3,"types":["unit"],"arena":"ground","aspects":[],"keywords":[],"traits":["fighter"]},
            {"setId":{"set":"TST","number":2},"setCodes":[],"cost":2,"power":1,"hp":4,"types":["unit"],"arena":"space","aspects":[],"keywords":[],"traits":[]},
            {"setId":{"set":"TST","number":3},"setCodes":[],"cost":3,"types":["event"],"aspects":[],"keywords":[],"traits":[]},
            {"setId":{"set":"TST","number":900},"setCodes":[],"cost":0,"types":["token","upgrade"],"aspects":[],"keywords":[],"traits":[]},
            {"setId":{"set":"TST","number":901},"setCodes":[],"cost":0,"hp":30,"types":["base"],"aspects":[],"keywords":[],"traits":[]}
        ])
    }
    fn ledger() -> RemainingLedger {
        RemainingLedger::from_original(
            "game-a",
            &json!({"deck":[{"id":"TST_001","count":3},{"id":"TST_002","count":2}]}),
            &cards(),
            true,
        )
    }
    fn identity(id: &str, code: &str) -> Identity {
        Identity {
            id: id.into(),
            code: code.into(),
            origin: Origin::Original,
        }
    }
    fn draw(l: &mut RemainingLedger, eid: &str, id: &str, code: &str) {
        l.apply(
            eid,
            Event::Draw {
                cards: vec![identity(id, code)],
            },
        )
        .unwrap();
    }
    fn mv(l: &mut RemainingLedger, eid: &str, id: &str, from: Zone, to: Zone) {
        l.apply(
            eid,
            Event::Move {
                id: id.into(),
                from,
                to,
            },
        )
        .unwrap();
    }
    fn count(l: &RemainingLedger, code: &str) -> u64 {
        l.known_counts().unwrap().get(code).copied().unwrap_or(0)
    }

    #[test]
    fn trusted_initial_deal_mulligan_return_and_shuffle_conserve() {
        let mut l = ledger();
        let original = l.context().features[..ROW_DIM].to_vec();
        draw(&mut l, "initial", "a", "ALT_1");
        assert_eq!(count(&l, "TST_001"), 2);
        mv(&mut l, "mulligan-return", "a", Zone::Hand, Zone::OwnDeck);
        let before = l.context();
        l.apply("shuffle", Event::Shuffle).unwrap();
        assert_eq!(before, l.context());
        assert_eq!(count(&l, "TST_001"), 3);
        draw(&mut l, "redeal", "a", "TST_001");
        assert_eq!(count(&l, "TST_001"), 2);
        assert_eq!(&l.context().features[..ROW_DIM], original.as_slice());
    }

    #[test]
    fn unordered_draw_batches_aliases_and_event_replay_are_identical() {
        let mut a = ledger();
        let mut b = ledger();
        let x = vec![identity("a", "ALT_001"), identity("b", "TST_002")];
        let mut y = x.clone();
        y.reverse();
        y[1].code = "TST_1".into();
        assert!(a.apply("deal", Event::Draw { cards: x }).unwrap());
        assert!(b.apply("deal", Event::Draw { cards: y.clone() }).unwrap());
        assert_eq!(a, b);
        assert!(!a.apply("deal", Event::Draw { cards: y }).unwrap());
        assert_eq!(a, b);
    }

    #[test]
    fn duplicates_overdraws_and_conflicting_ids_fail_closed_atomically() {
        let mut l = ledger();
        let prior = l.instances().clone();
        let cards = vec![identity("a", "TST_001"), identity("a", "TST_002")];
        assert!(l.apply("bad", Event::Draw { cards }).is_err());
        assert_eq!(*l.instances(), prior);
        assert!(l.known_counts().is_none());
        let mut l = ledger();
        let cards = (0..4)
            .map(|n| identity(&format!("id{n}"), "TST_001"))
            .collect();
        assert!(l.apply("overdraw", Event::Draw { cards }).is_err());
        assert!(l.instances().is_empty());
        assert!(l.known_counts().is_none());
        let mut l = ledger();
        draw(&mut l, "e", "a", "TST_001");
        assert!(l.apply("e", Event::Shuffle).is_err());
        assert!(l.known_counts().is_none());
        let mut l = ledger();
        draw(&mut l, "e", "a", "TST_001");
        assert!(l
            .apply(
                "again",
                Event::Draw {
                    cards: vec![identity("a", "TST_002")]
                }
            )
            .is_err());
        assert_eq!(l.instances()["a"].code, "TST_001");
    }

    #[test]
    fn resources_play_attachments_capture_discard_and_returns_subtract_once() {
        let mut l = ledger();
        draw(&mut l, "draw", "a", "TST_001");
        let zones = [
            Zone::Hand,
            Zone::Resource,
            Zone::Ground,
            Zone::Attached,
            Zone::Captured,
            Zone::Discard,
            Zone::Removed,
            Zone::PublicOther,
            Zone::ExternalPrivate,
            Zone::Hand,
        ];
        for (n, pair) in zones.windows(2).enumerate() {
            mv(&mut l, &format!("move{n}"), "a", pair[0], pair[1]);
            assert_eq!(count(&l, "TST_001"), 2);
        }
        mv(&mut l, "return-to-pile", "a", Zone::Hand, Zone::OwnDeck);
        assert_eq!(count(&l, "TST_001"), 3);
        draw(&mut l, "draw-again", "a", "TST_001");
        assert_eq!(count(&l, "TST_001"), 2);
    }

    #[test]
    fn opponent_public_cards_and_generated_cards_never_consume_original_copies() {
        let mut l = ledger();
        l.apply(
            "capture",
            Event::Acquire {
                id: "enemy".into(),
                code: "TST_001".into(),
                to: Zone::Captured,
            },
        )
        .unwrap();
        l.apply(
            "create",
            Event::Create {
                id: "clone".into(),
                code: "TST_001".into(),
                to: Zone::Ground,
            },
        )
        .unwrap();
        assert_eq!(count(&l, "TST_001"), 3);
        mv(&mut l, "exchange", "enemy", Zone::Captured, Zone::Hand);
        mv(
            &mut l,
            "shuffle-external",
            "enemy",
            Zone::Hand,
            Zone::OwnDeck,
        );
        mv(
            &mut l,
            "shuffle-created",
            "clone",
            Zone::Ground,
            Zone::OwnDeck,
        );
        assert_eq!(count(&l, "TST_001"), 5);
        let context = l.context();
        assert_eq!(context.features[4], 5.0 / 60.0);
        assert_eq!(context.features[ROW_DIM + 4], 7.0 / 60.0);
        assert_eq!(context.features[ROW_DIM + 3], 1.0);
        l.apply(
            "draw-clone",
            Event::Draw {
                cards: vec![Identity {
                    id: "clone".into(),
                    code: "ALT_001".into(),
                    origin: Origin::Generated,
                }],
            },
        )
        .unwrap();
        assert_eq!(count(&l, "TST_001"), 4);
        assert_eq!(l.original_counts()["TST_001"], 3);
    }

    #[test]
    fn tokens_and_bases_never_deplete_original_main_bag() {
        let mut l = ledger();
        let before = l.known_counts();
        for (n, code) in ["TST_900", "TST_901"].iter().enumerate() {
            l.apply(
                &format!("create{n}"),
                Event::Create {
                    id: format!("nonmain{n}"),
                    code: (*code).into(),
                    to: Zone::Ground,
                },
            )
            .unwrap();
        }
        assert_eq!(l.known_counts(), before);
        assert!(l
            .apply(
                "illegal-pile",
                Event::Move {
                    id: "nonmain0".into(),
                    from: Zone::Ground,
                    to: Zone::OwnDeck
                }
            )
            .is_err());
        assert!(l.known_counts().is_none());
    }

    #[test]
    fn reveals_do_not_remove_cards_or_record_draw_order() {
        let mut l = ledger();
        let before = l.context();
        l.apply(
            "reveal",
            Event::Reveal {
                cards: vec![identity("revealed", "TST_002")],
            },
        )
        .unwrap();
        assert_eq!(before, l.context());
        assert_eq!(count(&l, "TST_002"), 2);
        l.apply(
            "reveal-again",
            Event::Reveal {
                cards: vec![identity("revealed", "TST_002")],
            },
        )
        .unwrap();
        mv(&mut l, "search-take", "revealed", Zone::OwnDeck, Zone::Hand);
        assert_eq!(count(&l, "TST_002"), 1);
        assert!(l
            .reconcile(&[], &BTreeSet::from([Zone::OwnDeck]), Some(4))
            .is_err());
    }

    #[test]
    fn size_is_only_a_checksum_and_never_fills_missing_identities() {
        let mut l = ledger();
        assert!(l
            .apply("unknown-draw", Event::UnobservedDraw { count: 1 })
            .is_err());
        assert!(l.reconcile(&[], &BTreeSet::new(), Some(4)).is_ok());
        assert!(l.known_counts().is_none());
        assert!(l.instances().is_empty());
        let row = l.context();
        assert_eq!(row.features[ROW_DIM + 3], 0.0);
        assert!(row.features[ROW_DIM + 4..].iter().all(|n| *n == 0.0));
        let mut l = ledger();
        assert!(l.reconcile(&[], &BTreeSet::new(), Some(4)).is_err());
        assert!(l.known_counts().is_none());
    }

    #[test]
    fn incomplete_lists_histories_and_new_visible_origins_stay_unknown() {
        let mut l = RemainingLedger::from_original("g", &json!({}), &cards(), true);
        assert!(l.known_counts().is_none());
        l.reconcile(&[], &BTreeSet::new(), Some(0)).unwrap();
        assert!(l.known_counts().is_none());
        let l = RemainingLedger::from_original("g", &json!({"deck":[]}), &cards(), false);
        assert!(l.known_counts().is_none());
        let mut l = ledger();
        let observed = Observed {
            id: "new".into(),
            code: "TST_001".into(),
            zone: Zone::Hand,
        };
        assert!(l
            .reconcile(&[observed], &BTreeSet::from([Zone::Hand]), Some(4))
            .is_err());
        assert!(l.known_counts().is_none());
        let mut l = ledger();
        assert!(l
            .apply(
                "draw",
                Event::Draw {
                    cards: vec![Identity {
                        id: "x".into(),
                        code: "TST_001".into(),
                        origin: Origin::Unknown
                    }]
                }
            )
            .is_err());
    }

    #[test]
    fn observations_detect_missing_duplicate_changed_or_private_instances() {
        for fault in 0..4 {
            let mut l = ledger();
            draw(&mut l, "draw", "a", "TST_001");
            let good = Observed {
                id: "a".into(),
                code: "ALT_1".into(),
                zone: Zone::Hand,
            };
            let observed = match fault {
                0 => vec![],
                1 => vec![good.clone(), good],
                2 => vec![Observed {
                    code: "TST_002".into(),
                    ..good
                }],
                _ => vec![Observed {
                    zone: Zone::ExternalPrivate,
                    ..good
                }],
            };
            assert!(l
                .reconcile(&observed, &BTreeSet::from([Zone::Hand]), Some(4))
                .is_err());
            assert!(l.known_counts().is_none());
        }
        let mut l = ledger();
        draw(&mut l, "draw", "a", "TST_001");
        l.reconcile(
            &[Observed {
                id: "a".into(),
                code: "ALT_1".into(),
                zone: Zone::Hand,
            }],
            &BTreeSet::from([Zone::Hand]),
            Some(4),
        )
        .unwrap();
        assert_eq!(count(&l, "TST_001"), 2);
    }

    #[test]
    fn independent_branches_restore_reset_and_future_targets() {
        let mut root = ledger();
        let checkpoint = root.checkpoint();
        let fixed = root.context().features[..ROW_DIM].to_vec();
        let a = root.future(&[(
            "a".into(),
            Event::Draw {
                cards: vec![identity("x", "TST_001")],
            },
        )]);
        let b = root.future(&[(
            "b".into(),
            Event::Draw {
                cards: vec![identity("y", "TST_002")],
            },
        )]);
        assert_eq!(count(&root, "TST_001"), 3);
        assert_eq!(count(&a, "TST_001"), 2);
        assert_eq!(count(&b, "TST_001"), 3);
        assert_ne!(
            a.context().features[ROW_DIM..],
            b.context().features[ROW_DIM..]
        );
        assert_eq!(&a.context().features[..ROW_DIM], fixed.as_slice());
        let uncertain = root.future(&[("unknown".into(), Event::UnobservedDraw { count: 1 })]);
        assert!(uncertain.known_counts().is_none());
        assert!(root.known_counts().is_some());
        root = a;
        root.restore(&checkpoint).unwrap();
        assert_eq!(root, checkpoint);
        let other_game =
            RemainingLedger::from_original("game-b", &json!({"deck":[]}), &cards(), true);
        assert!(root.restore(&other_game).is_err());
        assert!(root.known_counts().is_none());
        root = ledger();
        assert_eq!(count(&root, "TST_001"), 3);
        assert!(root.instances().is_empty());
        let empty = RemainingLedger::from_original("empty", &json!({"deck":[]}), &cards(), true);
        assert_eq!(empty.context().features[ROW_DIM + 3], 1.0);
        assert_eq!(empty.context().features[ROW_DIM + 4], 0.0);
    }

    #[test]
    fn malformed_aliases_unknown_generation_and_movement_fail_closed() {
        let mut cs = cards();
        cs.as_array_mut().unwrap().push(json!({"setId":{"set":"TST","number":4},"setCodes":[{"set":"ALT","number":1}],"types":["unit"]}));
        let l = RemainingLedger::from_original(
            "g",
            &json!({"deck":[{"id":"ALT_001","count":1}]}),
            &cs,
            true,
        );
        assert!(l.known_counts().is_none());
        let mut l = ledger();
        assert!(l
            .apply(
                "missing",
                Event::Move {
                    id: "missing".into(),
                    from: Zone::Hand,
                    to: Zone::Resource
                }
            )
            .is_err());
        let mut l = ledger();
        assert!(l
            .apply(
                "untracked",
                Event::Draw {
                    cards: vec![Identity {
                        id: "new".into(),
                        code: "TST_001".into(),
                        origin: Origin::Generated
                    }]
                }
            )
            .is_err());
        let l = RemainingLedger::from_original(
            "g",
            &json!({"deck":[{"id":"TST_001","count":0}]}),
            &cards(),
            true,
        );
        assert!(l.known_counts().is_none());
    }

    #[test]
    fn action_and_future_context_helpers_change_only_opt_in_deck_payload() {
        let root = ledger();
        let message = json!({"you":"p1","state":{"players":{"p1":{},"p2":{}}},"actions":[]});
        let baseline = crate::features::encode(&message, &crate::features::CardTables::default());
        assert!(baseline.own_deck.is_none());
        let branch = root.future(&[(
            "action-draw".into(),
            Event::Draw {
                cards: vec![identity("card", "TST_001")],
            },
        )]);
        let mut target = baseline.clone();
        branch.attach_context(&mut target);
        assert_eq!(target.state, baseline.state);
        assert_eq!(target.tokens, baseline.tokens);
        assert_eq!(target.actions, baseline.actions);
        let context = target.own_deck.unwrap();
        assert_eq!(
            &context.features[..ROW_DIM],
            &root.context().features[..ROW_DIM]
        );
        assert_eq!(context.features[ROW_DIM + 3], 1.0);
        assert_ne!(
            &context.features[ROW_DIM..],
            &root.context().features[ROW_DIM..]
        );
        let uncertain =
            root.future(&[("stochastic-draw".into(), Event::UnobservedDraw { count: 1 })]);
        assert_eq!(uncertain.context().features[ROW_DIM + 3], 0.0);
        assert_eq!(root.context().features[ROW_DIM + 3], 1.0);
    }

    #[test]
    fn conserved_identity_counts_do_not_override_serializer_metadata_unknown() {
        let l = RemainingLedger::from_original(
            "metadata-missing",
            &json!({"deck":[{"id":"TST_001","count":1}]}),
            &json!([]),
            true,
        );
        assert_eq!(count(&l, "TST_001"), 1);
        let context = l.context();
        assert_eq!(context.features[ROW_DIM + 3], 0.0);
        assert_eq!(context.features[ROW_DIM + 4], 1.0 / 60.0);
        assert_eq!(context.features[ROW_DIM + 5], 1.0 / 60.0);
        assert!(context.features[ROW_DIM + 50..].iter().any(|v| *v > 0.0));
    }
}
