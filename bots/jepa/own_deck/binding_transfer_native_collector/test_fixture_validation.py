"""Portable source/contract tests only; no build, native subprocess, or Engine.apply."""
import hashlib
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent


def function(source, name, following):
    return source.split("fn " + name + "(", 1)[1].split("fn " + following + "(", 1)[0]


class FixtureValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (HERE / "src/main.rs").read_text()
        cls.plan_raw = (HERE / "collection-plan.json").read_bytes()
        cls.plan = json.loads(cls.plan_raw)

    def test_same_frozen_twenty_six_worlds_and_quantities(self):
        self.assertEqual(hashlib.sha256(self.plan_raw).hexdigest(), "0187415c122ba3353938c909f14b800198d65a41a56dcbb1d52197f4fe0bc52f")
        self.assertEqual([w["id"] for w in self.plan["worlds"]], list(range(26)))
        self.assertEqual(self.plan["helpers"]["victim_upgrades"], ["ASH_066", "LOF_215"])
        self.assertEqual(sum(w["max_applies"] for w in self.plan["worlds"]), 48)
        self.assertEqual(self.plan["selected_whole_rows"]["TOKEN_SHIELD"]["status"], "unsupported")

    def test_fixed_constructor_appends_and_registers_exactly_once(self):
        body = function(self.source, "attach_fixture", "fixture")
        self.assertIn("while current!=0", body)
        self.assertIn("seen.contains(&current)", body)
        self.assertIn("s.card_mut(tail).next_upgrade=id", body)
        self.assertIn("s.card_mut(id).next_upgrade=0", body)
        self.assertEqual(body.count("s.registration_order.push(id)?"), 1)
        self.assertNotIn("next_upgrade=old", body)
        self.assertLess(body.index("let card=s.card(current)"), body.index("let id=add(e,s,owner,code)"))

    def test_unique_validator_binary_requires_explicit_validation(self):
        wrapper = (HERE / "src/fixture_validator.rs").read_text()
        self.assertIn("collector::entry(true)", wrapper)
        self.assertNotIn("entry(false)", wrapper)
        self.assertIn('name = "binding-transfer-fixture-validator"', (HERE / "Cargo.toml").read_text())
        entry = self.source.split("pub(crate) fn entry(", 1)[1].split("#[cfg(test)]", 1)[0]
        self.assertIn('args.len()==3&&args[1]=="--validate-fixtures-only"', entry)
        self.assertIn("require_validation&&!validate_only", entry)

    def test_validation_branch_returns_before_trace_budget_and_run_case(self):
        run = self.source.split("fn run(validate_only:bool)", 1)[1].split("pub(crate) fn entry(", 1)[0]
        branch = run.split("if validate_only{", 1)[1].split('env::var("BINDING_TRANSFER_NATIVE_TRACE")', 1)[0]
        self.assertIn("return Ok(json!", branch)
        self.assertLess(run.index("if validate_only{"), run.index("let mut budget=Budget"))
        self.assertNotIn("run_case(", branch)
        self.assertNotIn(".apply(", branch)
        for key in ('"applyCalls":0', '"engineApplyInvocations":0', '"actionsApplied":0',
                    '"nativeJournalCreated":false', '"neuralForwards":0', '"optimizerUpdates":0'):
            self.assertIn(key, branch)
        self.assertEqual(self.source.count("let result=e.apply(s,a)"), 1)

    def test_every_root_is_roundtripped_and_public_attachment_membership_queried(self):
        validate = function(self.source, "validate_fixtures", "offered")
        for fragment in ("worlds.len()!=26", "ids.contains(&id)", "fixture(e,world,plan)?",
                         "e.load_state(&snapshot)?", "snapshot!=e.snapshot(&imported)",
                         "e.legal_actions(&s)!=e.legal_actions(&imported)",
                         "fixture_chronology(&s,host)?", "offered(e,&query,host).is_none()"):
            self.assertIn(fragment, validate)
        self.assertNotIn("Budget", validate)
        self.assertNotIn("run_case", validate)
        self.assertNotIn(".apply(", validate)
        self.assertIn('deck.len!=0', validate)
        self.assertIn('seat==Seat::P2&&s.player(seat).hand.len!=0', validate)
        self.assertIn('code=="TOKEN_SHIELD"', validate)

    def test_regression_witnesses_include_original_reversal_and_cyclic_chain(self):
        tests = self.source.split("#[cfg(test)]", 1)[1]
        self.assertIn("state_with_two_upgrades(true)", tests)
        self.assertIn("cyclic.card_mut(3).next_upgrade=2", tests)
        self.assertIn("wrong_parent.card_mut(3).parent=2", tests)
        self.assertNotIn(".apply(", tests)


if __name__ == "__main__":
    unittest.main()
