"""Pure frontend/data/accounting tests; no neural/native/optimizer execution."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import whole_card_encoder as W


class WholeCardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows={r["setCode"]:r for r in W.read(W.CATALOG)["cards"]}
        cls.docs=[W.card_document(cls.rows[c])for c in W.CODES]
        cls.symbols=W.symbols_for(cls.docs)

    def test_all_eight_complete_rows_encode_not_action_only(self):
        self.assertEqual(len({W.digest(doc)for doc in self.docs}),8)
        triggers={a["trigger"]for doc in self.docs for a in doc["abilities"]["card"]}
        self.assertEqual(triggers,{"event","whenPlayed"})
        self.assertTrue(all(len(W.tokens(doc))<=512 for doc in self.docs))

    def test_zero_ability_shielded_sentinel_is_not_vanilla(self):
        shield,vanilla=self.docs[:2]
        self.assertFalse(shield["abilities"]["card"])
        self.assertEqual(shield["keywordValues"],{"sentinel":1,"shielded":1})
        self.assertNotEqual(W.tokens(shield),W.tokens(vanilla))

    def test_root_attachment_and_upgrade_stats_are_not_dropped(self):
        doc=W.card_document(self.rows["LOF_151"])
        self.assertTrue(doc["attachCondition"])
        self.assertEqual((doc["printed"]["upgradePower"],doc["printed"]["upgradeHp"]),(3,2))
        noattach=copy.deepcopy(doc);noattach["attachCondition"]=None
        self.assertNotEqual(W.tokens(doc),W.tokens(noattach))

    def test_identity_and_display_do_not_affect_typed_document(self):
        row=copy.deepcopy(self.rows["JTL_158"]);expected=W.card_document(row)
        row.update(setCode="OTHER_999",sourcePath="elsewhere",sourceHash="changed",id="elsewhere",internalName="elsewhere")
        row["card"].update(title="different",text="different",id="different",internalName="different",setId={"set":"OTHER","number":999})
        row["abilities"]["card"][0]["title"]="arbitrary display"
        self.assertEqual(W.card_document(row),expected)

    def test_unknown_semantics_and_nonempty_piloting_fail_closed(self):
        for where,key,value in(("root","stateWatchers",[{"kind":"new"}]),("root","newSemantic",True),("card","pilotText","Pilot [2]")):
            row=copy.deepcopy(self.rows["JTL_095"]);(row if where=="root"else row["card"])[key]=value
            with self.assertRaises(ValueError):W.card_document(row)

    def test_order_and_genuine_rule_literals_are_preserved(self):
        doc=copy.deepcopy(self.docs[3]);ability=doc["abilities"]["card"][0]
        ability["effect"]={"kind":"sequence","effects":[{"kind":"damage","amount":{"kind":"const","value":1}},{"kind":"exhaust"}]}
        first=W.tokens(doc);ability["effect"]["effects"].reverse()
        self.assertNotEqual(W.tokens(doc),first)
        literal=dict(kind="const",value="GENUINE_123")
        self.assertIn((("value",),"enum","GENUINE_123"),W.tokens(literal))

    def test_train_bank_zeros_every_held_semantic_and_identity_field(self):
        import numpy as np
        bank,scale=W.make_bank(self.docs,self.symbols,True)
        self.assertTrue(all(not a[6:].any()for a in bank.values()))
        self.assertGreaterEqual(scale,1.)
        full,_=W.make_bank(self.docs,self.symbols,False)
        self.assertEqual(len(set(W.bank_signatures(full))),8)
        self.assertTrue(full["token_mask"][6:].any());self.assertFalse(full["identity_indices"][6:].any())
        symbols=copy.deepcopy(self.symbols);symbols["value"].remove("enum:exhaust")
        with self.assertRaises(ValueError):W.make_bank(self.docs,symbols,False)
        self.assertEqual(bank["numeric"].dtype,np.float32)

    def test_partition_and_scalers_ignore_held_labels(self):
        import numpy as np
        arrays=dict(source_cards=np.tile(W.CODES,4),state_families=np.repeat(np.arange(4),8),selected_candidate_indices=np.zeros(32,np.int64),context_features=np.zeros((32,18),np.float32),candidate_features=np.zeros((32,8,34),np.float32),
                    source_targets=np.zeros((32,9),np.float32),source_mask=np.ones((32,9),np.float32),targets=np.zeros((32,8,7),np.float32),target_mask=np.ones((32,8,7),np.float32))
        manifest=dict(context_feature_names=[str(i)for i in range(18)],candidate_feature_names=[str(i)for i in range(34)],source_head_names=["s"+str(i)for i in range(9)],source_binary_heads=[],target_names=["t"+str(i)for i in range(7)],binary_heads=[])
        arrays["source_targets"][0,0]=1
        self.assertEqual({k:len(v)for k,v in W.partition(arrays).items()},dict(train=18,card_held=6,state_held=6,joint=2))
        before=W.scalers(arrays,manifest);changed=copy.deepcopy(arrays)
        held=np.setdiff1d(np.arange(32),W.partition(arrays)["train"])
        changed["source_targets"][held]=999;changed["targets"][held]=999;changed["context_features"][held]=999
        self.assertEqual(before,W.scalers(changed,manifest))
        W.validate_data(arrays,manifest)
        out=W.metrics(np.zeros((32,9)),np.zeros((32,8,7)),arrays,manifest,before)
        self.assertEqual(len(out["joint"]["heads"]),16)
        self.assertEqual(out["joint"]["heads"]["t6"]["native_values"],[0.])
        manifest["source_binary_heads"]=["s0"]
        sc=W.scalers(arrays,manifest)
        binary=W.metrics(np.zeros((32,9)),np.zeros((32,8,7)),arrays,manifest,sc)["train"]["heads"]["s0"]
        self.assertEqual((binary["positive_known_coordinates"],binary["negative_known_coordinates"]),(1,17))
        self.assertEqual((binary["sensitivity"],binary["specificity"],binary["balanced_accuracy"]),(0.,1.,.5))
        baseline=W.constant_baselines(arrays,manifest,sc)
        self.assertAlmostEqual(baseline["train_constant"]["source_values"][0],1/18)

    def test_dataset_presence_does_not_set_native_observed(self):
        import numpy as np
        arrays=dict(source_cards=np.tile(W.CODES,4),state_families=np.repeat(np.arange(4),8),source_targets=np.zeros((32,9)),source_mask=np.zeros((32,9)),target_mask=np.zeros((32,8,7)))
        arrays["source_mask"][:,0]=1
        records=[dict(card=str(code),state_family=int(state),steps=[],playAction=None,before=dict(offeredActions=[]),final=None,completion="play-unavailable",engineError=None)for code,state in zip(arrays["source_cards"],arrays["state_families"])]
        names=["play_available","play_committed","cost_resource",*["unused"+str(i)for i in range(6)]]
        manifest=dict(records=records,source_head_names=names)
        support=W.native_support(arrays,manifest)
        self.assertTrue(all(v["availability_roots"]==4 and not v["native_fixture_observed"]for v in support.values()))
        arrays["source_mask"][0,1:3]=1;arrays["source_targets"][0,1:3]=[1,2]
        with self.assertRaises(ValueError):W.native_support(arrays,manifest)

    def test_shared_ledger_preserves_native_and_rejects_duplicate_card_reservation(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);ledger=root/"campaign.jsonl";plan=root/"plan.json";plan.write_text("{}")
            W.append(ledger,dict(event="stage-start",phase="native",stage_id="n"))
            with self.assertRaises(ValueError):W.reserve(ledger,plan,root/"fit-1")
            W.append(ledger,dict(event="stage-finish",phase="native",stage_id="n",elapsed_seconds=1.))
            W.reserve(ledger,plan,root/"fit-1")
            with self.assertRaises(ValueError):W.reserve(ledger,plan,root/"fit-2")
            records=[json.loads(line)for line in ledger.read_text().splitlines()]
            self.assertEqual(len(records),3);self.assertEqual(records[-1]["reserved_updates"],800)

    def test_pure_import_does_not_load_torch(self):
        code="import sys;sys.path.insert(0,sys.argv[1]);import whole_card_encoder as w;assert 'torch' not in sys.modules;assert w.CONFIG['total_updates']==800"
        subprocess.run([sys.executable,"-B","-c",code,str(Path(W.__file__).parent)],check=True,capture_output=True,text=True)

    def test_fixed_budget(self):
        self.assertEqual((W.CONFIG["total_updates"],W.CONFIG["evaluation_forwards"],W.CONFIG["export_forwards"]),(800,8,0))
        self.assertEqual((W.CONFIG["seconds"],W.CONFIG["threads"],W.CONFIG["rss_bytes"]),(60,1,1073741824))

if __name__=="__main__":unittest.main()
