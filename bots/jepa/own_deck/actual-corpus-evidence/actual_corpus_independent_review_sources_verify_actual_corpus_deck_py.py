import collections,hashlib,json,math
from pathlib import Path
import numpy as np
R=Path('/Users/ericfode/Documents/Codex/2026-10-17/task-7/experiments/actual-corpus')
F=R/'deck-fit-1'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canon(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
plan=read(R/'deck-sealed-v1.json');res=read(F/'result.json');rec=read(F/'receipt.json');data=read(plan['dataset']['path'])
assert sha(R/'deck-sealed-v1.json')=='346b7cb0344cdae5a7d3319d09585ba526cf0cf8505c101d39f7d8de17670e77'
assert res['status']==rec['status']=='completed'
assert (res['optimizer_updates'],res['neural_forwards'],res['native_applies'])==(400,408,0)
assert rec['frozen_before']==rec['frozen_after']
assert all(sha(path)==digest for path,digest in rec['frozen_before'].items())
assert sha(Path('/Users/ericfode/Documents/Codex/2026-10-17/task-7/holocron-deck-context/bots/jepa/own_deck/actual_corpus_deck.py'))=='904ff7197c8fcad2700b6bd7eb00f141af689c9a911a25bf57142ef97cb63086'
journal=[json.loads(line)for line in (R/'deck-progress-1.jsonl').read_text().splitlines()]
assert [e['updates_completed']for e in journal]==list(range(1,401))
arms=['correct-typed','untrained-typed','id-only','current-deck']
for k,arm in enumerate(arms):
 entries=journal[k*100:(k+1)*100]
 assert all(e['arm']==arm for e in entries)
 assert [e['arm_step']for e in entries]==list(range(1,101))
 assert [e['neural_forwards']for e in entries]==list(range(k*102+2,k*102+102))
with np.load(F/'shared-initial.npz',allow_pickle=False)as pack:
 initial={k:pack[k].tolist()for k in pack.files}
 assert sum(pack[k].size for k in pack.files)==6829
assert hashlib.sha256(canon(initial).encode()).hexdigest()==res['initial_state_sha256']
held=data['held_idx'];train=data['train_idx'];bank=read(plan['banks']['correct-typed']['path'])
known={c['code']for c in bank['cards']};training={c['code']for c in bank['cards']if c['training_card']}
assert len(data['cards'])==251 and sum(r['total_count']for r in data['rows'])==1432
assert all(v['printed_known']for v in data['cards'].values())
zero=[i for i,row in enumerate(data['rows'])if not set(row['counts'])&known]
assert zero==[3,9,16,18,20,23,24,25]
assert set(held)=={2,3,10,14,25} and len({data['rows'][i]['family_id']for i in held})==4
assert not {data['rows'][i]['family_id']for i in held}&{data['rows'][i]['family_id']for i in train}
assert sum(n for row in data['rows']for c,n in row['counts'].items()if c in known)==65
assert sum(n for row in data['rows']for c,n in row['counts'].items()if c in training)==59

def metrics(pred,idx):
 losses=[sum((pred[j][i]-data['rows'][j]['targets'][i])**2 for j in idx)/len(idx)for i in range(13)]
 families=sorted({data['rows'][j]['family_id']for j in idx})
 family_losses=[]
 for family in families:
  members=[j for j in idx if data['rows'][j]['family_id']==family]
  family_losses.append(sum(sum((pred[j][i]-data['rows'][j]['targets'][i])**2 for i in range(13))/13 for j in members)/len(members))
 return dict(all13_mse=sum(losses)/13,varying_macro_mse=sum(losses)/13,per_head_mse=losses,family_first_varying_macro_mse=sum(family_losses)/len(family_losses))
def same(a,b):
 for key in ['all13_mse','varying_macro_mse','family_first_varying_macro_mse']:assert abs(a[key]-b[key])<1e-14,(key,a[key],b[key])
 assert all(abs(x-y)<1e-14 for x,y in zip(a['per_head_mse'],b['per_head_mse']))
assert all(data['train_varying_mask'])
mean=[sum(data['rows'][j]['targets'][i]for j in train)/len(train)for i in range(13)]
mean_pred=[mean for _ in data['rows']]
same(metrics(mean_pred,held),res['constant_train_mean_baseline']['held'])
summary={};maximum_gap=0
for arm in arms:
 a=res['arms'][arm];p=read(F/(arm+'-predictions.json'));v=read(F/(arm+'-vectors.json'))
 assert a['shared_initial_sha256']==res['initial_state_sha256']
 assert a['updates']==100 and sha(F/(arm+'.npz'))==a['checkpoint']['sha256']
 with np.load(F/(arm+'.npz'),allow_pickle=False)as pack:
  assert sum(pack[k].size for k in pack.files)==6829
  assert all(np.isfinite(pack[k]).all()for k in pack.files)
 assert len(p['predictions'])==len(p['targets'])==len(v['rows'])==27
 assert p['held_indices']==held and p['targets']==[r['targets']for r in data['rows']]
 assert all(len(x)==13 and all(math.isfinite(y)for y in x)for x in p['predictions'])
 assert [x['source_index']for x in v['rows']]==list(range(27))
 for i,row in enumerate(v['rows']):
  src=data['rows'][i]
  assert row['canonical_card_counts']==src['counts'] and row['total_count']==src['total_count']
  assert len(row['vector'])==32 and all(math.isfinite(x)for x in row['vector'])
  assert row['family_id']==src['family_id'] and row['split']==src['split']
  available=sum(n for c,n in src['counts'].items()if c in known)
  layer=row['coverage_layers']['whole_card_vector_available']
  assert layer['copies']==available and layer['unknown_copies']==src['total_count']-available
  assert abs(layer['copy_fraction']-available/src['total_count'])<1e-15
  assert row['coverage_snapshot']==src['coverage']
 same(metrics(p['predictions'],held),a['final_held'])
 same(metrics(p['predictions'],[i for i in held if i in zero]),a['zero_bank_covered_held'])
 for stage in ['initial_invariance','final_invariance']:
  for key,value in a[stage].items():
   assert math.isfinite(value)
   if 'max_abs' in key:
    assert value<=1e-5;maximum_gap=max(maximum_gap,value)
  assert a[stage]['duplicate_split_prediction_max_abs']==a[stage]['duplicate_split_latent_max_abs']==0
 summary[arm]=dict(held=metrics(p['predictions'],held),covered_held=metrics(p['predictions'],[i for i in held if i not in zero]),zero_covered_held=metrics(p['predictions'],[i for i in held if i in zero]),final_copy_perturbed_latent_l2=a['final_invariance']['copy_perturbed_latent_l2'])
ledger=[json.loads(line)for line in (R/'campaign-ledger.jsonl').read_text().splitlines()]
term=[r for r in ledger if r['event']=='stage-finish'];deck=[r for r in term if r['phase']=='deck']
assert len(deck)==1 and deck[0]['status']=='completed' and deck[0]['optimizer_updates']==400 and deck[0]['neural_forwards']==408
assert rec['elapsed_seconds']==deck[0]['elapsed_seconds']<60
assert read(F/'guard.json')['observed_tree_peak_rss_mib']<1024
proof=dict(status='PASS',method='Saved-artifact byte/hash/arithmetic verification only; no NN/native/optimizer execution. Invariance verifies recorded eight82-row forward witnesses and frozen source, not a fresh replay of unretained82-row outputs.',
 source_commit='8fb922bf56869c72f828ee8312a449f3891ed406',sealed_plan_sha256=sha(R/'deck-sealed-v1.json'),result_sha256=sha(F/'result.json'),receipt_sha256=sha(F/'receipt.json'),journal_sha256=sha(R/'deck-progress-1.jsonl'),verifier_sha256=sha(__file__),
 counts=dict(updates=400,training_forwards=400,evaluation_forwards=8,rows_per_eval=82,export_forwards=0,native_applies=0,readout_parameters_per_arm=6829,vectors_per_arm=27,vector_dimension=32),
 frozen_paths_verified=len(rec['frozen_before']),bank_copies=65,unknown_bank_copies=1367,bank_training_copies=59,zero_coverage_indices=zero,zero_coverage_held=[i for i in held if i in zero],max_recorded_invariance_gap=maximum_gap,
 deck_elapsed_seconds=rec['elapsed_seconds'],peak_sampled_tree_rss_mib=read(F/'guard.json')['observed_tree_peak_rss_mib'],constant_train_mean=metrics(mean_pred,held),constant_zero_covered=metrics(mean_pred,[i for i in held if i in zero]),arms=summary)
out=R/'deck-fit-1-independent-verification.json'
with out.open('x')as f:f.write(json.dumps(proof,indent=2,allow_nan=False)+'\n')
print(json.dumps(dict(path=str(out),sha256=sha(out),frozen_paths_verified=proof['frozen_paths_verified'],max_invariance=maximum_gap,summary=summary),indent=2))
