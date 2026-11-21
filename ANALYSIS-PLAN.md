# ANALYSIS-PLAN — D1 full study: the disclosure effect in RCA
Written 2026-11-20 05:2x PST, before any full-study diagnoser run. Frozen: not edited after the first run starts. Any correction goes in ERRATA.md with reasons. The plan's SHA-256 is recorded in STEPLOG.md at freeze time.
Inputs fixed before this plan: `results/plan_full.json` (case set, A/B assignment, accept sets; SHA-256 `22b180ca55af7247a0561d3a2dfdb8924faaf4955de4cea510cb0395b012f993`), `results/leakage_audit.csv` (telemetry text only, no model outputs). No full-study outcome has been seen.

## 1. Question (decision for addendum item 5)
The question is **anchoring after disclosure**: when a truthful notice names one fault (A) of a known two-fault incident, does the diagnoser stop finding the other fault (B)? The prominent/subtle framing is **dropped as the research question**. Reason: in the pilot all three prominence-rule cases sat at the recall floor, and the effect came from rotated cases where B was as loud as A. A is therefore assigned by a fixed alternation rule (§3). A prominence split (A has more downstream services than B, from the label graph) is reported as an exploratory descriptive only.

## 2. Diagnosers
| id | model | vendor | role |
|---|---|---|---|
| S | claude-sonnet-5-5 via Claude Code CLI, headless | Anthropic | **lead diagnoser** (pre-set; it carried the pilot effect) |
| O | claude-opus-5-5 via Claude Code CLI, headless | Anthropic | second |
| X | OpenAI model chosen by the installed Codex CLI default (model id recorded from its run record), `codex exec` | OpenAI | non-Claude. Existing ChatGPT login, no new sign-up. |
S and O are the same vendor and are never presented as independent. Results are reported per diagnoser. Pooled values are a descriptive appendix only and never lead.

## 3. Cases, arms, repeats
- **Cases:** all 18 `n_required_faults == 2` cases in `anon-ops/ops-lite` (455 cases; the only released set found; `ops-lite-review-sample` is a sample under the same owner and was not treated as a larger release). Final set = 18, no extension. Sorted by (n_service_edges, name) → f01..f18. A = label fault index 0 at even positions, index 1 at odd positions; B is the other. Controls k01..k06 = the pilot's six single-fault cases.
- **Arms (hybrid):** i no notice; ii neutral notice; iii truthful notice naming A (service + kind); fix = iii + "A notice does not bound the set of causes." **Controls:** notice only (ctl_truth) and notice + "Search for a second, independent cause in addition to the disclosed one." (ctl_invite). Prompt text is the pilot's; only the notice line varies.
- **Repeats:** arm i = 2 **screen** runs (s1, s2) + 3 analysis runs (r1..r3). Arms ii, iii, fix, ctl_truth, ctl_invite = 3 runs (r1..r3). Per diagnoser: 18×14 + 6×6 = 288 sessions. Screen runs are never used to estimate any effect.
- **Bundle identity:** each run gets its own directory; all 10 parquet files hashed (SHA-256) before and after the session and compared with the source file hashes; per-case identity across all arms, repeats and diagnosers is tested. A run whose post-session hash differs is discarded and re-run.

## 4. Scoring (fixed before runs; addendum item 2)
- Named service = lower-cased `service` strings in the final JSON block.
- `accept(F)` = {F.service} ∪ label `also_accept` ∪ (for Network* faults) the `target_service` of the matching entry in `injection.json` (`engine_config_summary`/`engine_config`). This is the edge-level fix for the pilot's `rate`/`search` artefact.
- **Hidden-fault hit (primary)** = at least one named service ∈ accept(B). If accept(A) ∩ accept(B) ≠ ∅ (e.g. both faults on `ts-user-service`), the named fault_kind must also equal B's kind. **Strict variant (secondary):** kind must match for every case.
- **Disclosed-fault hit** is scored the same way against accept(A).
- **Spurious service** (replaces "fabricated"): a named service outside accept(A) ∪ accept(B) (controls: outside accept(A)). A named peer service inside an accept set is not spurious.
- An unparsable final answer is re-run once; if still unparsable it is scored as a miss and counted; a sensitivity analysis drops them.

## 5. Screening rule (addendum item 3; set in advance)
Per (case, diagnoser): **at-risk** if B is hit in ≥ 1 of the 2 arm-i **screen** runs; otherwise **floor**. Screen runs are excluded from every effect estimate, so the selection does not use the same data as the contrast.

## 6. Primary analysis
**Primary contrast (per diagnoser):** change in hidden-fault recall, arm iii minus arm i, **over the at-risk cases of that diagnoser**, from analysis runs only (r1..r3 in each arm). Per-case value = mean hit rate over its 3 arm-iii runs − mean over its 3 arm-i analysis runs; primary statistic = mean of per-case values.
**Interval:** two-level bootstrap, 10,000 resamples, seed 0, percentile 95%. Level 1 resamples at-risk cases with replacement; level 2 resamples the 3 repeats within each arm of each drawn case with replacement. This puts both incident variation and run-to-run noise in the interval.
**Sensitivity (reported, not primary):** (a) case-family cluster bootstrap (family = unordered pair of service:kind; 16 families among the 18 cases, two families hold two cases each); (b) strict kind scoring; (c) all 18 cases (no screening) per diagnoser; (d) floor-case stratum, shown separately.
**Claim thresholds (per diagnoser, from the primary CI):**
- *Effect supported:* CI upper bound < 0 and point estimate ≤ −0.10.
- *Null supported:* whole CI inside (−0.10, +0.10).
- *Otherwise inconclusive.*
No claim is made about "responders in general" unless a non-Claude diagnoser also meets "effect supported". If only Claude models do, the claim is stated as Claude-family only. The claim published is whatever this table gives, including null or Sonnet-only.
**Kill / report-as-pilot-extension:** if the primary CI for the lead diagnoser (S) has half-width > 0.20, the study is reported as a pilot extension, stated plainly. The all-case interval is reported next to it but does not rescue it.

## 7. Secondary analyses (all per diagnoser; descriptive CIs from the same bootstrap)
1. ii vs i (neutral notice), at-risk set. 2. fix vs iii and fix vs i, at-risk set. 3. Arm-i baseline recall of A and B per case (conditioning table, addendum item 1). 4. Disclosed-fault recall per arm. 5. Tool-call counts per arm (anchoring-mechanism descriptive; transcripts are not read for mechanism). 6. Controls: rate of any spurious service, and of a named second cause, per arm, with Wilson 95% intervals. 7. Prominence split (§1) as an exploratory table. 8. Pooled-over-diagnosers figures, appendix only.
No other contrasts are computed for the headline. Anything added after seeing data is labelled post-hoc.

## 8. Leakage audit (binding condition 5)
Audit run on telemetry text only before this plan: all string columns of every logs file, all traces string columns (excluding ids) and metric names/labels, plus parquet file metadata, for the 18 hybrid and 6 control cases. Patterns: strong = injection-tool names (chaos-mesh, chaosd, \*chaos CRD kinds, litmus, toxiproxy, stress-ng, byteman, "fault inject", bare "chaos", etc.); weak = fault-kind names and "inject". **Rule:** any case with ≥ 1 strong hit is excluded from the primary analysis and reported in the all-case sensitivity; weak hits are flagged only. Result and per-case table are in FULL-REPORT. Run-level rule: a run whose tool calls read answer-key files or the dataset/project paths is excluded and re-run.

## 9. Isolation (addendum item 4)
One directory per run under `/tmp/d1full/<run id>/` (unique per case, arm, diagnoser, repeat), bundle copied, hashed before and after, deleted after the post-hash (disk is tight). Tool-call scan per run for paths outside the run directory and for answer-key names. After each round a scan of `/tmp` and `~` (new files since round start, excluding harness paths) is saved under `results/leak_scans/`. Codex runs use a minimal `CODEX_HOME` (no user instructions, plugins or MCP servers) and `workspace-write` sandbox with the run directory as the workspace; Claude runs use `--setting-sources ''`, no MCP, no memory.

## 10. Budget and ordering (binding condition 7)
Hard cap USD 120 of diagnoser run cost. Claude cost is read from each run's `total_cost_usd`. Codex runs under a ChatGPT login report tokens, not dollars; they are recorded in tokens and are **not priced** in the ledger (stated as such). Projection at pilot rates (~$0.14/run): 576 Claude sessions ≈ $81. Execution order is rounds: screen runs, then r1 for every cell, then r2, then r3, so any early stop leaves a balanced design. A cost check runs after each round and a hard stop at $115 cumulative. If the projection passes the cap, repeats are reduced before cases (never below 3 analysis runs per arm; screens dropped first), and the change is written to ERRATA.md.

## 11. What would count as a deviation
Any change to §§3-6 after the first run. Fixing a harness fault (race, hash mismatch) with a re-run of the same cell is not a deviation but is logged in STEPLOG.md with the discarded record kept.
