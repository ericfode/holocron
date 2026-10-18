"""Restricted typed Kessel capability/action adapter; no learned encoder or optimizer.

Identity/title/source paths remain provenance. Object-key order is immaterial;
effect sequence indices and expression operand roles remain semantic. Unknown
operations or ambiguous action/program bindings fail closed.
"""
from collections import Counter
import copy
from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path
import time

PINNED_KESSEL_COMMIT="c7ee39554901278cee70f61fd8b26fb1920696b3"
ADAPTER_SCHEMA="jepa-typed-ir-wiring/1"
MAX_SEMANTIC_TOKENS=512
MAX_ROLE_TOKENS=32
PINNED_SOURCE=Path("/Users/ericfode/Documents/Codex/2026-10-17/task-5/kessel-pilot-source")
HERE=Path(__file__).resolve().parent
RUNTIME_ADMISSION={
    "ASH_011":dict(admitted=True,source="compiler/generated/runtime-admission.json:26"),
    "IBH_053":dict(admitted=True,source="compiler/generated/runtime-admission.json:1546"),
    "IBH_001":dict(admitted=False,source="compiler/generated/runtime-admission.json:7137",reason="unit-side numCardsFunc selector is unsupported"),
    "SHD_002":dict(admitted=False,source="compiler/generated/runtime-admission.json:10002",reason="unit-side systemPropertiesFactory is unsupported"),
}

# Exact reviewed catalog excerpts; these are data, never JSON/text model inputs.
REVIEWED_CARDS=[{'abilities': {'leader': [{'costs': [{'kind': 'exhaustSelf'}],
                            'effect': {'amount': {'kind': 'const', 'value': 1},
                                       'kind': 'damage',
                                       'target': 'chosen'},
                            'targetResolver': {'owner': 'any',
                                               'predicate': {'kind': 'binary',
                                                             'left': {'args': [],
                                                                      'kind': 'query',
                                                                      'name': 'isUnit',
                                                                      'receiver': {'kind': 'ref',
                                                                                   'path': ['card']}},
                                                             'op': '&&',
                                                             'right': {'kind': 'binary',
                                                                       'left': {'kind': 'ref',
                                                                                'path': ['card', 'remainingHp']},
                                                                       'op': '>=',
                                                                       'right': {'kind': 'const', 'value': 2}}},
                                               'type': 'unit',
                                               'zone': 'anyAttackable'},
                            'title': 'Deal 1 damage to a unit with 2 or more remaining HP',
                            'trigger': 'action'}]},
  'abilityPath': ['abilities', 'leader', 0],
  'setCode': 'ASH_011',
  'sourceHash': 'c8deebf53ed30519ed4b4abe6b274f1c460997a55b209174e28125f3cec7752f',
  'sourcePath': 'game/cards/08_ASH/leaders/CadBaneStillFasterThanYou.ts',
  'status': 'supported'},
 {'abilities': {'leader': [{'costs': [{'amount': {'kind': 'const', 'value': 1}, 'kind': 'resources'},
                                      {'kind': 'exhaustSelf'}],
                            'effect': {'amount': {'kind': 'const', 'value': 1},
                                       'kind': 'heal',
                                       'target': 'chosen'},
                            'targetResolver': {'owner': 'self', 'type': 'unit', 'zone': 'anyAttackable'},
                            'title': 'Heal 1 damage from a friendly unit',
                            'trigger': 'action'}]},
  'abilityPath': ['abilities', 'leader', 0],
  'setCode': 'IBH_001',
  'sourceHash': '3c0fe1607253abaacff9632e5c79b03128acb6238a8cddf1eb44a6b40abd3f71',
  'sourcePath': 'game/cards/06_IBH/leaders/LeiaOrganaGetToYourTransports.ts',
  'status': 'supported'},
 {'abilities': {'leader': [{'costs': [{'amount': {'kind': 'const', 'value': 1}, 'kind': 'resources'},
                                      {'kind': 'exhaustSelf'}],
                            'effect': {'amount': {'kind': 'const', 'value': 1},
                                       'kind': 'damage',
                                       'target': 'chosen'},
                            'targetResolver': {'owner': 'any', 'type': 'any', 'zone': 'base'},
                            'title': 'Deal 1 damage to a base',
                            'trigger': 'action'}]},
  'abilityPath': ['abilities', 'leader', 0],
  'setCode': 'IBH_053',
  'sourceHash': '93cdf6459ac9de34369a172aec6a2729cb608c749f6a0bd847ccea8656987c41',
  'sourcePath': 'game/cards/06_IBH/leaders/DarthVaderDontFailMeAgain.ts',
  'status': 'supported'},
 {'abilities': {'leader': [{'costs': [{'kind': 'exhaustSelf'},
                                      {'amount': {'kind': 'const', 'value': 1}, 'kind': 'resources'}],
                            'effect': {'effects': [{'amount': {'kind': 'const', 'value': 2},
                                                    'kind': 'damage',
                                                    'target': 'chosen'},
                                                   {'amount': {'kind': 'const', 'value': 1},
                                                    'kind': 'giveShield',
                                                    'target': 'chosen'}],
                                       'kind': 'sequence'},
                            'targetResolver': {'owner': 'self', 'type': 'unit', 'zone': 'anyAttackable'},
                            'title': 'Deal 2 damage to a friendly unit. Then, give a Shield token to it',
                            'trigger': 'action'}]},
  'abilityPath': ['abilities', 'leader', 0],
  'setCode': 'SHD_002',
  'sourceHash': 'bb15f551f385efc4f8cd4cfa8b0b8f0b495da82825e9893e3c7ec1bf6c4b8295',
  'sourcePath': 'game/cards/02_SHD/leaders/QiraIAloneSurvived.ts',
  'status': 'supported'}]


class UnknownIR(ValueError):
    pass


@dataclass(frozen=True)
class Token:
    path: tuple
    value_type: str
    value: object


@dataclass
class Encoding:
    known: bool
    semantic_tokens: tuple=()
    role_tokens: tuple=()
    program: dict|None=None
    provenance: dict=field(default_factory=dict)
    reason: str|None=None


def encoding_record(encoded):
    """Versioned inspection contract, not a production tensor/graph ABI."""
    def tokens(values):
        return [dict(path=list(t.path),value_type=t.value_type,value=t.value)for t in values]
    return dict(schema=ADAPTER_SCHEMA,status="known"if encoded.known else"unknown",known=encoded.known,
        coverage_status="selected-ability"if encoded.known else"unknown",
        semantic_tokens=tokens(encoded.semantic_tokens),role_tokens=tokens(encoded.role_tokens),
        program=encoded.program,provenance=encoded.provenance,reason=encoded.reason,
        numeric_feature_width=None,production_graph_integration=False)


def _object(value,allowed,required=()):
    if not isinstance(value,dict) or set(value)-set(allowed) or not set(required)<=set(value):
        raise UnknownIR("unsupported keys or missing typed fields")


def _enum(value,choices):
    if not isinstance(value,str) or value not in choices: raise UnknownIR("unsupported enum")
    return value


def _integer(value):
    if type(value)is not int or not 0<=value<=65535: raise UnknownIR("bounded unsigned integer required")
    return value


def _boolean(value):
    if type(value)is not bool: raise UnknownIR("boolean required")
    return value


def expression_type(expr):
    if expr["kind"]=="const": return "boolean" if type(expr["value"])is bool else "integer"
    if expr["kind"]=="ref":
        return {("card",):"object",("source",):"object",("card","remainingHp"):"integer",("source","exhausted"):"boolean"}[tuple(expr["path"])]
    return "boolean"


def expression(value,depth=0):
    if depth>8: raise UnknownIR("expression nesting exceeds admitted bound")
    if not isinstance(value,dict): raise UnknownIR("typed expression required")
    kind=value.get("kind")
    if kind=="const":
        _object(value,{"kind","value"},{"kind","value"})
        literal=value["value"]
        if type(literal)is not bool: _integer(literal)
        return dict(kind="const",value=literal)
    if kind=="ref":
        _object(value,{"kind","path"},{"kind","path"})
        path=tuple(value["path"]) if isinstance(value["path"],list) else ()
        if path not in (("card",),("source",),("card","remainingHp"),("source","exhausted")):
            raise UnknownIR("unreviewed reference path")
        return dict(kind="ref",path=list(path))
    if kind=="query":
        _object(value,{"kind","name","receiver","args"},{"kind","name","receiver","args"})
        if value["name"]!="isUnit" or value["args"]!=[]: raise UnknownIR("unreviewed query")
        receiver=expression(value["receiver"],depth+1)
        if receiver!={"kind":"ref","path":["card"]}: raise UnknownIR("isUnit receiver must be selection card")
        return dict(kind="query",name="isUnit",receiver=receiver,args=[])
    if kind=="binary":
        _object(value,{"kind","op","left","right"},{"kind","op","left","right"})
        op=_enum(value["op"],("&&",">=","<=","===","!=="))
        left=expression(value["left"],depth+1); right=expression(value["right"],depth+1)
        lt,rt=expression_type(left),expression_type(right)
        if (op=="&&" and (lt!="boolean"or rt!="boolean"))or(op in(">=","<=")and(lt!="integer"or rt!="integer")):
            raise UnknownIR("expression operand type mismatch")
        if op in("===","!==")and(lt!=rt or lt=="object"):
            raise UnknownIR("object identity comparison is not in the reviewed expression subset")
        return dict(kind="binary",op=op,left=left,right=right)
    raise UnknownIR("unreviewed expression kind")


def selector(value):
    _object(value,{"owner","type","zone","arena","predicate","optional"},{"owner","type","zone"})
    out=dict(owner=_enum(value["owner"],("self","opponent","any")),
             type=_enum(value["type"],("unit","base","any")),
             zone=_enum(value["zone"],("arena","base","anyAttackable")),optional=_boolean(value.get("optional",False)))
    if "arena"in value: out["arena"]=_enum(value["arena"],("ground","space"))
    if "predicate"in value:
        out["predicate"]=expression(value["predicate"])
        if expression_type(out["predicate"])!="boolean": raise UnknownIR("selector predicate must be boolean")
    return out


def effect(value,depth=0):
    if depth>8 or not isinstance(value,dict): raise UnknownIR("effect bound/type unsupported")
    if value.get("kind")=="sequence":
        _object(value,{"kind","effects"},{"kind","effects"})
        if not isinstance(value["effects"],list) or not 1<=len(value["effects"])<=4: raise UnknownIR("sequence size unsupported")
        return dict(kind="sequence",effects=[effect(v,depth+1) for v in value["effects"]])
    _object(value,{"kind","target","amount"},{"kind","target","amount"})
    kind=_enum(value["kind"],("damage","heal","giveShield"))
    target=_enum(value["target"],("chosen",))
    amount=expression(value["amount"])
    if amount["kind"]!="const" or type(amount["value"])is not int: raise UnknownIR("primitive requires a literal amount")
    if kind=="giveShield" and amount["value"]!=1: raise UnknownIR("only one shield is reviewed")
    return dict(kind=kind,target=target,amount=amount)


def ability(value):
    _object(value,{"trigger","title","costs","optional","requiresConfirmation","condition","targetResolver","effect"},{"trigger","title","targetResolver","effect"})
    if not isinstance(value["title"],str): raise UnknownIR("title must be a string, retained only in provenance")
    out=dict(trigger=_enum(value["trigger"],("action",)),optional=_boolean(value.get("optional",False)),
             requiresConfirmation=_boolean(value.get("requiresConfirmation",False)),costs=[])
    if not isinstance(value.get("costs",[]),list) or len(value.get("costs",[]))>4: raise UnknownIR("cost list unsupported")
    for cost in value.get("costs",[]):
        if not isinstance(cost,dict): raise UnknownIR("cost object required")
        if cost.get("kind")=="exhaustSelf":
            _object(cost,{"kind"},{"kind"}); out["costs"].append(dict(kind="exhaustSelf"))
        elif cost.get("kind")=="resources":
            _object(cost,{"kind","amount"},{"kind","amount"}); amount=expression(cost["amount"])
            if amount["kind"]!="const" or type(amount["value"])is not int: raise UnknownIR("literal resource cost required")
            out["costs"].append(dict(kind="resources",amount=amount))
        else: raise UnknownIR("unreviewed cost")
    if value.get("condition")is not None:
        out["condition"]=expression(value["condition"])
        if expression_type(out["condition"])!="boolean": raise UnknownIR("ability condition must be boolean")
    if value["targetResolver"]is None: raise UnknownIR("an explicit chosen-target resolver is required")
    out["targetResolver"]=selector(value["targetResolver"])
    out["effect"]=effect(value["effect"])
    return out


def typed_tokens(value,path=()):
    """Shared structural featurizer: sorted object edges, ordered array edges."""
    def walk(value,path):
        if isinstance(value,dict):
            yield Token(path,"node","object")
            for key in sorted(value): yield from walk(value[key],path+(key,))
        elif isinstance(value,list):
            yield Token(path,"node","ordered-list");yield Token(path,"length",len(value))
            for i,child in enumerate(value): yield from walk(child,path+(i,))
        elif type(value)is bool: yield Token(path,"boolean",value)
        elif type(value)is int: yield Token(path,"integer",value)
        elif isinstance(value,str): yield Token(path,"enum",value)
        else: raise UnknownIR("untyped semantic value")
    tokens=[]
    for token in walk(value,path):
        if len(tokens)>=MAX_SEMANTIC_TOKENS: raise UnknownIR("typed token budget exceeded")
        tokens.append(token)
    return tuple(tokens)


def capability(card,path):
    provenance={k:copy.deepcopy(card.get(k)) for k in ("setCode","sourcePath","sourceHash","status")}
    provenance.update(ability_path=list(path),coverage="selected ability only; not whole-card admission")
    provenance["whole_card_runtime_admission"]=copy.deepcopy(RUNTIME_ADMISSION.get(card.get("setCode"),dict(admitted=None,reason="not reviewed")))
    try:
        if len(path)!=3 or path[0]!="abilities" or path[1]not in ("leader","unit","card") or type(path[2])is not int or path[2]<0:
            raise UnknownIR("explicit ability side/index required")
        raw=card[path[0]][path[1]][path[2]]
        program=ability(raw)
        roles=(Token(("source",),"form",path[1]),*[Token((role,),"role","ownPlayer")for role in("controller","chooser","payer")])
        return Encoding(True,typed_tokens(program),roles,program,provenance)
    except (UnknownIR,KeyError,IndexError,TypeError) as exc:
        return Encoding(False,provenance=provenance,reason=str(exc))


@dataclass(frozen=True)
class CuratedBinding:
    source_instance: str
    source_card: str
    ability_path: tuple
    stage: str
    offered_action: dict
    card: dict


def action_key(offered):
    _object(offered,{"kind","card","arg","method","label"},{"kind","card","arg","method","label"})
    if offered["kind"]not in ("button","card"): raise UnknownIR("offered kind outside reviewed microfixtures")
    # The exact offered tuple is a binding witness, never a semantic feature.
    return tuple(json.dumps(offered[k],sort_keys=True,separators=(",",":")) for k in ("kind","card","arg","method","label"))


def evaluate_expression(expr,state):
    kind=expr["kind"]
    if kind=="const": return expr["value"]
    if kind=="ref":
        paths={("card",):state["chosen"],("source",):state["source"],
               ("card","remainingHp"):state["chosen"]["hp"]-state["chosen"]["damage"],
               ("source","exhausted"):state["source"]["exhausted"]}
        return paths[tuple(expr["path"])]
    if kind=="query": return evaluate_expression(expr["receiver"],state)["type"]=="unit"
    left=evaluate_expression(expr["left"],state); right=evaluate_expression(expr["right"],state)
    return {"&&":lambda:bool(left)and bool(right),">=":lambda:left>=right,"<=":lambda:left<=right,
            "===":lambda:type(left)is type(right)and left==right,"!==":lambda:type(left)is not type(right)or left!=right}[expr["op"]]()


def roles_compatible(encoded,state):
    if not encoded.known: return False
    resolver=encoded.program.get("targetResolver")
    if resolver is None: return False
    chosen=state["chosen"]
    if chosen.get("owner")not in("self","opponent")or chosen.get("type")not in("unit","base"): return False
    if (chosen["type"]=="unit"and chosen.get("zone")!="arena")or(chosen["type"]=="base"and chosen.get("zone")!="base"): return False
    if resolver["owner"]!="any" and resolver["owner"]!=chosen["owner"]: return False
    if resolver["type"]!="any" and resolver["type"]!=chosen["type"]: return False
    if resolver["zone"]!="anyAttackable" and resolver["zone"]!=chosen["zone"]: return False
    if resolver.get("arena")is not None and resolver["arena"]!=chosen.get("arena"): return False
    return True


def instantiate_action(offered,context,bindings):
    """Unique reviewed source/program/stage binding; labels do not infer an IR node."""
    try:
        key=action_key(offered)
        matches=[b for b in bindings if b.source_instance==context["source_instance"] and b.source_card==context["source_card"]
                 and b.stage==context["stage"] and action_key(b.offered_action)==key]
        if len(matches)!=1: return Encoding(False,reason=f"expected one curated binding, found{len(matches)}")
        bound=matches[0]; encoded=capability(bound.card,bound.ability_path)
        if not encoded.known: return encoded
        if bound.card.get("setCode")!=bound.source_card or context.get("source_form")!=bound.ability_path[1]:
            return Encoding(False,reason="curated source card/form does not match selected program")
        if context["state"]["source"].get("owner")!="self": return Encoding(False,reason="source controller role is outside own-action subset")
        if context["source_form"]!="leader"or context["state"]["source"].get("type")!="leader"or context["state"]["source"].get("deployed",False):
            return Encoding(False,reason="only undeployed leader source forms have reviewed action fixtures")
        if context["stage"]!="abilityTarget" or offered["kind"]!="card" or offered["card"]!=context["chosen_instance"]:
            return Encoding(False,reason="only fully chosen target-stage fixtures are admitted")
        if not roles_compatible(encoded,context["state"]): return Encoding(False,reason="target role/domain incompatible")
        predicate=encoded.program["targetResolver"].get("predicate")
        if predicate is not None and not evaluate_expression(predicate,context["state"]):
            return Encoding(False,reason="chosen target contradicts reviewed predicate")
        source=context["state"]["source"]; chosen=context["state"]["chosen"]
        encoded.role_tokens=encoded.role_tokens+tuple(Token((role,),key,value) for role,values in (
            ("source",{"owner":source["owner"],"type":source["type"]}),
            ("chosen",{"owner":chosen["owner"],"type":chosen["type"],"zone":chosen["zone"]}),
            ("bindings",{"source_equals_chosen":context["source_instance"]==context["chosen_instance"]}),
            ("recipient",{"role":"chosen"})) for key,value in sorted(values.items()))
        if len(encoded.role_tokens)>MAX_ROLE_TOKENS: raise UnknownIR("role token budget exceeded")
        encoded.provenance.update(binding_stage=context["stage"],binding_kind="explicit curated source/program/target witness")
        return encoded
    except (UnknownIR,KeyError,TypeError) as exc:
        return Encoding(False,reason=str(exc))


def synthetic_affordance(encoded,state):
    if not roles_compatible(encoded,state): return False
    p=encoded.program
    if p.get("condition")is not None and not evaluate_expression(p["condition"],state): return False
    predicate=p["targetResolver"].get("predicate")
    if predicate is not None and not evaluate_expression(predicate,state): return False
    resource_cost=sum(c["amount"]["value"] for c in p["costs"] if c["kind"]=="resources")
    return state["ready_resources"]>=resource_cost and not(any(c["kind"]=="exhaustSelf" for c in p["costs"])and state["source"]["exhausted"])


def synthetic_transition(encoded,state):
    """Restricted committed-target oracle, not a Kessel runtime replacement.

    Nonlethal scalar damage/heal and one shield on one chosen target only.
    No triggers, defeat, cancellation, hidden cards, replacement effects other
    than a single shield, or persistent registrations are simulated.
    """
    if not synthetic_affordance(encoded,state): raise UnknownIR("primitive oracle precondition not met")
    out=copy.deepcopy(state); p=encoded.program
    if p["optional"]or p["requiresConfirmation"]: raise UnknownIR("optional/confirmation oracle unsupported")
    for cost in p["costs"]:
        if cost["kind"]=="resources": out["ready_resources"]-=cost["amount"]["value"]
        else: out["source"]["exhausted"]=True
    def apply(e):
        if e["kind"]=="sequence":
            for child in e["effects"]: apply(child)
            return
        if e["target"]!="chosen": raise UnknownIR("oracle requires an explicitly chosen target")
        target=out["chosen"]; amount=e["amount"]["value"]
        if e["kind"]=="damage":
            if target["shield"]==1 and amount: target["shield"]=0
            elif target["damage"]+amount>=target["hp"]: raise UnknownIR("lethal transitions outside primitive oracle")
            else: target["damage"]+=amount
        elif e["kind"]=="heal": target["damage"]=max(0,target["damage"]-amount)
        else:
            if target["shield"]!=0: raise UnknownIR("multiple shields outside primitive oracle")
            target["shield"]=1
    apply(p["effect"])
    return out


def fixture(card,index):
    # Shape follows model.rs Action::card and generic_runtime AbilityTarget.
    # Source/program state is an explicit curated witness, not inferred from label.
    own=card["setCode"]in ("IBH_001","SHD_002")
    base=card["setCode"]=="IBH_053"
    state=dict(ready_resources=3,source={"owner":"self","type":"leader","exhausted":False},
               chosen={"owner":"self"if own else"opponent","type":"base"if base else"unit", "zone":"base"if base else"arena",
                       "arena":"ground","hp":10,"damage":3,"shield":0})
    offered=dict(kind="card",card=f"c{20+index}",arg=None,method=None,label="curated public target")
    context=dict(source_instance=f"c{10+index}",source_card=card["setCode"],source_form="leader",chosen_instance=offered["card"],stage="abilityTarget",state=state)
    binding=CuratedBinding(context["source_instance"],card["setCode"],tuple(card["abilityPath"]),context["stage"],offered,card)
    return offered,context,binding


def hard_negatives(card):
    negatives={}
    for name in ("cost","condition","target","effect"):
        changed=copy.deepcopy(card); a=changed["abilities"]["leader"][0]
        if name=="cost": a["costs"].append({"kind":"resources","amount":{"kind":"const","value":2}})
        elif name=="condition": a["condition"]={"kind":"const","value":False}
        elif name=="target": a["targetResolver"]["owner"]="any" if a["targetResolver"]["owner"]!="any"else"opponent"
        else:
            e=a["effect"]
            if e["kind"]=="sequence": e["effects"][0]["amount"]["value"]+=1
            else: e["amount"]["value"]+=1
        negatives[name]=changed
    if card["abilities"]["leader"][0]["effect"]["kind"]=="sequence":
        changed=copy.deepcopy(card); changed["abilities"]["leader"][0]["effect"]["effects"].reverse(); negatives["sequence"]=changed
    return negatives


def cosine(left,right):
    a=Counter(left.semantic_tokens); b=Counter(right.semantic_tokens)
    dot=sum(value*b[token] for token,value in a.items())
    norm=math.sqrt(sum(v*v for v in a.values())*sum(v*v for v in b.values()))
    return dot/norm if norm else 0.


def frozen_alignment(action,candidates,state,positive=0,temperature=.07):
    mask=[action.known and c.known and roles_compatible(c,state)for c in candidates]
    if not mask[positive]: raise UnknownIR("positive binding role mask is unknown/incompatible")
    scores=[cosine(action,c) if allowed else None for c,allowed in zip(candidates,mask)]
    logits=[score/temperature for score in scores if score is not None]
    maximum=max(logits)
    loss=-(scores[positive]/temperature-maximum-math.log(sum(math.exp(v-maximum)for v in logits)))
    return dict(scores=scores,role_compatible_mask=mask,positive_index=positive,temperature=temperature,
                frozen_info_nce_loss=loss,positive_unique_best=all(s is None or i==positive or scores[positive]>s for i,s in enumerate(scores)),
                interpretation="Shared deterministic feature consistency only; no learned alignment or representation-success claim.")


def structural_report():
    """Deterministic wiring diagnostics; labels here do not establish semantics."""
    started=time.perf_counter()
    cards=[]
    for i,card in enumerate(REVIEWED_CARDS):
        encoded=capability(card,card["abilityPath"])
        offered,context,binding=fixture(card,i)
        action=instantiate_action(offered,context,[binding])
        negatives=hard_negatives(card)
        candidates=[encoded,*[capability(c,c["abilityPath"])for c in negatives.values()]]
        diagnostics=frozen_alignment(action,candidates,context["state"])
        before=context["state"]
        after=synthetic_transition(encoded,before)
        cards.append(dict(card=card["setCode"],provenance=encoded.provenance,
            feature_count=len(encoded.semantic_tokens),hard_negative_names=list(negatives),
            hard_negatives_all_known=all(v.known for v in candidates),
            diagnostics=diagnostics,synthetic_oracle=dict(
                scope="restricted synthetic nonlethal scalar/shield oracle; not Kessel execution",
                before=before,after=after,followup_affordance=synthetic_affordance(encoded,after))))
    return dict(schema="jepa-typed-ir-structural-wiring/1",source_commit=PINNED_KESSEL_COMMIT,
        cards=cards,optimizer_steps=0,learned_semantic_quality=None,
        elapsed_seconds=time.perf_counter()-started,
        interpretation="Identity-free typed path/count features and binding checks; positive program is injected by curated binding, so overlap is partly by construction.")


def native_binding_report(receipt):
    """Bind reviewed programs to exact recorded offers; labels come from snapshots.

    This is restricted to this experiment's two undeployed leaders and public
    scalar microstates. It does not deserialize arbitrary engine programs.
    """
    if receipt.get("schema")!="jepa-typed-ir-native-microprobe/1"or receipt.get("sourceRevision")!=PINNED_KESSEL_COMMIT:
        raise UnknownIR("unreviewed native receipt")
    def state_view(snapshot,target_id):
        players=snapshot["players"]; own=players["p1"]; source=own["leader"]
        for seat,p in players.items():
            for zone,cards in (("base",[p["base"]]),("ground",p["ground"]),("space",p["space"])):
                for card in cards:
                    if card["id"]==target_id:
                        return dict(ready_resources=sum(not c["exhausted"]for c in own["resources"]),
                            source=dict(owner="self",type="leader",exhausted=source["exhausted"],deployed=source["deployed"]),
                            chosen=dict(owner="self"if seat=="p1"else"opponent",type="base"if zone=="base"else"unit",
                                zone="base"if zone=="base"else"arena",arena=zone if zone!="base"else"ground",
                                hp=card["hp"],damage=card["damage"],shield=sum(c["setCode"]=="TOKEN_SHIELD"for c in card.get("upgrades",[]))))
        raise UnknownIR("chosen target absent from reviewed public zones")
    rows=[]
    for case in receipt["cases"]:
        card=next((c for c in REVIEWED_CARDS if c["setCode"]==case["card"]),None)
        if card is None or not RUNTIME_ADMISSION[card["setCode"]]["admitted"]or case["abilityPath"]!=card["abilityPath"]:
            raise UnknownIR("native card/program outside reviewed fixture subset")
        provenance=[p for p in receipt.get("provenance",[])if p["card"]==card["setCode"]]
        if(len(provenance)!=1 or provenance[0]["sourceHash"]!=card["sourceHash"]or
            provenance[0]["actualUnmodifiedAbility"]!=card["abilities"]["leader"][0]):
            raise UnknownIR("native selected-program source witness differs from reviewed template")
        before=case["before"]["state"]; prompt=case["targetPrompt"]
        offered=case["targetAction"]; target=offered["card"]
        source=before["players"]["p1"]["leader"]
        if (source["setCode"]!=card["setCode"]or prompt["decision"]!="AbilityTarget"or
            prompt["sourceInstance"]!=source["id"]or prompt["abilityProgramPlusOne"]<=0 or offered not in prompt["offeredActions"]):
            raise UnknownIR("actual offered source/program/target witness does not match")
        context=dict(source_instance=source["id"],source_card=card["setCode"],source_form="leader",
            chosen_instance=target,stage="abilityTarget",state=state_view(before,target))
        binding=CuratedBinding(source["id"],card["setCode"],tuple(card["abilityPath"]),"abilityTarget",offered,card)
        action=instantiate_action(offered,context,[binding])
        if not action.known: raise UnknownIR(action.reason)
        actual=state_view(case["after"]["state"],target)
        predicted=synthetic_transition(action,context["state"])
        players=before["players"]
        references={"own_base":players["p1"]["base"]["id"],"opponent_base":players["p2"]["base"]["id"]}
        for hp in (1,2):
            units=[c for zone in("ground","space")for c in players["p2"][zone]if c["hp"]-c["damage"]==hp]
            if len(units)!=1: raise UnknownIR("reference HP context is outside reviewed microfixture")
            references[f"opponent_unit_remaining_hp_{hp}"]=units[0]["id"]
        actual_targets={a["card"]for a in prompt["offeredActions"]if a["kind"]=="card"}
        # These labels are independently read from engine snapshots, not tokens.
        rows.append(dict(card=card["setCode"],binding_known=True,program_feature_count=len(action.semantic_tokens),
            observed=dict(ready_resource_delta=actual["ready_resources"]-context["state"]["ready_resources"],
                target_damage_delta=actual["chosen"]["damage"]-context["state"]["chosen"]["damage"],
                source_exhausted=actual["source"]["exhausted"],
                target_admissibility_mask={name:identity in actual_targets for name,identity in references.items()},
                followup_source_offered=any(a.get("card")==source["id"]for a in case["following"]["offeredActions"])),
            restricted_oracle_matches_observed_scalar_projection=predicted==actual,
            actual_offered_action=offered,stage="abilityTarget"))
    return dict(rows=rows,scope="Actual Kessel public microstates, two reviewed abilities; curated structural binding, not learned semantic quality.",
        behavioral_distance=dict(label_source="Actual offered-target masks and before/after snapshots, independent of typed features.",
            held_out_card_rank_correlation=None,held_out_card_retrieval=None,
            reason="Two cards/one pair cannot validate a distance metric or held-out-card ranking."))
