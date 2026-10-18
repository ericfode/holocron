"""Primitive journal/command tests only; no engine, model, array or actual data."""
import copy
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('real_ir_supervise_tested', HERE / 'supervise.py')
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)


def toy():
    records = [dict(schema='jepa-real-ir-transfer-apply-journal/1', expectedCases=56,
                    maxApplyCalls=168, planSha256='toy-only')]
    cases = []; n = 0
    for i in range(56):
        context = 'world-' + str(i) + '-TOY'
        play = dict(kind='card', id='own-source')
        choice = dict(kind='card', id='own-target')
        before = dict(offeredActions=[play], marker=[i, 0], settled=True)
        prompt = dict(offeredActions=[choice], marker=[i, 1], settled=False)
        final = dict(offeredActions=[], marker=[i, 2], settled=True)
        steps = []
        for stage, action, b, a in [('play-own-hand', play, before, prompt),
                                   ('chosen-target', choice, prompt, final)]:
            n += 1
            records += [dict(phase='beforeApply', applyCall=n, context=context,
                             branch=stage, before=b, offeredAction=action),
                        dict(phase='afterApply', applyCall=n, context=context,
                             branch=stage, after=a)]
            steps.append(dict(stage=stage, action=action, before=b, after=a))
        case = dict(world_id=i, card='TOY', steps=steps, applyCalls=2,
                    before=before, lastObserved=final, final=final, completion='settled',
                    engineError=None, intentResolution='committed', intentOffered=True)
        cases.append(case)
        records.append(dict(phase='contextComplete', context=context, case=case, applyCalls=n))
    return dict(schema='jepa-real-ir-transfer-native/1', synthetic=False,
                collectionComplete=True, cases=cases, applyCalls=n,
                collectionPlanSha256='toy-only'), records


class NativeProof(unittest.TestCase):
    def test_complete_toy_is_paired(self):
        raw, rows = toy(); proof = S.native_proof(raw, rows)
        self.assertEqual(proof['actual_native_applies'], 112)
        self.assertTrue(proof['exact_step_chains'])

    def test_missing_after_rejected(self):
        raw, rows = toy(); del rows[2]
        with self.assertRaises(ValueError): S.native_proof(raw, rows)

    def test_unoffered_actual_action_rejected(self):
        raw, rows = toy(); rows[1]['before']['offeredActions'] = []
        with self.assertRaises(ValueError): S.native_proof(raw, rows)

    def test_changed_snapshot_chain_rejected(self):
        raw, rows = toy(); rows[3]['before'] = dict(marker='invented', offeredActions=[])
        with self.assertRaises(ValueError): S.native_proof(raw, rows)

    def test_pending_terminal_rejected(self):
        raw, rows = toy(); raw['cases'][0]['final']['settled'] = False
        with self.assertRaises(ValueError): S.native_proof(raw, rows)

    def test_observed_prompt_only_has_no_future(self):
        raw, rows = toy()
        raw = copy.deepcopy(raw); rows = copy.deepcopy(rows)
        # A complete event fixture is expected to settle/cancel. This primitive
        # proves unsupported pending futures cannot be admitted as settled.
        raw['cases'][0]['completion'] = 'pending'
        rows[5]['case'] = raw['cases'][0]
        with self.assertRaises(ValueError): S.native_proof(raw, rows)

    def test_native_error_blocks_success(self):
        raw, rows = toy(); raw['cases'][0]['engineError'] = 'toy-error'
        with self.assertRaises(ValueError): S.native_proof(raw, rows)

    def test_capped_root_counts(self):
        raw, rows = toy(); raw['cases'][0]['applyCalls'] = 4
        with self.assertRaises(ValueError): S.native_proof(raw, rows)

    def test_command_is_new_binary_and_direct_files(self):
        command = S.commands('native', '/new', '/new/metadata-1/plan.json', '/new/native-1')
        self.assertEqual(command, ['/new/build-1/real-ir-transfer-native-collector',
            '/new/metadata-1/plan.json', '/new/native-1/receipt.json', '/new/native-1/transitions.jsonl'])
        build = S.commands('build', '/new', '/new/metadata-1/plan.json', '/new/build-1')
        self.assertIn('--offline', build); self.assertIn('--locked', build)
        self.assertEqual(build[-2:], ['-j', '1'])


if __name__ == '__main__': unittest.main()
