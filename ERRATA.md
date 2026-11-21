# ERRATA — D1 full study
Corrections to ANALYSIS-PLAN.md. The plan itself is not edited. Each entry says when it was made relative to the first full-study run.

## E1 — Codex diagnoser model pinned (20 Nov 2026, before any full-study run)
Plan §2 said the Codex model would be "chosen by the installed Codex CLI default (model id recorded from its run record)". Codex's JSON event stream does not report the model, and no `model` key is set in the user's Codex config, so the default could not be recorded. Fix: pin `-m gpt-6.2-sol`, the priority-1 listed, API-supported entry in `codex debug models`. Unverified: that this equals the unpinned default. Smoke runs (8 per vendor-arm set, f01, results/smoke/) ran before the pin and are excluded from analysis.

## E2 — Codex error rule fixed in analyze_full.py (20 Nov 2026, evening; harness fix under plan §11)
Defect (found by the Fable vetting, A4): the analyser set Codex `err = not bool(last agent message)`. Eleven Codex records cut off mid-run by the usage limit carried an interim progress message, so they were stored and counted as valid (merely unparsed). True Codex completeness was 263/288, not 274/288. Fix: a Codex record with a `turn.failed` event, or with no `turn.completed` event, is a failure (err=1) regardless of message text. Checked on the 11 records: all err=1. The 11 files were moved to results/failed_X_cutoff/ (kept) so run_full.py would not skip them. No scoring rule changed. sha256 of analyze_full.py after both E2 and E3 edits is in STEPLOG.

## E3 — Accept-set overlay for controls k05 and k06 (20 Nov 2026, evening)
Defect (vetting A3): the edge fix (peer `target_service` in accept(A)) was applied to hybrids from `injection.json` `engine_config_summary`, but k05 and k06 have none; the peer is in `display_config.injection_point.target_service`. Verified in data/cases: k05 ts-train-service, k06 ts-order-other-service. plan_full.json is hashed and is not edited. Overlay: analyze_full.py adds these services to accept(A) for k05 and k06 at load time (dict OVERLAY). Effect: a run naming the far end of the disclosed edge is no longer scored spurious. No other case touched.
