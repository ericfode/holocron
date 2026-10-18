"""Pure data-contract tests: no engines, model forwards or optimizers."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("actual_corpus_coverage", HERE / "actual_corpus_coverage.py")
C = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(C)


def fixtures():
    rows = []
    for i,code in enumerate((*C.PROPOSED_IDS,"ZZZ_001")):
        set_name, number = code.split("_")
        card = dict(setId=dict(set=set_name,number=int(number)),setCodes=[],types=["unit"],cost=2,power=1,hp=3,keywords=[],traits=[],aspects=[])
        rows.append(dict(setCode=code,id=str(100+i),card=card,abilities=dict(card=[],leader=[],unit=[]),sourceHash="a"*64))
    rows[0]["card"]["setCodes"] = [dict(set="RPT",number=1)]
    rows[0]["attachCondition"] = {"kind":"const","value":False}
    catalog = dict(schema="swu-card-ir-cards/v1",cards=rows)
    admission = dict(runtimeAdmittedCards=[dict(setCode=C.PROPOSED_IDS[0],implementation="sourceIr")],gameConformance="not assessed by this report")
    decks = dict(rows=[dict(source_index=0,split="train",family_id="f0",composition_fingerprint="x",leader={"id":"LEA_001"},base={"id":"BAS_001"},
                           total_count=5,canonical_card_counts={C.PROPOSED_IDS[0]:2,"RPT_001":1,"ZZZ_001":2})])
    saved = dict(rows=[])
    split = dict(split=dict(train_idx=[0],val_idx=[]))
    return catalog,admission,decks,saved,split


class CoverageTests(unittest.TestCase):
    def test_alias_merge_and_order_invariance(self):
        catalog,*_ = fixtures()
        aliases,_,_ = C.index_catalog(catalog)
        a = [dict(id="ash_48",count=1),dict(id="RPT_1",count=2)]
        self.assertEqual(C.canonical_counts(a,aliases),{"ASH_048":3})
        self.assertEqual(C.canonical_counts(a[::-1],aliases),C.canonical_counts(a,aliases))

    def test_counts_fail_closed(self):
        catalog,*_ = fixtures();aliases,_,_ = C.index_catalog(catalog)
        for value in (True,-1,1.5,float("nan"),2**53):
            with self.subTest(value=value),self.assertRaises(ValueError):
                C.canonical_counts([dict(id="ASH_048",count=value)],aliases)
        with self.assertRaises(ValueError):
            C.canonical_counts([dict(id="ASH_048",count=2**53-1),dict(id="RPT_001",count=1)],aliases)

    def test_ambiguous_reprint_excluded(self):
        catalog,*_ = fixtures()
        catalog["cards"][1]["card"]["setCodes"] = [dict(set="RPT",number=1)]
        aliases,_,ambiguous = C.index_catalog(catalog)
        self.assertNotIn("RPT_001",aliases)
        self.assertEqual(len(ambiguous["RPT_001"]),2)
        with self.assertRaises(ValueError):
            C.canonical_counts({"RPT_001":1},aliases)

    def test_all_copies_and_source_ids_retained(self):
        result = C.build(*fixtures())
        entries = result["decks"][0]["main_cards"]
        self.assertEqual(sum(row["copies"] for row in entries),5)
        self.assertEqual({row["canonical_id"] for row in entries},{"ASH_048","ZZZ_001"})
        self.assertTrue(all(row["source_id"].isdigit() for row in entries))
        self.assertEqual(result["summary"]["runtime_admitted"]["copies"],3)
        self.assertEqual(result["summary"]["runtime_admitted"]["unknown_copies"],2)
        self.assertEqual(result["summary"]["saved_selected_action_vectors"]["copies"],0)

    def test_admission_never_promoted_to_learned_or_native(self):
        result = C.build(*fixtures())
        known = result["decks"][0]["main_cards"][0]
        self.assertTrue(known["runtime_admitted"])
        self.assertTrue(known["proposed_native_fixture_selected"])
        for key in ("whole_card_typed_model_serialized","native_fixture_verified","learned_whole_card_vector_available","whole_card_trained"):
            self.assertFalse(known[key],key)
        self.assertEqual(result["runtime_game_conformance"],"not assessed by this report")

    def test_full_top_level_row_preserved(self):
        result = C.build(*fixtures())
        row = result["runtime_admitted_card_inventory"][0]
        self.assertEqual(row["whole_catalog_row"]["attachCondition"],{"kind":"const","value":False})
        raw = json.dumps(row["whole_catalog_row"],sort_keys=True,separators=(",",":"),allow_nan=False).encode()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),row["whole_catalog_row_sha256"])
        self.assertFalse(row["vanilla_semantics_verified"])

    def test_numeric_source_id_not_used_for_saved_join(self):
        args = list(fixtures())
        args[3] = dict(rows=[dict(id="RPT_001",canonical_card_id="999999",ability_path=["abilities","card",0])])
        result = C.build(*args)
        self.assertEqual(result["summary"]["saved_selected_action_vectors"]["copies"],3)

    def test_leader_main_and_changed_split_rejected(self):
        args = list(fixtures());args[0]["cards"][0]["card"]["types"] = ["leader"]
        with self.assertRaises(ValueError):C.build(*args)
        args = list(fixtures());args[2]["rows"][0]["split"] = "validation"
        with self.assertRaises(ValueError):C.build(*args)

    def test_nested_typed_nodes_inventory_is_data_only(self):
        value = {"kind":"conditional","effect":{"kind":"sequence","effects":[{"kind":"damage"},{"kind":"damage"}]}}
        self.assertEqual(C.effect_kinds(value),{"conditional":1,"damage":2,"sequence":1})


if __name__ == "__main__":
    unittest.main()
