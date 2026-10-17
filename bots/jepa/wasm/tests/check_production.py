"""Check final production WASM choices/transcripts and strict-v2 rejection, without engine games."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from check_runtime import JsonProcess, check_vectors, decide_with_transcript, require


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wasm', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    reference = json.loads((Path(__file__).parent / 'fixtures/runtime-reference.json').read_text())
    artifact = args.wasm.resolve()
    def command(config):
        return ['wasmtime', 'run', '--env', 'JEPA_CONFIG=' + json.dumps(config, separators=(',', ':')), str(artifact)]
    with JsonProcess(command(reference['settings']), reference['settings'], 20) as session:
        vectors = check_vectors(session, reference)
    behavior = []
    for case in reference['behaviors']:
        config = case['settings']
        with JsonProcess(command(config), config, 20) as session:
            require(session.exchange(case['hello']) == case['ready'], 'production hello differs')
            reply, consumed = decide_with_transcript(session, case['msg'], case['transcript'], 0, case['name'])
            require(reply == case['reply'], case['name'] + ': production action differs')
            if case.get('followup'):
                follow = case['followup']
                reply, consumed = decide_with_transcript(session, follow['msg'], case['transcript'], consumed, case['name'])
                require(reply == follow['reply'], case['name'] + ': production follow-up differs')
            require(consumed == len(case['transcript']), 'production simulation transcript differs')
            require(session.exchange({'t': 'over'}) == {'t': 'ok'}, 'production over differs')
            behavior.append({'name': case['name'], 'simulatorMessages': consumed, 'passed': True})
    rejected = []
    for name, message, config in [
        ('v1-only', {'t': 'hello', 'versions': [1]}, {}),
        ('string-version', {'t': 'hello', 'versions': ['2']}, {}),
        ('boolean-version', {'t': 'hello', 'versions': [True]}, {}),
        ('imagined-legacy-fallback', {'t': 'hello', 'versions': [2]}, {'score': 'imagined'}),
        ('diagnostics-disabled', {'t': 'stats'}, {}),
    ]:
        result = subprocess.run(command(config), input=json.dumps(message)+'\n', text=True,
                                capture_output=True, timeout=20)
        require(result.returncode != 0 and not result.stdout, name + ': production should reject before replying')
        rejected.append(name)
    report = {'passed': True, 'artifactSha256': hashlib.sha256(artifact.read_bytes()).hexdigest(),
              'artifactBytes': artifact.stat().st_size, 'runnerVersion': subprocess.check_output(['wasmtime', '--version'], text=True).strip(),
              'vectors': vectors, 'behaviors': behavior, 'rejected': rejected,
              'scope': 'Final production module, synthetic JS transcript parity and strict-v2 boundary; no tensor diagnostics, engine games or admission'}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
