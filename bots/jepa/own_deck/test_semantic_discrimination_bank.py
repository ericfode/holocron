"""Synthetic banks only: no actual cohort, data labels, model, or forward."""
import copy
import unittest
import numpy as np
import semantic_discrimination_bank as B


def documents():
    return [dict(role='main', printed=dict(cost=i + 1, power=None, hp=None, unique=False,
        upgradePower=None, upgradeHp=None, aspects=['vigilance'], traits=['tactic'],
        arena=None, keywords=[], types=['event']), keywordValues={}, attachCondition=None,
        abilities=dict(leader=[], unit=[], card=[dict(trigger='event', costs=[],
            effect=dict(kind='damage', target='chosen', amount=dict(kind='const', value=n)))]))
        for i, n in enumerate((1, 3, 1000, 2000))]


class BankTests(unittest.TestCase):
    def setUp(self):
        self.docs = documents(); self.codes = ['TST_001', 'TST_002', 'TST_003', 'TST_004']
        self.train = self.codes[:2]; self.E = B.frontend(); self.symbols = self.E.symbols_for(self.docs)
        self.donors = B.fixed_donors(self.codes, self.train)

    def banks(self, training=False):
        return B.make_banks(self.docs, self.codes, self.train, self.symbols, self.donors, training)

    def equal(self, first, second):
        self.assertEqual(set(first), set(second))
        for key in first:
            np.testing.assert_array_equal(first[key], second[key], err_msg=key)
            self.assertEqual(first[key].dtype, second[key].dtype)

    def test_full_bitidentical_to_frozen_reference(self):
        expected, scale = self.E.make_bank(self.docs, self.codes, self.train, self.symbols)
        actual = B.make_banks(self.docs, self.codes, self.train, self.symbols, self.donors,
                              numeric_scale=scale)
        self.equal(actual['full'], expected)
        self.equal(B._encode(self.docs, self.codes, self.train, self.symbols, scale, False), expected)

    def test_printed_keeps_original_positions_and_full_printed_values(self):
        banks = self.banks(); W = self.E.prior()
        for slot, doc in enumerate(self.docs):
            for pos, (path, _, _) in enumerate(W.tokens(doc)):
                keep = not path or path[0] == 'printed'
                for key in B.TOKEN_ARRAYS:
                    expected = banks['full'][key][slot, pos] if keep else np.zeros_like(banks['printed'][key][slot, pos])
                    np.testing.assert_array_equal(banks['printed'][key][slot, pos], expected)
        self.equal(banks['printed'], banks['swapped_printed'])
        self.assertIsNot(banks['printed']['numeric'], banks['swapped_printed']['numeric'])

    def test_ability_only_partition_local_swap(self):
        changed = B.swapped_documents(self.docs, self.codes, self.train, self.donors)
        for code, old, new in zip(self.codes, self.docs, changed):
            for key in old:
                self.assertEqual(new[key], self.docs[self.codes.index(self.donors[code])]['abilities']
                                 if key == 'abilities' else old[key])
            self.assertEqual(code in self.train, self.donors[code] in self.train)
        self.assertEqual(self.donors, dict(zip(self.codes, ['TST_002', 'TST_001', 'TST_004', 'TST_003'])))

    def test_swap_uses_original_train_scale_not_donor_refit(self):
        full, scale = self.E.make_bank(self.docs, self.codes, self.train, self.symbols)
        banks = self.banks(); swapped = B.swapped_documents(self.docs, self.codes, self.train, self.donors)
        for slot, doc in enumerate(swapped):
            for pos, (_, kind, value) in enumerate(self.E.prior().tokens(doc)):
                if kind in ('number', 'length'):
                    np.testing.assert_array_equal(banks['swapped_full']['numeric'][slot, pos],
                        np.asarray((value / scale, np.sign(value) * np.log1p(abs(value))), np.float32))
        modified = copy.deepcopy(self.docs); modified[2]['printed']['cost'] = 60000
        changed_symbols = self.E.symbols_for(modified)
        altered, changed_scale = self.E.make_bank(modified, self.codes, self.train, changed_symbols)
        self.assertEqual(scale, changed_scale)
        self.equal({k: v[:2] for k, v in full.items()}, {k: v[:2] for k, v in altered.items()})
        with self.assertRaisesRegex(ValueError, 'scale changed'):
            B.make_banks(self.docs, self.codes, self.train, self.symbols, self.donors, numeric_scale=scale + 1)

    def test_training_zeroes_entire_held_slots_every_bank(self):
        for bank in self.banks(training=True).values():
            for array in bank.values():
                self.assertEqual(np.count_nonzero(array[2:]), 0)
            np.testing.assert_array_equal(bank['identity_indices'][:2], [1, 2])

    def test_donor_admission_rejects_cross_partition_or_ineffective(self):
        wrong = dict(self.donors); wrong['TST_001'] = 'TST_003'
        with self.assertRaisesRegex(ValueError, 'donor cycles'):
            B.swapped_documents(self.docs, self.codes, self.train, wrong)
        same = copy.deepcopy(self.docs); same[1]['abilities'] = copy.deepcopy(same[0]['abilities'])
        with self.assertRaisesRegex(ValueError, 'change the ability'):
            B.swapped_documents(same, self.codes, self.train, self.donors)

    def test_object_order_invariance_and_ability_difference(self):
        def reversed_keys(value):
            if isinstance(value, dict):
                return {k: reversed_keys(v) for k, v in reversed(list(value.items()))}
            return [reversed_keys(v) for v in value] if isinstance(value, list) else value
        first = self.banks()
        second = B.make_banks(reversed_keys(self.docs), self.codes, self.train, self.symbols, self.donors)
        for name in B.BANK_NAMES:
            self.equal(first[name], second[name])
        self.assertNotEqual(self.E.tensor_signatures(first['full']), self.E.tensor_signatures(first['swapped_full']))

    def test_effect_sequence_order_is_preserved(self):
        docs = copy.deepcopy(self.docs)
        effects = [dict(kind='damage', target='chosen', amount=dict(kind='const', value=1)),
                   dict(kind='heal', target='chosen', amount=dict(kind='const', value=2))]
        docs[0]['abilities']['card'][0]['effect'] = dict(kind='sequence', effects=effects)
        docs[1]['abilities']['card'][0]['effect'] = dict(kind='sequence', effects=list(reversed(effects)))
        symbols = self.E.symbols_for(docs)
        bank = B.make_banks(docs, self.codes, self.train, symbols, self.donors)['full']
        self.assertFalse(np.array_equal(bank['value_ids'][0], bank['value_ids'][1]))

    def test_synthetic_metadata_and_representation_contract(self):
        cards = []
        for code, doc in zip(self.codes, self.docs):
            cards.append(dict(code=code, raw_card=dict(card=doc['printed'], abilities=doc['abilities'], keywordValues={})))
        cards[2]['raw_card']['abilities']['card'][0]['effect']['kind'] = 'heal'
        meta = B.metadata(dict(cards=cards, split=dict(train_codes=self.train)))
        self.assertEqual(meta['schema'], B.SCHEMA)
        self.assertFalse(meta['semantic_validated'])
        self.assertEqual(meta['donors'], self.donors)
        self.assertIn('enum:heal', meta['public_held_only_atoms']['value'])
        self.assertEqual(meta['public_held_only_atom_counts']['value'], len(meta['public_held_only_atoms']['value']))
        self.assertIn('decay', meta['held_vocabulary_scope'])
        for name, bank in B.banks_from_metadata(meta).items():
            self.assertEqual(meta['semantic_signatures'][name], self.E.tensor_signatures(bank))
        self.assertEqual(B.representation_signatures(meta, 'ID-only'), ['ID:1', 'ID:2', 'ID:0', 'ID:0'])
        self.assertEqual(B.representation_signatures(meta, 'public-only', True), ['PUBLIC-ZERO'] * 4)
        self.assertEqual(B.representation_signatures(meta, 'printed-only'), B.representation_signatures(meta, 'printed-only', True))
        self.assertEqual(B.representation_signatures(meta, 'frozen-full'), B.representation_signatures(meta, 'learned-full'))
        self.assertNotEqual(B.representation_signatures(meta, 'learned-full'), B.representation_signatures(meta, 'learned-full', True))
        enriched = copy.deepcopy(meta)
        enriched.update(fit_schema='jepa-semantic-discrimination-fit/1', config=dict(synthetic=True))
        for name, bank in B.banks_from_metadata(enriched).items():
            self.equal(bank, B.banks_from_metadata(meta)[name])


if __name__ == '__main__':
    unittest.main()
