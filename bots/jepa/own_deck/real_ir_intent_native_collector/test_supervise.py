"""Artificial journal/route primitives only; never an engine/model/actual plan."""
import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import tempfile
import json
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('real_ir_intent_supervise_tested', HERE / 'supervise.py')
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)


def toy(stage='dev-native'):
    roots, cap, role = S.PANELS[stage]
    rows = [dict(schema='jepa-real-ir-intent-apply-journal/1', expectedCases=roots,
                 maxApplyCalls=cap, planSha256='toy-only')]
    cases, validation = [], []; calls = 0
    for i in range(roots):
        context = 'world-' + str(i) + '-TOY'
        play = dict(card='source'); target = dict(card='helper')
        b = dict(offeredActions=[play], marker=[i, 0], settled=True)
        p = dict(offeredActions=[target], marker=[i, 1], settled=False)
        f = dict(offeredActions=[], marker=[i, 2], settled=True)
        steps = []
        for name, action, before, after in [('play-own-hand', play, b, p), ('chosen-target', target, p, f)]:
            calls += 1
            rows += [dict(phase='beforeApply', applyCall=calls, context=context, branch=name, before=before, offeredAction=action),
                     dict(phase='afterApply', applyCall=calls, context=context, branch=name, after=after)]
            steps.append(dict(stage=name, action=action, before=before, after=after))
        c = dict(world_id=i, card='TOY', before=b, steps=steps, applyCalls=2, engineError=None,
            completion='settled', intentResolution='committed', final=f, lastObserved=f)
        cases.append(c); rows.append(dict(phase='contextComplete', context=context, case=c, applyCalls=calls))
        validation.append(dict(world_id=i, before=b, publicSnapshotRoundtripExact=True,
            legalActionsRoundtripExact=True, allProgramsAdmitted=True, applyCalls=0, actionsApplied=0))
    rows[0]['fixtureValidation'] = validation
    raw = dict(schema='jepa-real-ir-intent-native/1', synthetic=False, collectionComplete=True, panel_role=role,
        cases=cases, applyCalls=calls, collectionPlanSha256='toy-only', fixtureValidation=validation)
    return raw, rows


class Proof(unittest.TestCase):
    def test_both_panel_sizes_and_caps(self):
        for stage, expected in [('dev-native', 112), ('terminal-native', 16)]:
            raw, rows = toy(stage)
            self.assertEqual(S.native_proof(raw, rows)['actual_native_applies'], expected)

    def test_validation_durable_header_required(self):
        raw, rows = toy(); rows[0] = copy.deepcopy(rows[0]); rows[0].pop('fixtureValidation')
        with self.assertRaises(ValueError): S.native_proof(raw, rows)

    def test_bad_initial_validation_rejected(self):
        raw, rows = toy(); raw['fixtureValidation'][0]['applyCalls'] = 1
        with self.assertRaises(ValueError): S.native_proof(raw, rows)

    def test_missing_after_or_unoffered_action_rejected(self):
        raw, rows = toy(); del rows[2]
        with self.assertRaises(ValueError): S.native_proof(raw, rows)
        raw, rows = toy(); rows[1]['before']['offeredActions'] = []
        with self.assertRaises(ValueError): S.native_proof(raw, rows)

    def test_pending_or_error_rejected(self):
        raw, rows = toy(); raw['cases'][0]['final']['settled'] = False
        with self.assertRaises(ValueError): S.native_proof(raw, rows)
        raw, rows = toy(); raw['cases'][0]['engineError'] = 'toy'
        with self.assertRaises(ValueError): S.native_proof(raw, rows)

    def test_unique_binary_and_explicit_plan(self):
        command = S.commands('terminal-native', '/new', '/new/terminal-plan.json', '/new/terminal-native-1')
        self.assertEqual(command, ['/new/build-1/real-ir-intent-native-collector', '/new/terminal-plan.json',
                                  '/new/terminal-native-1/receipt.json', '/new/terminal-native-1/transitions.jsonl'])

    def test_terminal_route_rejected_before_process_helpers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); out = root / 'out'; out.mkdir(); plan = root / 'plan.json'
            plan.write_text(json.dumps(dict(panel_role='terminal', expected_cases=8, collector_max_engine_applies=40)))
            args = SimpleNamespace(stage='terminal-native', out=out, plan=plan, root=root)
            run = SimpleNamespace(state=dict(pending=dict(stage='terminal-native'), completed=[]))
            with self.assertRaisesRegex(ValueError, 'completed fit'): S.worker(args, run, {})

    def test_wrong_panel_cannot_be_launched_as_development(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); out = root / 'out'; out.mkdir(); plan = root / 'plan.json'
            plan.write_text(json.dumps(dict(panel_role='terminal', expected_cases=8, collector_max_engine_applies=40)))
            args = SimpleNamespace(stage='dev-native', out=out, plan=plan, root=root)
            run = SimpleNamespace(state=dict(pending=dict(stage='dev-native'), completed=[]))
            with self.assertRaisesRegex(ValueError, 'route'): S.worker(args, run, {})


if __name__ == '__main__': unittest.main()
