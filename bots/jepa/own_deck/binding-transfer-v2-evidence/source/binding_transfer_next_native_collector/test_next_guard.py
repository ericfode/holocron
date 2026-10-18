"""Pure synthetic raw/journal/identity checks; no native process or real ledger."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC=importlib.util.spec_from_file_location("next_complete_guard",Path(__file__).with_name("supervise.py"))
G=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(G)


def endpoint():
    return dict(terminal=False,settled=True,offeredActions=[],settlement=dict(decision="Window",ability_program=0,
        death_depth=0,death_pending=0,death_window=0,pending_programs=0,pending_triggers=0,
        after_attack_triggers=0,after_attack_programs=0,event_group_active=False,support_pending=False))


def evidence(root,target=False):
    worlds=[];cases=[];rows=[dict(planSha256="synthetic")];calls=0
    for i in range(26):
        requires=target and i==0
        world=dict(id=i,source_code="SYN_001",cohort="synthetic",partition="train",template_id="synthetic",
            state_family=i,observation_mode="chosen-target"if requires else"passive-aura",
            observation_refs=["anchor_a","anchor_b"],intent_ref="anchor_a"if requires else"source",
            requires_target=requires,max_applies=2 if requires else 1)
        worlds.append(world);source="c"+str(i*2);victim="c"+str(i*2+1)
        play=dict(kind="card",card=source,label="play")
        chosen=dict(kind="card",card=victim,label="target")
        initial=endpoint();initial["offeredActions"]=[play]
        final=endpoint();middle=endpoint();middle["settled"]=False;middle["offeredActions"]=[chosen]
        steps=[dict(stage="play-own-hand",action=play,before=initial,after=middle if requires else final)]
        if requires:steps.append(dict(stage="chosen-target",action=chosen,before=middle,after=final))
        case=dict(world_id=i,card=world["source_code"],cohort=world["cohort"],partition=world["partition"],
            template_id=world["template_id"],state_family=i,observation_mode=world["observation_mode"],
            observation_refs=world["observation_refs"],refs=dict(source=source,anchor_a=victim),
            declared_intent=dict(ref=world["intent_ref"],id=victim if requires else source,requires_target=requires),
            steps=steps,applyCalls=len(steps),completion="settled",engineError=None,before=initial,
            final=final,lastObserved=final,playAction=play,targetAction=chosen if requires else None,
            intendedTargetCommitted=requires)
        context=f"world-{i}-{world['source_code']}"
        for step in steps:
            calls+=1
            rows.extend([dict(phase="beforeApply",applyCall=calls,context=context,branch=step["stage"],before=step["before"],offeredAction=step["action"]),
                         dict(phase="afterApply",applyCall=calls,context=context,branch=step["stage"],after=step["after"])])
        rows.append(dict(phase="contextComplete",context=context,case=case));cases.append(case)
    plan=root/"plan.json";plan.write_text(json.dumps(dict(worlds=worlds))+"\n")
    raw=dict(schema="jepa-binding-transfer-native/1",collectionComplete=True,collectionPlanSha256="synthetic",cases=cases,applyCalls=calls)
    journal=root/"journal.jsonl"
    def save():journal.write_text("".join(json.dumps(v)+"\n"for v in rows))
    save()
    return raw,dict(collection_plan=G.pin(plan)),journal,rows,save


class NextGuardTests(unittest.TestCase):
    def test_exact26_native_chains_and_actual_target_commits(self):
        for target in(False,True):
            with self.subTest(target=target),tempfile.TemporaryDirectory()as td:
                raw,manifest,journal,_,_=evidence(Path(td),target)
                proof=G.verify_complete_cases(raw,manifest,journal)
                self.assertEqual(proof["completed_roots"],26)
                self.assertEqual(proof["actual_applies"],27 if target else 26)
                self.assertTrue(proof["all_required_targets_actually_applied"])

    def test_attempt_bit_without_actual_target_step_is_rejected(self):
        with tempfile.TemporaryDirectory()as td:
            raw,manifest,journal,rows,save=evidence(Path(td),True)
            raw["cases"][0]["targetAction"]=dict(kind="card",card="c999",label="not committed")
            save()
            with self.assertRaisesRegex(ValueError,"not actually committed"):
                G.verify_complete_cases(raw,manifest,journal)

    def test_false_settled_flag_and_per_root_cap_are_rejected(self):
        with tempfile.TemporaryDirectory()as td:
            raw,manifest,journal,rows,save=evidence(Path(td))
            raw["cases"][0]["final"]["settlement"]["pending_triggers"]=1;save()
            with self.assertRaisesRegex(ValueError,"unsettled"):
                G.verify_complete_cases(raw,manifest,journal)
        with tempfile.TemporaryDirectory()as td:
            raw,manifest,journal,rows,save=evidence(Path(td))
            raw["cases"][0]["applyCalls"]=2;save()
            with self.assertRaisesRegex(ValueError,"per-world"):
                G.verify_complete_cases(raw,manifest,journal)

    def test_journal_action_binding_cannot_be_substituted(self):
        with tempfile.TemporaryDirectory()as td:
            raw,manifest,journal,rows,save=evidence(Path(td))
            rows[1]["offeredAction"]=dict(kind="card",card="c999",label="substituted");save()
            with self.assertRaisesRegex(ValueError,"action/state binding"):
                G.verify_complete_cases(raw,manifest,journal)

    def test_world_and_intended_physical_role_are_bound(self):
        with tempfile.TemporaryDirectory()as td:
            raw,manifest,journal,rows,save=evidence(Path(td),True)
            raw["cases"][0]["declared_intent"]["id"]="c999";save()
            with self.assertRaisesRegex(ValueError,"physical role"):
                G.verify_complete_cases(raw,manifest,journal)
        with tempfile.TemporaryDirectory()as td:
            raw,manifest,journal,rows,save=evidence(Path(td))
            raw["cases"][1]["state_family"]=True;save()
            with self.assertRaisesRegex(ValueError,"frozen world binding"):
                G.verify_complete_cases(raw,manifest,journal)

    def test_both_previous_binary_bytes_are_protected(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);pins=[]
            for name in("binding-transfer-native-collector","binding-transfer-fixture-validator"):
                path=root/name;path.write_bytes(name.encode());pins.append(G.pin(path))
            manifest=dict(preserved_binaries=pins)
            self.assertTrue(G.verify_preserved_binaries(manifest)["prior_binaries_unchanged"])
            (root/"binding-transfer-fixture-validator").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError,"prior binary changed"):
                G.verify_preserved_binaries(manifest)

    def test_unique_next_wrapper_keeps_fixed_scientific_source(self):
        self.assertEqual(G.sha(G.CRATE/"src/main.rs"),"6355cde9d6ec5bfb51feab133b3d7fbf352b2edb392bba74187d91c7ff00d61c")
        self.assertEqual(G.sha(G.CRATE/"collection-plan.json"),"0187415c122ba3353938c909f14b800198d65a41a56dcbb1d52197f4fe0bc52f")
        wrapper=(G.CRATE/"src/next_collector.rs").read_text()
        self.assertIn("collector::entry(false)",wrapper)
        self.assertNotIn(".apply(",wrapper)
        source=Path(G.__file__).read_text()
        self.assertIn('debug/binding-transfer-next-native-collector',source)
        self.assertIn('str(CRATE/"Cargo.toml")',source)


if __name__=="__main__":unittest.main()
