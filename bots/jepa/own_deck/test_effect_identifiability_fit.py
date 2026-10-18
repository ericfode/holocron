"""Pure frontend, supervision and identifiability contracts. No neural calls."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import effect_identifiability_fit as E


class EffectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.W=E.prior();cls.rows={r["setCode"]:r for r in cls.W.read(cls.W.CATALOG)["cards"]}

    def test_recursive_display_cleanup_retains_mechanics(self):
        doc,audit=E.canonical_document(self.rows["ASH_171"])
        self.assertFalse("title"in json.dumps(doc));self.assertTrue(audit["display_paths"])
        self.assertEqual(doc["abilities"]["card"][0]["ifYouDo"]["effect"],{"kind":"ready","target":"self"})
        doc,_=E.canonical_document(self.rows["JTL_102"])
        self.assertEqual(doc["abilities"]["card"][0]["effect"],self.rows["JTL_102"]["abilities"]["card"][0]["effect"])

    def test_callback_source_position_renaming_is_invariant(self):
        raw=self.rows["SEC_051"];first,audit=E.canonical_document(raw)
        renamed=json.loads(json.dumps(raw).replace("callback:922:0","callback:31415:0"));second,_=E.canonical_document(renamed)
        self.assertEqual(first,second);self.assertEqual(len(audit["callback_occurrences"]),2)
        self.assertEqual(audit["callback_occurrences"][0]["slot"],audit["callback_occurrences"][1]["slot"])
        self.assertEqual(len(first["abilities"]["card"]),2)
        self.assertEqual(first["abilities"]["card"][0]["effect"]["kind"],"giveExperience")
        self.assertEqual(first["abilities"]["card"][1]["effect"]["power"]["value"]["value"],3)
        self.assertNotIn("callback:922:0",json.dumps(first))

    def test_distinct_binders_and_hook_scopes_remain_distinct(self):
        raw=copy.deepcopy(self.rows["SEC_051"]);hook=raw["abilities"]["card"][0]["hooks"][0]
        hook["predicate"]["right"]["left"]["argumentBinding"]["id"]="callback:922:1"
        _,audit=E.canonical_document(raw);self.assertEqual({r["slot"]for r in audit["callback_occurrences"]},{0,1})
        raw=copy.deepcopy(self.rows["SEC_051"]);raw["abilities"]["card"][0]["hooks"].append(copy.deepcopy(raw["abilities"]["card"][0]["hooks"][0]))
        _,audit=E.canonical_document(raw)
        self.assertEqual([r["slot"]for r in audit["callback_occurrences"]],[0,0,0,0])
        self.assertNotEqual(audit["callback_occurrences"][0]["scope"],audit["callback_occurrences"][2]["scope"])

    def test_unknown_binding_and_structured_literal_reject(self):
        raw=copy.deepcopy(self.rows["SEC_051"]);raw["abilities"]["card"][0]["hooks"][0]["predicate"]["left"]["args"][0]["argumentBinding"]["readAt"]="otherTime"
        with self.assertRaises(ValueError):E.canonical_document(raw)
        raw=copy.deepcopy(self.rows["JTL_144"]);raw["abilities"]["card"][0]["effect"]["amount"]={"kind":"const","value":{"title":"genuine semantic literal"}}
        with self.assertRaises(ValueError):E.canonical_document(raw)

    def test_old_eight_documents_and_semantic_tensors_exact(self):
        import numpy as np
        old=[self.W.card_document(self.rows[c])for c in self.W.CODES]
        new=[E.canonical_document(self.rows[c])[0]for c in self.W.CODES]
        self.assertEqual(old,new);symbols=self.W.symbols_for(old)
        before,scale=self.W.make_bank(old,symbols,False);after,scale2=E.make_bank(new,list(self.W.CODES),list(self.W.TRAIN),symbols,False)
        self.assertEqual(scale,scale2)
        self.assertTrue(all(np.array_equal(v,after[k])for k,v in before.items()))

    def test_dynamic_twelve_storage_without_truncation_or_held_content(self):
        codes=["ASH_048","LOF_151","SEC_142","JTL_144","JTL_217","ASH_171","SEC_051","JTL_102","LAW_131","JTL_079","LAW_127","ASH_228"]
        docs=[E.canonical_document(self.rows[c])[0]for c in codes];bank,_=E.make_bank(docs,codes,codes[:7],E.symbols_for(docs),True)
        self.assertEqual(bank["path_ids"].shape,(12,512,32));self.assertTrue(all(not a[7:].any()for a in bank.values()))

    def test_sparse_only_five_training_masks_change(self):
        import numpy as np
        names=["target_allowed","target_removed",*E.TARGET_EFFECTS]
        a=dict(source_mask=np.ones((4,9),np.float32),target_mask=np.ones((4,8,7),np.float32))
        sparse=E.training_masks(a,[0,2],names,"sparse-typed")
        self.assertTrue(np.array_equal(a["source_mask"],sparse["source_mask"]));self.assertTrue(np.array_equal(a["target_mask"][...,:2],sparse["target_mask"][...,:2]))
        self.assertFalse(sparse["target_mask"][[0,2],:,2:].any());self.assertTrue(sparse["target_mask"][[1,3],:,2:].all())
        self.assertTrue(a["target_mask"].all())

    def test_actual_id_unknown_collision_is_not_hidden_by_true_document(self):
        import numpy as np
        codes=["ASH_048","JTL_095"];docs=[E.canonical_document(self.rows[c])[0]for c in codes]
        a=dict(source_cards=np.asarray(codes),selected_candidate_indices=np.asarray([0,0]),source_targets=np.asarray([[0.],[1.]]),source_mask=np.ones((2,1)),targets=np.zeros((2,8,1)),target_mask=np.zeros((2,8,1)))
        m=dict(source_head_names=["s"],target_names=["t"]);x=np.zeros((2,18));c=np.zeros((2,8,34))
        typed=E.exact_input_conflicts(a,m,docs,codes,x,c,train_codes=[]);ids=E.exact_input_conflicts(a,m,docs,codes,x,c,"id-only",[])
        self.assertEqual(typed["conflict_count"],0);self.assertEqual(ids["conflict_count"],1)
        a["source_mask"][1]=0;self.assertEqual(E.exact_input_conflicts(a,m,docs,codes,x,c,"id-only",[])["conflict_count"],0)

    def test_candidate_hash_does_not_borrow_intent_or_other_panel_rows(self):
        import numpy as np
        codes=["ASH_048"];docs=[E.canonical_document(self.rows[codes[0]])[0]]
        a=dict(source_cards=np.asarray(codes*2),selected_candidate_indices=np.asarray([0,1]),source_targets=np.zeros((2,1)),source_mask=np.zeros((2,1)),targets=np.zeros((2,8,1)),target_mask=np.zeros((2,8,1)))
        a["targets"][1,3,0]=1;a["target_mask"][:,3]=1
        x=np.zeros((2,18));c=np.zeros((2,8,34));c[1,0,0]=1
        audit=E.exact_input_conflicts(a,dict(source_head_names=["s"],target_names=["t"]),docs,codes,x,c,train_codes=codes)
        self.assertEqual(audit["conflict_count"],1)

    def test_import_and_frontend_are_neural_free(self):
        code="import sys;sys.path.insert(0,sys.argv[1]);import effect_identifiability_fit as e;e.prior();e.frontend_fingerprint();assert 'torch' not in sys.modules"
        subprocess.run([sys.executable,"-B","-c",code,str(Path(E.__file__).parent)],check=True,capture_output=True,text=True)

    def test_guard_live_rss_and_cleanup_without_numerical_import(self):
        import signal
        from unittest.mock import patch
        before=signal.getsignal(signal.SIGALRM)
        with E.Guard(1)as guard:self.assertGreater(guard.rss(),0)
        self.assertEqual(signal.getsignal(signal.SIGALRM),before);self.assertEqual(signal.getitimer(signal.ITIMER_REAL),(0.,0.))
        with patch.object(E.Guard,"rss",side_effect=RuntimeError("rss failed")):
            with self.assertRaises(RuntimeError):
                with E.Guard(1):pass
        self.assertEqual(signal.getsignal(signal.SIGALRM),before);self.assertEqual(signal.getitimer(signal.ITIMER_REAL),(0.,0.))
        with patch.object(E.Guard,"rss",return_value=2**31):
            with self.assertRaises(RuntimeError):
                with E.Guard(1):pass
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL),(0.,0.))
        for seconds in(0,-1,float("nan"),float("inf")):
            with self.assertRaises(ValueError):E.Guard(seconds)

    def test_common_transforms_and_fixed_weights_use_train_only(self):
        import numpy as np
        a=dict(context_features=np.arange(4*18,dtype=np.float32).reshape(4,18),candidate_features=np.zeros((4,8,34),np.float32),source_targets=np.asarray([[0.],[1.],[99.],[99.]],np.float32),source_mask=np.ones((4,1),np.float32),targets=np.zeros((4,8,1),np.float32),target_mask=np.zeros((4,8,1),np.float32))
        a["targets"][:2,0,0]=[-2,2];a["target_mask"][:2,0,0]=1
        m=dict(source_head_names=["source"],source_binary_heads=["source"],target_names=["delta"],binary_heads=[])
        sc=E.common_scalers(a,m,[0,1]);b=copy.deepcopy(a);b["source_targets"][2:]=0;b["context_features"][2:]=999
        self.assertEqual(sc,E.common_scalers(b,m,[0,1]));self.assertEqual(sc["targets"][0]["class_weights"],{"-1":1.,"0":0.,"1":1.});self.assertEqual(sc["targets"][0]["loss_coefficient"],.5)

    def test_zero_control_participates_in_both_behavior_gates(self):
        def result(error):return dict(cells=dict(family_held=dict(behavior=dict(family_first_mae=error,known_families=3,known_program_groups=5))),contrasts=dict(family_first_mae=error,family_first_direction_accuracy=1.,known_pairs=10,known_families=3))
        evaluations={a:result(1. if a=="rich-typed"else 2.)for a in E.ARMS}
        baselines=dict(train_constant=result(2.),zero_heads=result(.5));gate=E.behavioral_gate(evaluations,baselines)
        self.assertFalse(gate["passed"]);self.assertEqual(gate["strongest_control_error"],.5);self.assertEqual(gate["strongest_control_contrast_error"],.5)
        baselines["zero_heads"]=result(2.);self.assertTrue(E.behavioral_gate(evaluations,baselines)["passed"])

    def test_unsupported_identity_does_not_count_as_known_program_group(self):
        import numpy as np
        names=["target_allowed","target_removed",*E.TARGET_EFFECTS];a=dict(source_cards=np.asarray(["a","b"]),targets=np.zeros((2,8,7),np.float32),target_mask=np.zeros((2,8,7),np.float32));a["target_mask"][0,0,5:7]=1
        m=dict(target_names=names,cards={c:dict(family="pointed-unit-event-stat-debuff",normalized_program_group=c)for c in("a","b")});sc=dict(targets=[dict(scale=1.)for _ in names]);support=dict(mechanics={k:dict(eligible=True)for k in E.MECHANICS})
        r=E.family_metrics(np.zeros_like(a["targets"]),a,m,sc,support,[0,1]);self.assertEqual(r["known_program_groups"],1);self.assertEqual(r["families"]["pointed-unit-event-stat-debuff"]["declared_program_groups"],["a","b"])

    def test_durable_forward_and_update_journal_rejects_reorder(self):
        import tempfile
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/"progress.jsonl";E.append_journal(p,dict(event="forward-intent",global_forward=1,kind="train"));E.append_journal(p,dict(event="optimizer-update",global_update=1))
            self.assertEqual(E.journal_counts(p)["optimizer_updates"],1)
            E.append_journal(p,dict(event="optimizer-update",global_update=1))
            with self.assertRaises(ValueError):E.journal_counts(p)

    def test_all_mechanics_require_two_zero_and_nonzero_training_support(self):
        import numpy as np
        names=["target_allowed","target_removed",*E.TARGET_EFFECTS];specs=[dict(name=n,known=4,zero=2,nonzero=2)for n in names]
        a=dict(source_cards=np.asarray(["a"]*4),state_families=np.asarray([0,1,2,3]));split=dict(train_codes=["a"],train_state_families=[0,1,2]);m=dict(target_names=names)
        r=E.behavioral_support(a,m,dict(targets=specs),split);self.assertEqual(set(r["eligible_mechanics"]),set(E.MECHANICS))
        specs[names.index("target_exhausted_delta")]["nonzero"]=1
        r=E.behavioral_support(a,m,dict(targets=specs),split);self.assertFalse(r["mechanics"]["exhaustion"]["eligible"])

if __name__=="__main__":unittest.main()
