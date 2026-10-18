"""Versioned program-bank interventions; import is stdlib-only.

Actual cohort construction belongs inside the root-controlled metadata guard.
No model, data labels, engine, optimizer, or forward is used by this module.
"""
import copy
import hashlib
import importlib
import math
from pathlib import Path

SCHEMA = 'jepa-semantic-discrimination-bank/1'
EFFECT_SHA = '90ef1c0c6e2a2626f0d54c1f031fea77a25ea80b9e6e351882cb7ddd38cbd765'
BANK_NAMES = ('full', 'printed', 'swapped_full', 'swapped_printed')
TOKEN_ARRAYS = ('path_ids', 'path_lengths', 'type_ids', 'value_ids', 'numeric', 'token_mask')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def frontend():
    E = importlib.import_module('effect_identifiability_fit')
    require(hashlib.sha256(Path(E.__file__).read_bytes()).hexdigest() == EFFECT_SHA,
            'frozen effect frontend changed')
    return E


def fixed_donors(codes, train_codes):
    """One prelabel cycle per partition; no labels or outcomes are inspected."""
    codes, train_codes = list(codes), list(train_codes)
    require(len(codes) == len(set(codes)) and len(train_codes) == len(set(train_codes))
            and set(train_codes) <= set(codes), 'unique codes and TRAIN subset required')
    donors = {}
    for group in (train_codes, [c for c in codes if c not in train_codes]):
        require(len(group) >= 2, 'both donor partitions require at least two cards')
        donors.update({code: group[(i + 1) % len(group)] for i, code in enumerate(group)})
    return donors


def swapped_documents(documents, codes, train_codes, donors):
    """Swap abilities only; printed values, role, keywords and attachment stay."""
    require(donors == fixed_donors(codes, train_codes), 'exact partition-local prelabel donor cycles required')
    require(len(documents) == len(codes), 'complete ordered document bank required')
    lookup = dict(zip(codes, documents)); output = []
    for code, document in zip(codes, documents):
        require('abilities' in document and 'printed' in document, 'whole-card document required')
        changed = copy.deepcopy(document)
        changed['abilities'] = copy.deepcopy(lookup[donors[code]]['abilities'])
        require(changed['abilities'] != document['abilities'], 'donor must change the ability program')
        output.append(changed)
    return output


def _encode(documents, codes, train_codes, symbols, scale, training):
    """Frozen E.make_bank layout/arithmetic, using the original FULL scale."""
    import numpy as np
    W = frontend().prior(); n = len(codes)
    lookup = {key: {v: i for i, v in enumerate(values)} for key, values in symbols.items()}
    bank = dict(path_ids=np.zeros((n, 512, 32), np.int64), path_lengths=np.zeros((n, 512), np.int64),
        type_ids=np.zeros((n, 512), np.int64), value_ids=np.zeros((n, 512), np.int64),
        numeric=np.zeros((n, 512, 2), np.float32), token_mask=np.zeros((n, 512), np.float32),
        slot_mask=np.ones(n, np.float32), identity_indices=np.asarray(
            [train_codes.index(c) + 1 if c in train_codes else 0 for c in codes], np.int64))
    for slot, document in enumerate(documents):
        for position, (path, kind, value) in enumerate(W.tokens(document)):
            try:
                ids = [lookup['path'][('index:' if type(k) is int else 'key:') + str(k)] for k in path]
                bank['type_ids'][slot, position] = lookup['type'][kind]
                bank['value_ids'][slot, position] = lookup['value'][
                    'NUMBER' if kind in ('number', 'length') else kind + ':' + str(value)]
            except KeyError as error:
                raise ValueError('unreviewed symbol; no remap') from error
            bank['path_ids'][slot, position, :len(ids)] = ids
            bank['path_lengths'][slot, position] = len(ids)
            bank['token_mask'][slot, position] = 1
            if kind in ('number', 'length'):
                bank['numeric'][slot, position] = (value / scale, np.sign(value) * np.log1p(abs(value)))
        if training and codes[slot] not in train_codes:
            for value in bank.values():
                value[slot] = 0
    return bank


def printed_bank(full, documents):
    """Mask original positions; never re-tokenize a shorter printed document."""
    import numpy as np
    W = frontend().prior(); bank = {key: value.copy() for key, value in full.items()}
    for slot, document in enumerate(documents):
        keep = np.zeros(512, dtype=bool)
        for position, (path, _, _) in enumerate(W.tokens(document)):
            keep[position] = not path or path[0] == 'printed'
        for key in TOKEN_ARRAYS:
            bank[key][slot, ~keep] = 0
    return bank


def make_banks(documents, codes, train_codes, symbols, donors, training=False, numeric_scale=None):
    """Return four E-compatible banks. Numeric scale fits original TRAIN only."""
    E = frontend(); codes, train_codes = list(codes), list(train_codes)
    swapped = swapped_documents(documents, codes, train_codes, donors)
    full, scale = E.make_bank(documents, codes, train_codes, symbols, training)
    require(math.isfinite(scale) and scale >= 1, 'finite original TRAIN scale required')
    if numeric_scale is not None:
        require(type(numeric_scale) in (int, float) and float(numeric_scale) == scale,
                'saved original FULL TRAIN scale changed; never refit an arm')
    printed = printed_bank(full, documents)
    return dict(full=full, printed=printed,
        swapped_full=_encode(swapped, codes, train_codes, symbols, scale, training),
        swapped_printed={key: value.copy() for key, value in printed.items()})


def metadata(nativeplan):
    """Pure NumPy metadata preparation, called only in the allocated stage.

    printed_documents are inspection views. Their shorter token positions MUST
    NOT be re-encoded: the actual printed intervention masks the FULL bank.
    """
    E = frontend(); cards = nativeplan['cards']; codes = [row['code'] for row in cards]
    train = list(nativeplan['split']['train_codes']); documents, audits = [], []
    for row in cards:
        doc, audit = E.canonical_document(row['raw_card'])
        documents.append(doc); audits.append(audit)
    symbols = E.symbols_for(documents); donors = fixed_donors(codes, train)
    train_symbols = E.symbols_for([d for code, d in zip(codes, documents) if code in train])
    held_atoms = {key: [value for value in symbols[key] if value not in train_symbols[key]]
                  for key in symbols}
    banks = make_banks(documents, codes, train, symbols, donors)
    # Same scale definition as the frozen frontend, with original TRAIN tokens.
    import numpy as np
    numbers = [value for code, doc in zip(codes, documents) if code in train
               for _, kind, value in E.prior().tokens(doc) if kind in ('number', 'length')]
    scale = max(1., float(np.std(numbers))) if numbers else 1.
    M = importlib.import_module('public_input_binding_model_v1')
    return dict(schema=SCHEMA, documents=documents,
        printed_documents=[dict(printed=copy.deepcopy(d['printed'])) for d in documents],
        swapped_documents=swapped_documents(documents, codes, train, donors), codes=codes,
        train_codes=train, held_codes=[c for c in codes if c not in train], donors=donors,
        vocabularies=symbols, numeric_scale=scale, parameters=M.parameter_counts(symbols, len(train)),
        semantic_signatures={name: E.tensor_signatures(bank) for name, bank in banks.items()},
        public_held_only_atoms=held_atoms,
        public_held_only_atom_counts={key: len(values) for key, values in held_atoms.items()},
        held_vocabulary_scope='Public held paths/value atoms are allocated before labels. Zero HELD training slots prevent held-observation gradients; dense AdamW decay can still change unused embedding rows. No optimizer change is introduced.',
        frontend=E.frontend_fingerprint(), frontend_audits=audits,
        bank_contract=dict(names=list(BANK_NAMES), max_tokens=512, max_path=32,
            numeric_scale='Original full TRAIN documents only; identical scale in all banks',
            printed='Original root plus path[0]==printed, all other token fields zero; original positions retained',
            swap='Abilities subtree only; fixed donor cycles within TRAIN and HELD partitions',
            swapped_printed='Byte-identical copy of correct printed bank',
            training='All arrays in every HELD slot zero, including identity and slot masks',
            id_only='TRAIN code index+1, HELD UNK0', public_only='Semantic vector multiplied by zero after encoding'),
        semantic_validated=False)


prepare_bank_metadata = metadata


def banks_from_metadata(meta, training=False):
    require(meta.get('schema') == SCHEMA, 'versioned bank metadata required')
    return make_banks(meta['documents'], meta['codes'], meta['train_codes'], meta['vocabularies'],
                      meta['donors'], training, meta['numeric_scale'])


def representation_signatures(meta, arm, swapped=False):
    if arm == 'public-only':
        return ['PUBLIC-ZERO'] * len(meta['codes'])
    if arm == 'ID-only':
        return ['ID:' + str(meta['train_codes'].index(c) + 1 if c in meta['train_codes'] else 0)
                for c in meta['codes']]
    require(arm in ('learned-full', 'frozen-full', 'printed-only'), 'unknown matched representation arm')
    key = 'printed' if arm == 'printed-only' else 'swapped_full' if swapped else 'full'
    return list(meta['semantic_signatures'][key])
