# PILOT-REPORT: disclosure effect in RCA, paired replay on OpenRCA 2.0 (revised D1)
Date: 19 Nov 2026. Local files only; nothing posted, pushed or transmitted.

## Summary
- **Replay works.** The released hybrid cases carry usable telemetry (10 parquet files each). All 18 cases (12 hybrid, 6 single-fault) replayed, and every bundle verified byte-identical across arms (SHA-256, and equal to the source file). KILL conditions not triggered.
- **Primary result: the disclosure effect is negative.** Naming fault A (arm iii) *lowered* recall of the undisclosed fault B vs no notice (arm i): pooled mean change **-0.25** (bootstrap 95% CI -0.375 to -0.125) over 12 incidents; 0 incidents up, 6 down, 6 unchanged. By diagnoser: Sonnet 5.5 -0.42 (CI -0.67 to -0.17; B recalled in 5/12 arm-i runs, 0/12 arm-iii runs), Opus 5.5 -0.08 (CI -0.25 to 0.0; 1 down, 11 unchanged).
- **Neutral notice (ii): no detectable effect** (+0.04, CI -0.08 to 0.17).
- **Prompt-fix arm** ("a notice does not bound the set of causes") recovers part of the loss: fix vs iii +0.125 (CI 0.0 to 0.25); fix vs i still -0.125 (CI -0.25 to 0.0). B recall pooled: i 10/24, ii 11/24, iii 4/24, fix 7/24. It does not fully remove the effect.
- **False positives are low** and do not rise in the fix arm (fabricated extra services: i 6, ii 5, iii 3, fix 4 of 24 runs each). On single-fault controls, a truthful notice alone produced 0/12 fabricated second causes; adding an invitation to search for a second cause produced 3/12 (Sonnet 1/6, Opus 2/6).
- **Caveat that matters:** n=12 incidents, one run per cell per diagnoser, both diagnosers are Claude models, and 5 of 12 incidents never recover B in any arm. Pilot-scale evidence only.

## Pass/kill against the pre-set bars (Muse adjudicates)
| Bar | Status |
|---|---|
| Cases replay with bundles verified identical across arms | Met. 18/18 cases, 1 distinct hash set each, all equal to source. See `results/bundle_identity.csv`. |
| Pipeline runs unattended | Met with one exception: the run was unattended, but I found and fixed a race (below) afterwards and re-ran 3 runs. |
| Primary effect estimated with a CI | Met. See above. |
| KILL: hybrid cases lack usable telemetry | Not triggered. |
| KILL: notice arms cannot be kept telemetry-identical | Not triggered; the notice is the only variable in the prompt. |

## Case selection and difficulty spread
Source: `anon-ops/ops-lite` (Hugging Face, public, Apache-2.0; 455 cases), manifest and per-case files read directly. Paper read: arXiv 2606.27154 (§3.3 quote in the brief checked against the HTML text).
- **Hybrid definition (mine, operational):** `n_required_faults == 2` in the manifest (two faults that both took effect). 18 such cases exist (12 hs, 6 ts; none in otel-demo). The dataset does not label cases "hybrid" with a prominent/subtle split; the prominent/subtle framing is the paper's description, not a released field. **Unverified** that these 18 are the paper's "hybrid" injections.
- **Difficulty signal: not available.** The brief asks for the paper's per-case fraction of models clearing F1>0. The released manifest and case files contain no such field (manifest keys: name, system, root_services, optional_services, chaos_types, n_injected_faults, n_required_faults, process_applicable, n_service_edges, longest_service_path). I used a structural proxy instead: sorted the 18 by (n_service_edges, name) and took 12 evenly spaced by index (fixed rule, set before any run, no outcome used). Spread: n_service_edges 2 to 23, longest path 1 to 3; 9 hs and 3 ts cases. The proxy is not validated against model difficulty.
- **Disclosed fault A:** if the two faults differ in type and downstream reach, A is the one with more downstream services in the label's service graph ("prominent"); otherwise A alternates (rotation). 4 cases used the prominence rule, 8 rotated. This uses the label file for planning only; the diagnosers never saw it.
- **Controls:** 6 single-fault cases (`n_injected_faults == 1`), the first two by name per system (hs, otel-demo, ts).
- Plan with all choices: `results/plan.json` (cids c01-c12 hybrid, c13-c18 control). Cases c07: both faults are on the same service (JVMLatency + DNSError), so hidden recall there requires the right fault kind.

| cid | system | edges | A (disclosed) | B (hidden) |
|---|---|---|---|---|
| c01 | hs | 2 | profile PodFailure | recommendation PodFailure |
| c02 | hs | 2 | attractions MemoryStress | user PodFailure |
| c03 | hs | 2 | user PodFailure | attractions MemoryStress |
| c04 | hs | 3 | geo PodFailure | profile PodFailure |
| c05 | hs | 3 | search NetworkDelay | recommendation PodFailure |
| c06 | hs | 3 | recommendation PodFailure | search NetworkDelay |
| c07 | ts | 3 | ts-user-service JVMLatency | ts-user-service DNSError |
| c08 | hs | 3 | profile PodFailure | search NetworkPartition |
| c09 | hs | 3 | geo PodFailure | reservation MemoryStress |
| c10 | ts | 4 | ts-route-service NetworkPartition | ts-admin-route-service JVMLatency |
| c11 | ts | 5 | ts-route-plan-service JVMLatency | ts-travel2-service NetworkLoss |
| c12 | ts | 23 | ts-route-service NetworkCorrupt | ts-admin-route-service JVMLatency |

## Bundle-identity check
Each run gets its own directory with the 10 parquet files copied from the dataset (no `env.json`, `injection.json`, `label.json`, `causal_graph.json`). Each file is SHA-256 hashed at copy time and stored in the raw run record. Analysis compares: (a) all arms/diagnosers per case have one identical hash set, (b) every hash equals the hash of the downloaded source file. Result: 18/18 cases, 1 hash set each, all match source (`results/bundle_identity.csv`).
**Defect found and fixed:** in the first pass the two diagnosers shared one directory per (case, arm) and copied concurrently; the check caught empty-file hashes in 3 c01 runs (race). I discarded those 3 runs (`results/raw_superseded/`), gave each diagnoser its own directory and re-ran them. The re-ran runs are fresh samples of the same cell (non-deterministic), not replays of the discarded ones. The discarded runs' outcomes were not used.

## Method
- Diagnosers: `claude-sonnet-5-5` and `claude-opus-5-5` (model names as reported in each run's usage record), Claude Code CLI 2.1.300, headless (`-p`), fresh session per arm per incident, no user/project settings, no MCP, no memory, no skills. Tools: Bash, Read, Glob, Grep. Same prompt except the notice line. Same budget: "at most 40 shell commands" in the prompt and a $3 cap per run; none hit it (mean tool calls per run 3 to 10).
- Both diagnosers are the same vendor family. "2 LLM agents" is met, but this is weaker independence than two vendors.
- Prompt notice text: (ii) "A planned maintenance/experiment window was in effect during this incident." (iii) "A planned experiment injected <kind> into <service> during this window." fix = (iii) + "A notice does not bound the set of causes." Control variant = (iii) + "Search for a second, independent cause in addition to the disclosed one." Full prompt stored per run in `results/raw/*.json`.
- Scoring: answer parsed from the final JSON block (120/120 parsed). Hidden-fault hit = B's service (or its `also_accept`) named; where A and B share a service (c07) the fault kind must also match. A strict variant requires the fault kind to match for every case. Fabricated = a named service outside the two injected services (hybrid) or outside the sole injected service (controls). Bootstrap: 10,000 resamples of incidents, seed 0; pooled value = mean of the two diagnosers per incident.
- Leak check: scanned all tool calls for references to answer-key files, the dataset path or project folder: 0 hits. The agents could technically run shell commands outside their directory; none did.
- Cost: about $16.9 for the 120 reported runs (plus a smoke test and 3 discarded runs).

## Results
### Primary: change in hidden-fault recall, arm iii minus arm i (per incident, B recalled 0/1 per diagnoser, pooled = average)
| diagnoser | n | mean change | 95% CI | up / down / same |
|---|---|---|---|---|
| pooled | 12 | -0.250 | -0.375 to -0.125 | 0 / 6 / 6 |
| Sonnet 5.5 | 12 | -0.417 | -0.667 to -0.167 | 0 / 5 / 7 |
| Opus 5.5 | 12 | -0.083 | -0.250 to 0.000 | 0 / 1 / 11 |
| pooled, strict (kind must match) | 12 | -0.167 | -0.292 to -0.042 | 0 / 4 / 8 |

The CI resamples incidents only; run-to-run sampling noise within a cell is not captured (one run per cell). With 12 incidents the interval is wide and the bootstrap is approximate.

### Hidden-fault recall counts by arm (runs where B was named)
| arm | pooled (of 24) | Sonnet (of 12) | Opus (of 12) | disclosed fault A named (pooled) |
|---|---|---|---|---|
| i no notice | 10 | 5 | 5 | 20 |
| ii neutral | 11 | 6 | 5 | 19 |
| iii truthful, names A | 4 | 0 | 4 | 24 |
| fix | 7 | 3 | 4 | 24 |

### Secondary
| contrast | mean change | 95% CI | up/down/same |
|---|---|---|---|
| ii vs i | +0.042 | -0.083 to 0.167 | 2 / 1 / 9 |
| fix vs i | -0.125 | -0.250 to 0.000 | 0 / 3 / 9 |
| fix vs iii | +0.125 | 0.000 to 0.250 | 3 / 0 / 9 |

Fabricated extra services on hybrid cases (runs with at least one, of 24): i 6, ii 5, iii 3, fix 4. Prompt-fix false-positive cost relative to iii: +1 run of 24; relative to i: -2. No false-positive penalty visible, though the counts are tiny.

Single-fault controls (6 cases x 2 diagnosers = 12 runs per arm): truthful notice only: 0/12 fabricated second causes. Notice + invitation to look for a second cause: 3/12 (Sonnet 1, Opus 2). The disclosed fault was named in 12/12 runs in both arms.

### Reading
- The pattern in arm iii is anchoring on the disclosed fault: A named 24/24, B named 4/24, with shorter investigations (mean 3.5 tool calls vs 5.2 in arm i). This is a descriptive observation from tool-call counts; I did not read transcripts for mechanism.
- Arm i itself recalls B only 10/24, so the baseline leaves room both ways, but the observed direction is only downward.
- The effect is mostly Sonnet. Opus barely moves. A full study should not pool them blindly.
- A one-line prompt change recovers about half of the loss but not all of it (fix vs i CI touches 0). Whether that counts as "weak" is for Muse; the data says partial, at no visible false-positive cost, at n=12.

## Limits (not hidden)
1. n=12 incidents, one run per cell. 5 of 12 incidents (c07, c08, c09, c10, c12) never recover B in any arm for either diagnoser, so they cannot show an effect. The primary effect comes from c01-c05 and c11 (see `results/per_incident_arm.csv`).
2. Difficulty proxy is structural, not the paper's. Hybrid = two required faults; prominent/subtle split is my downstream-reach rule, applied to 4 cases.
3. Same-vendor diagnosers. Non-deterministic sampling; no repeats.
4. Telemetry contains Kubernetes event text in logs in some cases (c01 transcript cited k8s events). Dataset notes that injection-tool log lines were removed; I did not audit the logs for other leakage.
5. The three re-run cells (c01 ii-Opus, c01 iii-Opus, c01 iii-Sonnet) replaced discarded runs.

## Files
`results/per_run.csv` (one row per run: answers, hits, cost, tool calls), `results/per_incident_arm.csv`, `results/bundle_identity.csv`, `results/summary.json`, `results/plan.json`, `results/raw/*.json` (full prompt, hashes, stream output), `results/raw_superseded/`, `work/` (scripts: `build_plan.py`, `run_pilot.py`, `run_pilot2.py`, `analyze.py`), `data/` (downloaded dataset subset, 102 MB).

## Completion note
- **Did:** downloaded 27 cases, built plan, ran 120 diagnoser sessions (2 models x 60), verified bundles, scored, bootstrapped CIs.
- **Found:** disclosure of A reduced recall of B (pooled -0.25, CI -0.375 to -0.125), driven mainly by Sonnet; neutral notice no effect; prompt fix partly recovers it; low false-positive rates.
- **Blocked / unavailable:** the paper's per-case difficulty signal is not in the released data; used a structural proxy. Hybrid label is my operational definition.
- Nothing posted, pushed or transmitted. Dataset and paper were downloaded only.
