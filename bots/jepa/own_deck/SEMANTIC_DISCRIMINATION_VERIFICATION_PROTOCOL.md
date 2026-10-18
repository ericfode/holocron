# Saved-output verification repair

The native collection, preparation, matched learner and baselines completed
under source freeze `fea073737d9b7564278f752cb4dcb9a65023ef14`: 33 roots,
67 successful native applications, 3,000 optimizer updates, 3,045 forwards and
16 fixed ridge head fits. The official counters are known and remain unchanged.

Verification failed before writing a result. It incorrectly required the
allowlisted public feature record to equal the complete native capture. It
also attempted to reconstruct the legacy 18/34 inputs from that stripped record,
although those inputs were correctly constructed from the original capture.
The public C1R1 extension intentionally consumes only the stripped allowlist.

The original failed verifier and its five-second charge remain intact. The
closed journal is SHA256
`38aec9744526ed6483aa870df59ddf4fac0c04bc71d419f0810f44e1c671f83c`,
220,276 bytes, final chain
`31f0c00536f47077d17f7b2865aa503892513ffd9f5165aff951279a71491755`.
The linked campaign carries **275 charged applications and
214.23341095773503 charged seconds**. Historical aggregate observed applications
remain unknown; the newly observed 67 applications and 3,045 forwards are known.

The versioned verifier independently reconstructs the exact public allowlist
from the raw BEFORE capture and compares it to the consumed record. It derives
legacy 18/34 features from raw BEFORE and the C/R extension from the allowlist,
then compares both with the saved actual inputs. It changes no feature, label,
mask, split, model, prediction, score, threshold or gate. Synthetic tests cover
the distinction and reject added menus/private fields and changed public data.

A separate journal under experiments/semantic-discrimination-verification-v1
permits **one five-second saved-output verification only**, zero native calls,
neural forwards, optimizer updates, numerical fits, exports or paid jobs.
Its cumulative ceiling is 275 applications and 219.23341095773503 seconds.
It uses the old campaign only for read-only pins, counters and closed state.
New accounting reserves before verification, forbids retry/overwrite, charges
the full five seconds on failure, and checks the closed evidence before/after.
No old journal is reopened and no completed stage is rerun.

The financial ceiling/reserve remain $100/$25. Production, engine/card sources,
original workspaces and dashboard pointer remain unchanged. Verification checks
are engineering evidence, not independent semantic samples. Regardless of the
result, only two held card programs were tested and `semantic_validated=false`.
