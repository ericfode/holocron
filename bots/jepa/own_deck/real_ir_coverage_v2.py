"""Complete fixed-snapshot adapter/copy census; no engine or numerical imports."""
from collections import Counter
import json
from pathlib import Path

import real_ir_adapter as A
import real_ir_reservation_v2 as R


def read(path):return json.loads(Path(path).read_text())


def summary(rows):
    keys=('profile_serialized','program_adapter_supported','full_card_supported')
    result={key:sum(r[key] for r in rows) for key in keys}
    result['total']=len(rows)
    result['forms']=dict(sorted(Counter((r['canonical_program']['form']+':'+str(r['canonical_program'].get('trigger')))
        for r in rows if r['full_card_supported']).items()))
    return result


def coverage():
    for path,expected in((R.CATALOGUE,R.CATALOGUE_SHA),(R.RUNTIME,R.RUNTIME_SHA),(R.COVERAGE,R.COVERAGE_SHA)):
        R.require(R.pin(path)['sha256']==expected,'exact pinned1178 snapshot required')
    cat,rt,old=read(R.CATALOGUE),read(R.RUNTIME),read(R.COVERAGE)
    admitted={r['setCode'] for r in rt['runtimeAdmittedCards']}
    R.require(len(cat['cards'])==2458 and len(admitted)==1178,'wrong catalogue/runtime universe')
    rows=[]
    for raw in cat['cards']:
        record=A.adapt_row(raw)
        record['runtime_admitted']=raw['setCode'] in admitted
        rows.append(record)
    by_id={str(r['raw_row']['id']):r for r in rows}
    R.require(len(by_id)==len(rows),'canonical source identity must be unique')
    fields=('profile_serialized','program_adapter_supported','full_card_supported','runtime_full_card_supported',
            'plain_profile_supported','event_program_supported','when_played_program_supported')
    decks=[];totals={key:Counter() for key in fields};all_copies=Counter()
    for deck in old['decks']:
        cards=[]
        for source in deck['main_cards']:
            sid=str(source['source_id']);record=by_id[sid];full=record['full_card_supported'];p=record['canonical_program'] or {}
            flags={key:record[key] for key in fields[:3]}
            flags.update(runtime_full_card_supported=full and record['runtime_admitted'],
                plain_profile_supported=full and record['runtime_admitted'] and p.get('form')=='plain-profile',
                event_program_supported=full and record['runtime_admitted'] and p.get('trigger')=='event',
                when_played_program_supported=full and record['runtime_admitted'] and p.get('trigger')=='whenPlayed')
            copies=source['copies'];all_copies[sid]+=copies
            for key,value in flags.items():
                if value:totals[key][sid]+=copies
            cards.append(dict(canonical_id=source['canonical_id'],source_id=sid,copies=copies,
                              source_code=record['raw_row']['setCode'],**flags))
        total=sum(c['copies'] for c in cards)
        R.require(total==deck['total_main_copies'],'no unsupported copy may disappear')
        decks.append(dict(source_index=deck['source_index'],family_id=deck['family_id'],split=deck['split'],
            total_main_copies=total,main_cards=cards,coverage={key:dict(unique_ids=sum(c[key] for c in cards),
            copies=sum(c['copies'] for c in cards if c[key]),unknown_copies=sum(c['copies'] for c in cards if not c[key])) for key in fields}))
    R.require(len(decks)==27 and len(all_copies)==251 and sum(all_copies.values())==1432,'saved27/251/1432 denominator changed')
    old_rejections=read(R.EXP/'compositional-actual-admission-v1/audit-1/admission-report.json')
    old_by={r['set_code']:r for r in old_rejections['rows']}
    transitions=Counter()
    for r in rows:
        before=old_by[r['raw_row']['setCode']]
        R.require(before['full_row_sha256']==r['whole_row_sha256'],'old/new rows must be identical')
        key=before['error_type']+': '+before['error_message']
        transitions[(key,'full-supported' if r['full_card_supported'] else 'unsupported')]+=1
    reasons=Counter((issue['path'],issue['reason']) for r in rows for issue in r['unsupported_reasons'])
    result=dict(schema='jepa-real-ir-coverage/1',status='metadata-only-no-native-or-learned-claim',
        inputs=dict(catalogue=R.pin(R.CATALOGUE),runtime=R.pin(R.RUNTIME),saved_decks=R.pin(R.COVERAGE),adapter=R.pin(A.__file__)),
        adapter_contract=A.contract(),catalogue=summary(rows),runtime=summary([r for r in rows if r['runtime_admitted']]),
        game_conformance=rt['gameConformance'],rows=rows,decks=decks,
        main_corpus=dict(declarations=27,unique_ids=251,copies=1432,coverage={key:dict(unique_ids=len(c),copies=sum(c.values()),unknown_copies=1432-sum(c.values()),source_ids=sorted(c)) for key,c in totals.items()}),
        old_rejection_transitions=[dict(old_first_rejection=k[0],adapter_status=k[1],cards=n) for k,n in sorted(transitions.items())],
        unsupported_path_counts=[dict(path=k[0],reason=k[1],occurrences=n) for k,n in sorted(reasons.items())],
        native_verified_ids=[],learned_vector_ids=[],native_calls=0,neural_calls=0,semantic_validated=False)
    return result,R.build_reservation()


def verify(report_path,reservation_path):
    """Saved accounting/provenance verification; not a second semantic oracle."""
    report,reserved=read(report_path),read(reservation_path)
    cat,rt,old=read(R.CATALOGUE),read(R.RUNTIME),read(R.COVERAGE)
    R.require(report['inputs']['catalogue']==R.pin(R.CATALOGUE) and report['inputs']['runtime']==R.pin(R.RUNTIME)
              and report['inputs']['saved_decks']==R.pin(R.COVERAGE) and report['inputs']['adapter']==R.pin(A.__file__),'input pin differs')
    admitted={r['setCode'] for r in rt['runtimeAdmittedCards']}
    R.require(len(report['rows'])==len(cat['cards'])==2458,'every catalogue row required')
    for record,raw in zip(report['rows'],cat['cards']):
        R.require(record['raw_row']==raw and record['whole_row_sha256']==R.digest(raw)
                  and record['runtime_admitted']==(raw['setCode'] in admitted),'full row/membership changed')
        R.require(type(record['full_card_supported']) is bool and
                  record['fully_supported']==record['full_card_supported'] and
                  (not record['full_card_supported'] or record['profile_serialized'] and record['program_adapter_supported'] and not record['unsupported_reasons']),
                  'partial or unsupported row counted as full')
    R.require(report['catalogue']==summary(report['rows']) and report['runtime']==summary([r for r in report['rows'] if r['runtime_admitted']]),'all-row counts differ')
    by_id={str(r['raw_row']['id']):r for r in report['rows']};aggregate={k:Counter() for k in report['main_corpus']['coverage']}
    R.require(len(report['decks'])==len(old['decks'])==27,'all saved declarations required')
    for d,original in zip(report['decks'],old['decks']):
        R.require(d['source_index']==original['source_index'] and len(d['main_cards'])==len(original['main_cards']),'deck membership changed')
        for c,o in zip(d['main_cards'],original['main_cards']):
            R.require(c['source_id']==str(o['source_id']) and c['copies']==o['copies'] and c['canonical_id']==o['canonical_id'],'identity/copy dropped')
            r=by_id[c['source_id']];full=r['full_card_supported'];p=r['canonical_program'] or {}
            expected={k:r[k] for k in('profile_serialized','program_adapter_supported','full_card_supported')}
            expected.update(runtime_full_card_supported=full and r['runtime_admitted'],
                plain_profile_supported=full and r['runtime_admitted'] and p.get('form')=='plain-profile',
                event_program_supported=full and r['runtime_admitted'] and p.get('trigger')=='event',
                when_played_program_supported=full and r['runtime_admitted'] and p.get('trigger')=='whenPlayed')
            R.require(all(type(c[k]) is bool and c[k]==v for k,v in expected.items()),'adapter/copy mask differs')
            for k in aggregate:
                if c[k]:aggregate[k][c['source_id']]+=c['copies']
        total=sum(c['copies'] for c in d['main_cards'])
        R.require(total==d['total_main_copies']==original['total_main_copies'],'full main denominator differs')
        for k in aggregate:
            R.require(d['coverage'][k]==dict(unique_ids=sum(c[k] for c in d['main_cards']),copies=sum(c['copies'] for c in d['main_cards'] if c[k]),unknown_copies=sum(c['copies'] for c in d['main_cards'] if not c[k])),'per-deck coverage differs')
    for k,c in aggregate.items():
        R.require(report['main_corpus']['coverage'][k]==dict(unique_ids=len(c),copies=sum(c.values()),unknown_copies=1432-sum(c.values()),source_ids=sorted(c)),'total weighted-copy coverage differs')
    for proof in reserved['input_pins']:R.require(R.pin(proof['path'])==proof,'reservation source changed')
    R.require(reserved['train_codes']==list(R.TRAIN) and reserved['held_codes']==list(R.HELD)
              and not set(reserved['mechanism_groups']['train'])&set(reserved['mechanism_groups']['held']),'holdout partition changed')
    for candidate in reserved['candidates']:
        r=next(r for r in report['rows'] if r['raw_row']['setCode']==candidate['code'])
        R.require(r['full_card_supported'] and r['runtime_admitted'] and r['whole_row_sha256']==candidate['whole_row_sha256'],'reserved source not full supported')
        if candidate['partition']=='held':R.require(not candidate['prior_raw_full_program_overlaps'] and not candidate['prior_adapter_full_program_overlaps'],'held family exposed')
    R.require(report['native_verified_ids']==report['learned_vector_ids']==[] and not report['semantic_validated'],'metadata counted as qualification')
    return dict(schema='jepa-real-ir-coverage-verification/1',verified=True,scope='Every raw row, support-tier accounting, deck copy and frozen reservation pin; adapter semantics separately fixture/peer reviewed and not native-validated here.',
        report=R.pin(report_path),reservation=R.pin(reservation_path),catalogue=report['catalogue'],runtime=report['runtime'],main_corpus=report['main_corpus'],
        native_calls=0,neural_calls=0,semantic_validated=False)
