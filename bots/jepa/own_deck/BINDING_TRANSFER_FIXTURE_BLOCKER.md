# Fixture chronology blocker

The frozen binding-transfer collection failed before its first engine apply.
No learned ablation, baseline fit, dataset conversion or new semantic result
was produced. The failed native reservation remains charged at 48 calls; the
linked cumulative native ceiling of 160 is consumed. No retry is authorized.

The first planned LAW_045 world attaches ASH_066 and then LOF_215 to SEC_028
(`binding_transfer_native_collector/collection-plan.json`, helpers.victim_upgrades;
the first world starts at line 1064). Frozen `src/main.rs:111–114` prepends each
upgrade to the linked attachment list while appending it to registration order.
Thus registration records ASH_066 then LOF_215, but the physical list traverses
LOF_215 then ASH_066. `run_case` calls `Engine::load_state(snapshot)` at line 163,
before reaching `Budget::apply` at line 183.

Pinned Kessel c7ee39554901278cee70f61fd8b26fb1920696b3 requires those orders to
agree (`crates/kessel/src/registration_runtime.rs:71–90`). Its native attachment
operation appends to the linked-list tail and registration order
(`crates/kessel/src/simulator.rs:304–313`). This explains the captured error:
`registrationOrder conflicts with physical attachment chronology`.

Evidence under `experiments/binding-transfer-v1/native-attempt-1/`:

- `stderr.log`: 75 bytes, SHA256
  `adc3916fa5c31e0c91d7eeac9fcb9daf54838299de6a46adcc5e5f11eac6533a`.
- `native-transitions.jsonl`: exactly one complete header, 408 bytes, SHA256
  `f2351c7a0f9220e71168b5782c24c9935a0079b89dbd6ef5abc3eab5f2674a16`.
  It contains no beforeApply, afterApply, applyError or contextComplete record.
- `native-receipt.json` is absent. The supervisor reports verified observed
  native applies 0 and failed charged native applies 48. The authoritative
  ledger finish separately charges 30 seconds for this failed native stage;
  supervisor charged_seconds is the cumulative campaign value.

Zero actual applies is supported by the saved journal and frozen control flow:
the only `e.apply` is at `src/main.rs:155`, immediately after the fsynced
beforeApply record at line 154. Fixture roundtrip validation at line 163 failed
before that code was reached. This observation does not credit back the failed
reservation or relax any cap.

`binding_transfer_fixture_chronology.patch` is an **unapplied proposal for a
future explicitly allocated cycle**. It changes only the collector fixture
helper to append ordinary upgrades in native chronological order, checks an
existing chain for invalid IDs/cycles/foreign parents, and propagates fixture
errors. It does not modify the engine, frozen plan, catalogue, scientific labels
or accounting. It has not been compiled, applied or executed. The frozen Rust
source remains SHA256
`e8e698a9d1de4de90670c782076afb0f94e9816162dcd7351569394c836f5429`.

A future preflight should check a two-upgrade chain and registration projection
agree before any native apply, retaining the existing exact snapshot/load gate.
This is a fixture correction, not evidence about representation or transfer.
