# Modal pricing and batch budget

Pricing checked **2026-10-17 UTC** against Modal's official documentation. This is a proposal and read-only account audit; it does not authorize a worker to launch compute.

Eric's **US$100 cumulative cap covers the entire JEPA experiment batch**, including failed runs, retries, image builds, startup/idle compute, storage and egress. The parent owns the budget and is the only spending authority. Hold **$25 as an unallocated margin**, leaving a **$75 operating ceiling** for actual gross usage plus outstanding reservations. Count usage before credits and allowances for conservative accounting. Workers have no independent spending allocation. No paid jobs have been launched for this batch; its current estimated Modal spend is **$0**. This does **not** assert that the account's total usage is zero.

The current tiny representation runs should remain on local CPU. A cloud probe becomes useful only after local held-out learning succeeds and profiling establishes a meaningful GPU or Linux/CUDA validation need.

Modal Function resource rates from the [official pricing page](https://modal.com/pricing):

| Resource | US dollars per second |
| --- | ---: |
| T4 GPU | 0.000164 |
| L4 GPU | 0.000222 |
| A10 GPU | 0.000306 |
| A100 80 GB GPU | 0.000694 |
| H100 SXM5 GPU | 0.001097 |
| CPU, per physical core | 0.0000131 |
| Host memory, per GiB | 0.00000222 |

CPU, host memory and GPU charges add together. A physical core corresponds to two vCPUs. Volumes cost $0.09/GiB-month beyond included storage (up to 1 TiB included). Egress is $0.04/GiB beyond the plan allowance. Sandbox/Notebook CPU and memory rates are higher: $0.00003942/core-second and $0.00000667/GiB-second. Prefer an ordinary Function for this batch; avoid region-selection and non-preemptible premiums. [Pricing](https://modal.com/pricing), [egress billing](https://modal.com/docs/guide/network-egress-billing).

Startup/application loading and post-input idle time are billable; the default idle tail is 60 seconds. There are no minimum usage-time increments. CPU and memory billing uses the greater of the request and actual consumption. CPU limits throttle rather than form a precise dollar cap; memory limits can terminate an overflowing container. Increased ephemeral-disk requests can raise the memory request at a 20:1 ratio. These are reasons to reserve margin rather than treat a nominal resource request as a hard invoice guarantee. [Pricing FAQ](https://modal.com/pricing), [billing units](https://modal.com/docs/guide/billing), [resource requests and limits](https://modal.com/docs/guide/resources).

If local evidence justifies a first cloud probe and the parent reserves its cost, use one fixed L4 Function and one invocation containing the matched arms sequentially. Keep the data, source and initialization hashes identical to the local run. Suggested bounds are one container, one input at a time, no warm pool/buffer, a five-second scaledown window, zero configured retries, `timeout=600`, `startup_timeout=120`, one requested/limited physical CPU core, and 8 GiB requested/hard-limited host RAM. Use a connected ephemeral App, no detach, schedule, web endpoint, GPU fallback list, persistent Volume or separately running worker. These are proposed settings, not an existing deployment. [Scaling controls](https://modal.com/docs/guide/scale), [timeouts](https://modal.com/docs/guide/timeouts), [ephemeral App lifecycle](https://modal.com/docs/guide/apps).

The proposed probe's arithmetic is deliberately conservative:

| Allowance | Gross estimate |
| --- | ---: |
| L4 + 1 physical core + 8 GiB RAM: $0.00025286/second, allowing 1,200 billed seconds | $0.303432 |
| Additional CPU-only image-build allowance: 300 seconds, 2 cores, 8 GiB | $0.013188 |
| Up to 100 MiB egress, ignoring any free allowance | $0.00390625 |
| Estimated envelope | **$0.32052625; round to $0.35** |
| Reservation before any launch | **$1.00** |

This is an estimate, not a platform-enforced $0.35 ceiling. The parent must reserve the full $1 before starting, including any build. If setup cannot fit the reviewed resource/time envelope, stop and revise the estimate. Return compact metrics and one small checkpoint directly; do not create persistent storage for this probe. No paid launch is currently recommended.

The root supervisor should impose a 1,200-second total wall-clock deadline across build, startup and execution, as well as the in-function step/time limits. Function timeouts are per attempt and exclude scheduling; they can overrun by several seconds. Therefore timeouts alone do not cap a batch. In `finally`, the parent should explicitly stop only the recorded experiment App ID with `modal app stop APP_ID --yes`, then verify that App is stopped and has no running containers. A connected ephemeral App also stops after the caller exits or disconnects. These shutdown actions are for a future parent-authorized run; none were performed by this audit. [Timeout semantics](https://modal.com/docs/guide/timeouts), [App lifecycle](https://modal.com/docs/guide/apps), [stop command](https://modal.com/docs/cli/latest/app).

Before each launch, the parent should record the reservation, source/data/checkpoint hashes, rates, resource limits, deadline and maximum artifact bytes in its cumulative batch ledger; append the App ID immediately when allocated. Do not admit another run when gross actual usage plus outstanding reservations and the new reservation exceeds $75; retain the $25 margin inside the absolute $100 cap. Platform monthly budgets can supplement this ledger, but they have different scope: Workspace budgets include account-wide usage, while Environment budgets exclude storage and egress. Do not change a shared Workspace budget without reviewing its other workloads. [Budget scope](https://modal.com/docs/guide/budgets).

Read-only account checks confirmed Modal CLI **1.4.3**, active profile/workspace **ericfode**, and a working billing-report API. Configuration existence/stat was inspected without printing credentials. The installed CLI supports `modal billing report --for today --resolution h --json`; it does not expose newer documentation's `billing summary`, `billing rates` or `--show-resources` commands. No CLI upgrade, credentials, Apps, jobs or storage were created. Unrelated workspace billing rows were withheld.

For realized cost, retain the reservation until billing data has arrived. Query complete hourly intervals with `modal billing report`, filter to the recorded App ID (and experiment tags where supported), and reconcile compute/build/egress costs with the Usage & Billing dashboard. Reports show gross amounts before credits, reservations and egress allowances; data usually arrives within minutes but may be delayed. Use live dashboard estimates while waiting, and do not interpret an absent early row as zero spend. Record estimated and reported costs separately. [Billing reports and lag](https://modal.com/docs/guide/billing), [network usage reporting](https://modal.com/docs/guide/network-egress-billing).
