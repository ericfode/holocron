"""Primitive/synthetic JSON recovery tests; no actual records or science."""
import ast
import copy
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

import compositional_typed_saved_campaign as C


class SavedCampaignTests(unittest.TestCase):
    def fixture(self):
        plan=dict(source_revision='toy-revision',worlds=[dict(id=i,source_code='TOY'+str(i//4))for i in range(128)],candidate_order=['toy_role'],programs=[{'synthetic':True}],selected_whole_cards=['TOY'])
        pp=dict(path='/synthetic/never-opened/plan.json',sha256='a'*64,bytes=1)
        rows=[dict(schema='jepa-compositional-typed-apply-journal/1',planSha256=pp['sha256'],sourceRevision=plan['source_revision'],maxApplyCalls=512,expectedCases=128)];call=0
        for i,world in enumerate(plan['worlds']):
            steps=[]
            for stage in('play-own-hand','chosen-target'):
                call+=1;before={'toy_before':call};after={'toy_after':call};action={'card':'toy'+str(i)};context='world-'+str(i)
                steps.append(dict(before=before,after=after,action=action,stage=stage))
                rows.extend([dict(phase='beforeApply',applyCall=call,before=before,offeredAction=action,branch=stage,context=context),dict(phase='afterApply',applyCall=call,after=after,branch=stage,context=context)])
            case=dict(world_id=i,card=world['source_code'],engineError=None,completion='settled',intentResolution='committed',terminalClassification='settled-committed',steps=steps,applyCalls=2,final={'settled':True})
            rows.append(dict(phase='contextComplete',case=case))
        source='prefix;let validation=validate_fixtures(&engine,&plan)?;middle;let mut journal=fs::OpenOptions::new().write(true).create_new(true).open(journal_path);suffix;'
        provenance={k:dict(path='/synthetic/'+k,sha256='b'*64,bytes=1)for k in('source_journal','source_plan','failed_ledger','failed_stage_receipt','built_binary','collector_source','source_campaign_spec','truncated_pretty_receipt')}
        return plan,pp,rows,provenance,source

    def test_source_import_is_not_scientific_execution(self):
        tree=ast.parse(Path(C.__file__).read_text());imports=[a.name for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))for a in n.names]
        self.assertFalse(set(imports)&{'numpy','torch'})
        stage=ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='stage'))
        self.assertLess(stage.index('run.begin('),stage.index("actual == descriptor['argv']"))
        self.assertLess(stage.index('run.begin('),stage.index("import_module('effect_identifiability_fit')"))
        self.assertLess(stage.index('with E.Guard('),stage.index('import numpy'))
        self.assertNotIn('subprocess.',stage);self.assertNotIn('subprocess_stage',stage)
        self.assertEqual(C.SECONDS,dict(recover=10.,prep=5.,fit=120.,verify=10.))

    def test_exact_cases_recovered_without_invented_fixture_snapshots(self):
        args=self.fixture();raw,proof=C.reconstruct(*args)
        self.assertEqual(raw['applyCalls'],256);self.assertTrue(raw['collectionComplete']);self.assertEqual(len(raw['cases']),128)
        self.assertIs(raw['cases'][0],args[2][5]['case']);self.assertNotIn('fixtureValidation',raw)
        self.assertEqual(proof['source_charged_native_applies'],512);self.assertEqual(proof['source_observed_native_applies'],256);self.assertEqual(proof['new_native_applies'],0)
        self.assertFalse(proof['per_fixture_validation_records_persisted']);self.assertTrue(proof['no_credit']);self.assertEqual(proof['fixture_validation_scope'],C.SCOPE)
        self.assertIsNone(raw['selectedCatalogueSha256']);self.assertIsNone(raw['elapsedSeconds'])

    def test_missing_root_and_error_phase_rejected(self):
        a=list(self.fixture());a[2]=a[2][:-1]
        with self.assertRaises(ValueError):C.reconstruct(*a)
        a=list(self.fixture());a[2][1]['phase']='applyError'
        with self.assertRaises(ValueError):C.reconstruct(*a)

    def test_action_state_pairing_and_failed_terminal_rejected(self):
        a=list(self.fixture());a[2][1]['offeredAction']={'card':'different'}
        with self.assertRaises(ValueError):C.reconstruct(*a)
        a=list(self.fixture());a[2][5]['case']['engineError']='toy error'
        with self.assertRaises(ValueError):C.reconstruct(*a)
        a=list(self.fixture());a[2][5]['case']['terminalClassification']='pending'
        with self.assertRaises(ValueError):C.reconstruct(*a)

    def test_plan_header_and_source_control_flow_fail_closed(self):
        a=list(self.fixture());a[1]=dict(a[1],sha256='c'*64)
        with self.assertRaises(ValueError):C.reconstruct(*a)
        a=list(self.fixture());a[4]=a[4].replace('let validation=validate_fixtures(&engine,&plan)?;','')
        with self.assertRaises(ValueError):C.reconstruct(*a)
        a=list(self.fixture());a[4]='let mut journal=fs::OpenOptions::new().write(true).create_new(true).open(journal_path);let validation=validate_fixtures(&engine,&plan)?;'
        with self.assertRaises(ValueError):C.reconstruct(*a)

    def test_primitive_copies_and_compact_exclusive_json(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);old=root/'old';new=root/'new';old.write_bytes(b'exact synthetic trace\n')
            p=C.copy_new(old,new);self.assertEqual(new.read_bytes(),old.read_bytes());self.assertEqual(p['bytes'],len(old.read_bytes()))
            with self.assertRaises(FileExistsError):C.copy_new(old,new)
            out=root/'value.json';C.write_new(out,{'ok':[1,True,None]});self.assertEqual(json.loads(out.read_text()),{'ok':[1,True,None]})
            with self.assertRaises(FileExistsError):C.write_new(out,{})
            invalid=root/'invalid.json'
            with self.assertRaises(TypeError):C.write_new(invalid,object())
            self.assertFalse(invalid.exists())

    def test_metadata_prepare_preserves_failed_parent_and_zero_native(self):
        with tempfile.TemporaryDirectory()as temp:
            base=Path(temp).resolve();old=base/'old';new=base/'new';own=base/'own';old.mkdir();own.mkdir();py=base/'python';py.write_text('not executable; never run')
            prior_file=old/'failed-artifact';prior_file.write_text('closed failed bytes');prior_pin=C.S.pin(prior_file)
            financial=dict(saved_batch_ceiling_usd=100,saved_reserve_usd=25,new_recorded_paid_spend_usd=0)
            carry=dict(charged_native_applies=807,charged_seconds=254.2131857079221,observed_native_applies=None)
            (old/'experiment-closure.json').write_text(json.dumps(dict(cumulative=carry)))
            for name in('test_compositional_typed_saved_campaign.py','compositional_typed_saved_verify.py','test_compositional_typed_saved_verify.py','COMPOSITIONAL_TYPED_SAVED_RECOVERY.md'):(own/name).write_text('synthetic source only')
            source=own/'frozen-fit.py';source.write_text('synthetic immutable source');source_pin=C.S.pin(source)
            zero=dict(C.ZERO);state=dict(pending=None,completed=['metadata','build'],failures=1,cumulative=carry,charged=dict(seconds=31.28667466691695,**dict(zero,native_applies=512)),proofs={prior_pin['path']:prior_pin})
            class Budget:
                parent=dict(pins=[],closed_journals=[],protected_roots=[])
                frozen={prior_pin['path']:prior_pin};ledger=old/'campaign-ledger.jsonl'
                spec=dict(stages=dict(metadata=dict(argv=[str(py)])),guard=dict(cpu_workers=1,rss_bytes=1024**3),environment={'synthetic':'true'},financial=financial,pins=[source_pin],caps=dict(seconds=185))
                def __init__(self,path):pass
                def inspect(self):return copy.deepcopy(state)
                def verify(self):pass
            with patch.object(C,'ROOT',new),patch.object(C,'OLD',old),patch.object(C,'HERE',own),patch.object(C.S,'Budget',Budget),patch.object(C.D,'closed_journal',return_value={'synthetic_closed':True}),patch.object(C.subprocess,'check_output',return_value='a'*40+'\n'):
                C.prepare()
            spec=json.loads((new/'campaign-spec.json').read_text());parent=json.loads((new/'parent-manifest.json').read_text())
            self.assertEqual(parent['carry'],carry);self.assertEqual(spec['financial'],financial);self.assertEqual(spec['caps']['seconds'],145.)
            self.assertEqual(spec['stage_order'],['recover','prep','fit','verify']);self.assertEqual(spec['caps']['native_applies'],0);self.assertEqual(spec['caps']['neural_forwards'],3624)
            self.assertEqual(spec['caps']['optimizer_updates'],3600);self.assertEqual(spec['caps']['numerical_fits'],2);self.assertIn(source_pin,spec['pins']);self.assertIn(prior_pin,parent['pins'])
            self.assertEqual(len(spec['stages']['recover']['outputs']),4);self.assertTrue(all(not d['external_counters']and d['reservation']['native_applies']==0 for d in spec['stages'].values()))


if __name__=='__main__':unittest.main()
