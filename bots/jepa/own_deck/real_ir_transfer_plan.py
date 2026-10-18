"""Pure plan assembly from the closed, prelabel seven-card reservation."""
import copy
import real_ir_adapter as A
import real_ir_reservation_v3 as R

ROLES=('p1_ground','p2_ground','p1_space','p2_space','own_base','opponent_base')
HELPERS=dict(base='ASH_019',leader='IBH_053',resource='LOF_256',ground='HMW_093',space='LOF_119')


def build(catalogue,reservation):
    rows={r['setCode']:r for r in catalogue['cards']}
    R.require(reservation['status']=='metadata-reserved-no-outcomes'and reservation['train_codes']==list(R.TRAIN)
              and reservation['held_codes']==list(R.HELD),'exact prelabel reservation required')
    candidates=reservation['candidates'];R.require([c['code']for c in candidates]==[*R.TRAIN,*R.HELD],'fixed seven-card source order')
    programs=[];worlds=[]
    for i,candidate in enumerate(candidates):
        code=candidate['code'];raw=rows[code];adapted=A.adapt_row(raw)
        R.require(R.digest(raw)==candidate['whole_row_sha256']and adapted['full_card_supported']and
                  adapted['canonical_program']==candidate['canonical_program'],'reserved whole source changed')
        R.require(adapted['canonical_program']['trigger']=='event','this assay admits events only')
        programs.append(dict(index=i,code=code,partition=candidate['partition'],raw_card=copy.deepcopy(raw),
            canonical_program=copy.deepcopy(candidate['canonical_program']),aliases=candidate['aliases'],
            exact_program_key=candidate['exact_program_key'],mechanism_family_key=candidate['mechanism_family_key'],
            full_row_sha256=candidate['whole_row_sha256'],synthetic=False))
        for variant in range(8):
            board={}
            for role in ROLES[:4]:
                owner,arena=role.split('_');helper=rows[HELPERS[arena]];profile=helper['card'];a=A.adapt_row(helper)
                R.require(a['full_card_supported']and a['canonical_program']['form']=='plain-profile'and
                          profile['unique']is False and profile['hp']>=(8 if arena=='ground'else 10),'natural plain helper contract')
                board[role]=dict(code=HELPERS[arena],owner=owner,arena=arena,
                    printed_cost=profile['cost'],hp=profile['hp'],power=profile['power'],
                    damage=0 if variant==6 and role=='p1_ground'else 3 if arena=='ground'else 5,exhausted=False)
            intent=ROLES[variant if variant<6 else 0 if variant==6 else 4]
            worlds.append(dict(id=i*8+variant,source_code=code,program_index=i,root_variant=variant,
                partition=candidate['partition'],intent_ref=intent,requires_target=True,max_applies=3,ready_resources=12,
                arena_cards=board,own_base_damage=0 if variant==7 else 5,opponent_base_damage=5))
    selected=sorted({*HELPERS.values(),'TOKEN_SHIELD',*R.TRAIN,*R.HELD})
    return dict(schema='jepa-real-ir-transfer-plan/1',synthetic=False,source_revision=A.ENGINE_REVISION,
        catalogue_sha256=A.CATALOGUE_SHA,runtime_sha256=A.RUNTIME_SHA,runtime_admitted_snapshot=1178,
        programs=programs,worlds=worlds,candidate_order=list(ROLES),helpers=HELPERS,ready_resources=12,
        selected_whole_cards=selected,selected_whole_rows={code:copy.deepcopy(rows[code])for code in selected},
        collector_max_engine_applies=168,collector_max_seconds=30,expected_apply_count=112,
        expected_count_is_not_observed=True,expected_cases=56,expected_programs=7,
        reservation_digest=R.digest(reservation),fit_source_policy='TRAIN40 roots/5cards/3fulltemplates; HELD16roots/2cards/2templates in one union form.',
        hidden_policy='Empty private piles; own declared source and twelve fixed resources only. Numeric features use public source descriptors and BEFORE candidate fields.',
        known_eligibility_limitation='All six held candidates are eligible: positive recall only, BA/specificity undefined and all-ones control perfect.',
        real_card_claim='Complete original real source/helper definitions, controlled public fixture states with natural printed profiles. Not competitive games or deck coverage.',
        production_changed=False,card_conversion_run=False)
