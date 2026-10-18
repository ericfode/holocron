"""Stdlib synthetic packaging primitives; no actual science or production copies."""
import copy
import gzip
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

import package_evidence as P


class EvidenceTests(unittest.TestCase):
    def test_gzip_preserves_content_and_is_deterministic_mtime_zero(self):
        raw=b'{"public":"fixture"}\n'*30
        one=P.deterministic_gzip(raw);two=P.deterministic_gzip(raw)
        self.assertEqual(one,two);self.assertEqual(one[4:8],b'\0'*4)
        self.assertEqual(gzip.decompress(one),raw)

    def test_traversal_and_runtime_archive_sources_rejected(self):
        for path in('../outside','a/../b','/absolute','a//b','x%20y','x:y','a\\b'):
            with self.assertRaises(ValueError):P.relative(path)
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);repair=root/'repair';native=root/'native';repo=root/'repo';repair.mkdir();native.mkdir();repo.mkdir()
            good=repair/'result.json';good.write_text('{}')
            self.assertEqual(P.allowed_source(good,repair,native,repo),good.resolve())
            for name in('oldportable.zip','native.bin','libkessel.rlib'):
                path=repair/name;path.write_bytes(b'not published')
                with self.assertRaises(ValueError):P.allowed_source(path,repair,native,repo)

    def test_entire_fit_inventory_is_fixed_not_a_selected_subset(self):
        rows=[dict(source='/synthetic/'+name,role='fit')for name in P.FIT_NAMES]
        counts=P.fit_inventory(rows)
        self.assertEqual(counts,dict(prediction_files=36,trained_checkpoint_files=18,initial_checkpoint_files=3,fit_files=62))
        with self.assertRaises(ValueError):P.fit_inventory(rows[:-1])
        with self.assertRaises(ValueError):P.fit_inventory(rows+[rows[0]])

    def test_npz_inventory_reads_zip_metadata_only_and_rejects_paths(self):
        def archive(name):
            stream=io.BytesIO()
            with zipfile.ZipFile(stream,'w')as z:z.writestr(name,b'opaque-NPY-bytes-no-array-load')
            return stream.getvalue()
        self.assertEqual(P.npz_inventory(archive('source.npy'))['members'],['source.npy'])
        with self.assertRaises(ValueError):P.npz_inventory(archive('../source.npy'))
        with self.assertRaises(ValueError):P.npz_inventory(archive('source.pkl'))

    def test_all_fixed_baseline_outputs_are_retained(self):
        rows=[dict(source='/synthetic/'+name,role='baselines')for name in P.BASELINE_NAMES]
        self.assertEqual(P.baseline_inventory(rows),dict(prediction_files=6,baseline_files=8))
        with self.assertRaises(ValueError):P.baseline_inventory(rows[:-1])

    def public_pair(self,root):
        state=dict(players={seat:dict(deck=[],discard=[],hand=[],resources=[],ground=[],space=[])for seat in('p1','p2')})
        state['players']['p1']['hand']=[dict(setCode='LAW_045')]
        state['players']['p1']['resources']=[dict(setCode='LOF_256')]
        cases=[dict(card='LAW_045',before=dict(state=copy.deepcopy(state),projections={}))for _ in range(26)]
        raw=dict(collectionComplete=True,applyCalls=48,cases=cases,collectionPlan=dict(selected_whole_cards=['LAW_045','LOF_256','TOKEN_SHIELD']))
        native=root/'native.json';native.write_text(json.dumps(raw))
        journal=root/'journal.jsonl'
        def save():
            native.write_text(json.dumps(raw));rows=[dict(phase='beforeApply',applyCall=i)for i in range(1,49)]
            rows +=[dict(phase='afterApply',applyCall=i)for i in range(1,49)]
            rows +=[dict(phase='contextComplete',case=c)for c in cases]
            journal.write_text(''.join(json.dumps(v)+'\n'for v in rows))
        save();return raw,native,journal,save

    def test_privacy_observes_empty_hidden_zones_and_own_authored_cards(self):
        with tempfile.TemporaryDirectory()as td:
            raw,native,journal,save=self.public_pair(Path(td))
            result=P.privacy_summary(native,journal)
            self.assertEqual(result['opponent_hand_cards'],0)
            self.assertEqual(result['raw_case_captures'],26)
            self.assertEqual(result['own_focus_source_codes'],['LAW_045'])
            raw['cases'][0]['before']['state']['players']['p2']['hand']=[dict(setCode='LAW_045')];save()
            with self.assertRaisesRegex(ValueError,'opponent private'):P.privacy_summary(native,journal)

    def test_nonempty_draw_pile_or_physical_support_token_is_rejected(self):
        with tempfile.TemporaryDirectory()as td:
            raw,native,journal,save=self.public_pair(Path(td))
            raw['cases'][0]['before']['state']['players']['p1']['deck']=[dict(setCode='LAW_045')];save()
            with self.assertRaisesRegex(ValueError,'draw/discard'):P.privacy_summary(native,journal)
        with tempfile.TemporaryDirectory()as td:
            raw,native,journal,save=self.public_pair(Path(td))
            raw['cases'][0]['before']['state']['players']['p1']['ground']=[dict(setCode='TOKEN_SHIELD')];save()
            with self.assertRaisesRegex(ValueError,'Shield'):P.privacy_summary(native,journal)


if __name__=='__main__':unittest.main()
