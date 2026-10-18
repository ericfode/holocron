"""Restricted analytical public-IR reference, never native labels or a game engine.

This helper describes direct consequences of one declared hand-play selection
(one selection followed by Done for upTo). It rejects unknown constructors and
expressions. It does not model lifecycle/trigger cascades or source-play heads.
Identity strings resolve public references only; no card-code dispatch exists.
"""
import copy
import math

SCHEMA = 'jepa-analytical-ability-reference/1'
HEADS = ('target_allowed', 'target_removed', 'target_damage_delta',
         'target_exhausted_delta', 'target_shield_delta',
         'target_power_delta', 'target_hp_delta')


class Unknown(ValueError):
    pass


def require(value, message):
    if not value:
        raise Unknown(message)


def number(value):
    require(type(value) in (int, float), 'finite number required')
    try:
        require(math.isfinite(value), 'finite number required')
        return float(value)
    except OverflowError as error:
        raise Unknown('finite number required') from error


def validate_program(ability):
    """Reject unreviewed constructs even when an ineligible intent skips execution."""
    def keys(node, allowed):
        require(isinstance(node, dict) and not set(node) - set(allowed), 'unreviewed typed field')
    def expression(node):
        require(isinstance(node, dict), 'typed expression required')
        kind = node.get('kind')
        if kind == 'const': keys(node, ('kind', 'value'))
        elif kind == 'ref': keys(node, ('kind', 'path'))
        elif kind == 'conditional':
            keys(node, ('kind', 'condition', 'then', 'else'))
            for k in ('condition', 'then', 'else'): expression(node[k])
        elif kind == 'binary':
            keys(node, ('kind', 'op', 'left', 'right'))
            expression(node['left']); expression(node['right'])
        elif kind == 'query':
            keys(node, ('kind', 'name', 'receiver', 'args'))
            require(node.get('name') in ('isUnit', 'hasSomeTrait', 'hasSomeAspect', 'hasSomeArenaUnit'),
                    'unsupported public query')
            expression(node['receiver'])
            for child in node.get('args', []): expression(child)
        else: raise Unknown('unsupported expression kind ' + str(kind))
    def selector(node):
        keys(node, ('owner', 'type', 'zone', 'arena', 'predicate', 'mode', 'count', 'optional'))
        if 'predicate' in node: expression(node['predicate'])
        if 'count' in node: expression(node['count'])
        if 'optional' in node: require(type(node['optional']) is bool, 'boolean optional required')
    def effect(node):
        require(isinstance(node, dict), 'typed effect required')
        kind = node.get('kind')
        if kind in ('damage', 'heal'):
            keys(node, ('kind', 'target', 'amount')); expression(node['amount'])
        elif kind == 'defeat': keys(node, ('kind', 'target'))
        elif kind == 'select':
            keys(node, ('kind', 'targetResolver', 'effect'))
            selector(node['targetResolver']); effect(node['effect'])
        elif kind == 'simultaneous':
            keys(node, ('kind', 'effects'))
            require(isinstance(node['effects'], list) and 1 <= len(node['effects']) <= 8,
                    'bounded nonempty simultaneous effects required')
            for child in node['effects']: effect(child)
        else: raise Unknown('unsupported effect ' + str(kind))
    keys(ability, ('trigger', 'title', 'contextTitle', 'promptTitle', 'costs', 'optional',
                   'effect', 'targetResolver', 'ifYouDo'))
    effect(ability['effect'])
    if 'targetResolver' in ability: selector(ability['targetResolver'])
    if 'ifYouDo' in ability:
        follow = ability['ifYouDo']
        keys(follow, ('title', 'contextTitle', 'promptTitle', 'costs', 'effect'))
        require(follow.get('costs', []) == [], 'additional continuation cost unsupported')
        effect(follow['effect'])


def current(p, name):
    require(p.get('known', {}).get(name) is True, 'unknown public ' + name)
    value = p.get(name)
    if name == 'exhausted':
        require(type(value) is bool, 'boolean exhaustion required')
        return float(value)
    return number(value)


def printed(p, name):
    key = 'printed_' + name
    require(p.get('known', {}).get(key) is True, 'unknown public ' + key)
    require(key in p, 'missing public ' + key)
    return p[key]


class Scene:
    def __init__(self, raw_card, case, rows=None):
        # Deliberately do not inspect case.after/final/prompts/offeredActions.
        self.projections = copy.deepcopy(case['before']['projections'])
        self.refs = dict(case['refs'])
        self.observations = list(case['observation_refs'])
        self.intent = dict(case['declared_intent'])
        self.source = self.projections['source']
        self.source_id = self.refs['source']
        self.own = self.source.get('owner')
        require(self.own in ('p1', 'p2') and self.source.get('known', {}).get('owner') is True,
                'known acting owner required')
        self.opponent = 'p2' if self.own == 'p1' else 'p1'
        self.initial = {}
        for role, p in self.projections.items():
            if p is None:
                continue
            require(p.get('id') == self.refs[role] and p.get('known', {}).get('identity') is True,
                    'public reference identity mismatch')
            require(p.get('zone') not in ('deck', 'hand') or
                    (role == 'source' and p.get('owner') == self.own and p.get('zone') == 'hand'),
                    'private observation forbidden')
            if p['id'] in self.initial:
                require(self.initial[p['id']] == p, 'duplicate public reference disagrees')
            self.initial[p['id']] = copy.deepcopy(p)
        self.state = copy.deepcopy(self.initial)
        require(set(raw_card['abilities']) == {'card', 'unit', 'leader'} and
                not raw_card['abilities']['unit'] and not raw_card['abilities']['leader'] and
                len(raw_card['abilities']['card']) == 1, 'one main-card ability required')
        self.ability = copy.deepcopy(raw_card['abilities']['card'][0])
        validate_program(self.ability)
        require(self.ability.get('trigger') in ('event', 'whenPlayed'),
                'only event/whenPlayed declaration task supported')
        require(self.ability.get('costs', []) == [], 'additional ability cost unsupported')
        require(not any(k in self.ability for k in ('condition', 'then', 'targetResolvers')),
                'unreviewed top-level composition')
        # The public printed rule says a played unit enters its arena before its
        # whenPlayed ability. This is an analytical rule, not an observed future.
        if self.ability['trigger'] == 'whenPlayed':
            types = raw_card['card']['types']
            require(types == ['unit'], 'whenPlayed reference admits units only')
            arena = raw_card['card'].get('arena')
            require(arena in ('ground', 'space'), 'known printed source arena required')
            self.state[self.source_id]['zone'] = arena
            self.state[self.source_id]['is_unit'] = True
            self.state[self.source_id]['present'] = True
        self.intended_id = self.refs.get(self.intent.get('ref'))
        require(self.intent.get('requires_target') is True and
                self.intent.get('id') == self.intended_id and self.intended_id in self.state,
                'one explicit known declared target required')
        self.arena_complete = False
        try:
            raw_ids = {u['id'] for seat in ('p1', 'p2') for zone in ('ground', 'space')
                       for u in case['before']['state']['players'][seat][zone]}
            projected = {p['id'] for p in self.initial.values()
                         if p.get('present') is True and p.get('is_unit') is True and
                         p.get('zone') in ('ground', 'space')}
            self.arena_complete = raw_ids == projected
        except (KeyError, TypeError):
            pass

    def expr(self, node, candidate):
        require(isinstance(node, dict), 'typed expression required')
        kind = node.get('kind')
        if kind == 'const':
            value = node.get('value')
            require(value is None or type(value) in (bool, int, float, str), 'primitive literal required')
            if type(value) in (int, float):
                number(value)
            return value
        if kind == 'conditional':
            condition = self.expr(node['condition'], candidate)
            require(type(condition) is bool, 'boolean condition required')
            return self.expr(node['then'] if condition else node['else'], candidate)
        if kind == 'ref':
            path = node.get('path')
            require(isinstance(path, list) and path, 'typed reference path required')
            root = {'card': candidate, 'source': self.state[self.source_id],
                    'player': self.own}.get(path[0])
            require(root is not None, 'unsupported reference root')
            if len(path) == 1:
                return root
            require(isinstance(root, dict) and len(path) == 2, 'unsupported reference path')
            if path[1] == 'cost':
                return number(printed(root, 'cost'))
            if path[1] == 'remainingHp':
                return current(root, 'hp') - current(root, 'damage')
            if path[1] == 'zoneName':
                return {'ground': 'groundArena', 'space': 'spaceArena', 'base': 'base'}.get(root['zone'])
            raise Unknown('unsupported reference property')
        if kind == 'binary':
            op = node['op']; left = self.expr(node['left'], candidate)
            if op in ('&&', '||'):
                require(type(left) is bool, 'boolean operand required')
                if (op == '&&' and not left) or (op == '||' and left):
                    return left
                right = self.expr(node['right'], candidate)
                require(type(right) is bool, 'boolean operand required')
                return right
            right = self.expr(node['right'], candidate)
            if op in ('<=', '<', '>=', '>', '+', '-'):
                left, right = number(left), number(right)
                return {'<=': lambda: left <= right, '<': lambda: left < right,
                        '>=': lambda: left >= right, '>': lambda: left > right,
                        '+': lambda: left + right, '-': lambda: left - right}[op]()
            if op in ('===', '!=='):
                equal = type(left) is type(right) and left == right
                return equal if op == '===' else not equal
            raise Unknown('unsupported binary operator')
        if kind == 'query':
            name = node['name']; receiver = self.expr(node['receiver'], candidate)
            if name == 'hasSomeArenaUnit':
                require(receiver == self.own and self.arena_complete and len(node['args']) == 1,
                        'complete own public arena required')
                return any(self.expr(node['args'][0], p) for p in self.state.values()
                           if p.get('owner') == self.own and p.get('present') is True and
                           p.get('is_unit') is True and p.get('zone') in ('ground', 'space'))
            require(isinstance(receiver, dict), 'public card query receiver required')
            if name == 'isUnit':
                require(node.get('args', []) == [], 'isUnit takes no arguments')
                return receiver.get('is_unit') is True
            if name in ('hasSomeTrait', 'hasSomeAspect'):
                args = [self.expr(n, candidate) for n in node.get('args', [])]
                require(len(args) == 1 and isinstance(args[0], str), 'one predicate literal required')
                values = printed(receiver, 'traits' if name == 'hasSomeTrait' else 'aspects')
                require(isinstance(values, list), 'printed metadata list required')
                return args[0] in values
            raise Unknown('unsupported query ' + name)
        raise Unknown('unsupported expression kind ' + str(kind))

    def allowed(self, resolver, p, effect):
        if not p.get('present') or p.get('zone') not in ('ground', 'space', 'base'):
            return False
        owner = resolver.get('owner', 'any')
        require(owner in ('any', 'self', 'opponent'), 'unsupported target owner')
        if owner != 'any' and p.get('owner') != (self.own if owner == 'self' else self.opponent):
            return False
        target_type = resolver.get('type', 'any')
        require(target_type in ('any', 'unit', 'nonLeaderUnit', 'base'), 'unsupported target type')
        unit, base = p.get('is_unit') is True, p.get('is_base') is True
        if not (unit or base) or (target_type in ('unit', 'nonLeaderUnit') and not unit) or (target_type == 'base' and not base):
            return False
        if target_type == 'nonLeaderUnit' and 'leader' in printed(p, 'types'):
            return False
        zone = resolver.get('zone', 'anyAttackable')
        require(zone in ('anyAttackable', 'arena', 'base'), 'unsupported target zone')
        if zone == 'arena' and not unit or zone == 'base' and not base:
            return False
        if 'arena' in resolver:
            require(resolver['arena'] in ('ground', 'space'), 'unsupported arena')
            if p.get('zone') != resolver['arena']:
                return False
        if 'predicate' in resolver:
            value = self.expr(resolver['predicate'], p)
            require(type(value) is bool, 'boolean target predicate required')
            if not value:
                return False
        if 'mode' in resolver:
            require(resolver['mode'] == 'upTo' and self.expr(resolver['count'], p) >= 1,
                    'only one selection plus Done upTo task supported')
        if effect.get('kind') == 'heal':
            return current(p, 'damage') > 0 and number(self.expr(effect['amount'], p)) > 0
        return True

    def apply(self, effect, chosen):
        kind = effect.get('kind')
        if kind == 'select':
            require(self.allowed(effect['targetResolver'], self.state[chosen], effect['effect']),
                    'nested selected target is ineligible')
            return self.apply(effect['effect'], chosen)
        if kind == 'simultaneous':
            original = copy.deepcopy(self.state); changes = {}; changed = False
            for child in effect['effects']:
                self.state = copy.deepcopy(original)
                changed |= self.apply(child, chosen)
                delta = {k: v for k, v in self.state.items() if v != original[k]}
                require(not set(changes) & set(delta), 'overlapping simultaneous writes unsupported')
                changes.update(delta)
            self.state = original; self.state.update(changes)
            return changed
        require(kind in ('damage', 'heal', 'defeat'), 'unsupported effect ' + str(kind))
        target = effect.get('target')
        if target == 'chosen': identity = chosen
        elif target == 'self': identity = self.source_id
        elif target == 'ownBase':
            bases = [p['id'] for p in self.state.values() if p.get('is_base') is True and p.get('owner') == self.own]
            require(len(bases) == 1, 'one public own base required'); identity = bases[0]
        else: raise Unknown('unsupported effect destination')
        p = self.state[identity]
        require(p.get('present') is True, 'effect target absent')
        if kind == 'defeat':
            require(p.get('is_unit') is True, 'only unit defeat admitted')
            p['present'] = False; p['zone'] = 'discard'; return True
        amount = number(self.expr(effect['amount'], p)); require(amount >= 0, 'negative amount unsupported')
        if kind == 'heal':
            old = current(p, 'damage'); p['damage'] = max(0., old - amount); return p['damage'] != old
        if amount > 0 and p.get('is_unit') is True and current(p, 'shield_count') > 0:
            p['shield_count'] -= 1; return True
        old = current(p, 'damage'); p['damage'] = old + amount
        if p.get('is_unit') is True and p['damage'] >= current(p, 'hp'):
            p['present'] = False; p['zone'] = 'discard'
        return amount > 0


def _selector(ability):
    if 'targetResolver' in ability:
        return ability['targetResolver'], ability['effect']
    effect = ability['effect']
    if effect.get('kind') == 'simultaneous':
        selects = [e for e in effect.get('effects', []) if e.get('kind') == 'select']
        require(len(selects) == 1, 'one nested selector required')
        return selects[0]['targetResolver'], selects[0]['effect']
    raise Unknown('no reviewed chosen-target selector')


def reference_case(raw_card, case, rows=None):
    """Return analytical values7/masks7 by public role; no native truth is read.

    Eligibility describes each candidate independently of the declared intent.
    Consequences describe committing that intent, or declining an optional
    selection. Mandatory ineligible intentions have unknown future outcomes.
    Source lifecycle heads and source endpoint consequences are always unknown.
    """
    output = dict(schema=SCHEMA, label_origin='analytical-public-IR-not-native',
        status='unknown', semantic_validated=False, observations={},
        source=dict(values=[0.] * 9, mask=[0] * 9), unsupported_reasons=[],
        scope='Direct selected program only; no lifecycle/cascade equivalence, no source-play predictions')
    for role in case.get('observation_refs', []):
        output['observations'][role] = dict(values=[0.] * len(HEADS), mask=[0] * len(HEADS))
    try:
        scene = Scene(raw_card, case, rows); resolver, effect = _selector(scene.ability)
        allowed = {}; reasons = []
        for role in scene.observations:
            p = scene.projections.get(role)
            if p is None or role == 'source':
                continue
            try:
                allowed[scene.refs[role]] = scene.allowed(resolver, scene.state[p['id']], effect)
                output['observations'][role]['values'][0] = float(allowed[p['id']])
                output['observations'][role]['mask'][0] = 1
            except Unknown as error:
                reasons.append(role + ': ' + str(error))
        intent_allowed = scene.allowed(resolver, scene.state[scene.intended_id], effect)
        future_known = intent_allowed or scene.ability.get('optional') is True or resolver.get('optional') is True
        if intent_allowed:
            did = scene.apply(scene.ability['effect'], scene.intended_id)
            if did and 'ifYouDo' in scene.ability:
                follow = scene.ability['ifYouDo']
                require(follow.get('costs', []) == [] and not any(k in follow for k in ('condition', 'targetResolver', 'then', 'ifYouDo')),
                        'unsupported ifYouDo continuation')
                scene.apply(follow['effect'], scene.intended_id)
        if future_known:
            for role, result in output['observations'].items():
                if role == 'source' or scene.projections.get(role) is None:
                    continue
                before = scene.initial[scene.refs[role]]; after = scene.state[scene.refs[role]]
                result['values'][1] = float(before.get('present') is True and after.get('present') is not True)
                result['mask'][1] = 1
                if result['values'][1]:
                    continue  # Physical numeric fields after departure stay unknown.
                for index, field in ((2, 'damage'), (3, 'exhausted'), (4, 'shield_count'), (5, 'power'), (6, 'hp')):
                    try:
                        result['values'][index] = current(after, field) - current(before, field)
                        result['mask'][index] = 1
                    except Unknown:
                        pass
        else:
            reasons.append('mandatory ineligible intent: no settled future predicted')
        output['status'] = 'partial' if reasons else 'known-direct-scope'
        output['unsupported_reasons'] = reasons
    except (Unknown, KeyError, TypeError, IndexError) as error:
        # A rejected constructor cannot leave partially asserted predictions.
        for result in output['observations'].values():
            result['values'] = [0.] * len(HEADS); result['mask'] = [0] * len(HEADS)
        output['unsupported_reasons'] = [str(error)]
    return output
