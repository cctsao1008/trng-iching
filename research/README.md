# Research index

Single entry point for [Issue #6](https://github.com/cctsao1008/trng-iching/issues/6). Read this before opening individual scripts or searching the entire issue history. Inventory: 37 retained tools/documents organized into nine semantic packages/directories, excluding this index, migration manifest and archive. Snapshot: 2026-11-28. Historical baseline commit `ff3cd1c1c9a8bc8cda0ad4ad353b24b8246b5f69`.

## Directory structure and historical aliases

| Directory | Purpose | Historical aliases |
|---|---|---|
| `common/` | Shared capture validation and transport | PH-BT capture helpers |
| `physical_model/` | Cross-domain reference, time, uncertainty and qualification | PH-BT |
| `tidal_gravity/` | Direct Sun/Moon tidal forcing and response diagnostics | M01 |
| `ocean_tide/` | Water level and tide prediction | D12 |
| `geomagnetism/` | Ground magnetic field | D06 |
| `cosmic_ray/` | Neutron-monitor corrected rate | D26 |
| `solar_wind/` | Magnetic field and plasma | D03 / D02 |
| `planetary_motion/` | Planetary and lunar geometry | COSM astronomical candidates |
| `classical_mapping/` | Classical sources and symbolic semantics | COSM |
| `archive/` | Immutable retired tools | Historical names retained |

See [migration.json](migration.json) for every old path, new path, and both Git blob IDs. Historical source/domain IDs, result names, SHA256 pins and issue links remain unchanged. Use meaningful names for new code; do not rename pinned provider data or results. Use Git commits for versioning.

## Research convergence and stopping rules (2026-11-28)

The goal is a meaningful, reproducible observation-to-symbol research framework, not unlimited precision testing. Research prioritization below is a working recommendation, not source qualification, production approval or a frozen model.

- **Stop routine tidal-gravity refinement.** Direct geometric rigid radial Sun/Moon forcing is the retained research estimand. Numerical replay, alternative ephemeris, projection, conditional GM, elastic-response and frame-implementation diagnostics are sufficient for this exploratory stage. Reopen external EOP/Horizons and calibrated uncertainty only if this candidate is selected for formal qualification, or a concrete discrepancy could alter its intended use. Elastic gravity response is a separate estimand, not another required refinement of direct forcing.
- **Planetary motion bounded feasibility completed.** Owner export received, pinned replay passed; apparent geocentric motion retained as a slow-changing astronomical context candidate, not a replacement for current short-cadence MPH. No extra precision tests or new acquisition absent a concrete design decision. Sixth channel, encoder and ordering remain provisional.
- **Keep the six-domain physical model as a separate exploratory track.** Rechecked stored comparison result SHA256 `96594e3f9a98c6171ec889d564552917d79cf6976614d05caf20ae1a33ba02c3`. On inspected BT-B, sweep-midpoint P1, 30/60-minute nominal joint-resolved counts for fixed reference B and mixed D0 are 32/11; prior-six-hour C gives 2/0; illustrative guard D_guard gives 0/0. There are 47/23 possible within-day adjacent pairs. These are alternative diagnostic assumptions, not independent tests, and the guard is not calibrated. Reference/support/quality differences, not more tidal arithmetic, are the current integration bottlenecks. Do not select a candidate by code yield.
- **External blockers stay blocked:** provider QC/calibration/rights/as-of and missing artifacts. Do not manufacture proxy data, repeat captures, or start parallel refinements merely to fill a task list. Proceed to formal validation only after choosing an estimand and defining its acceptance criteria; retain BT-C sealed.
- **Completion rule:** one bounded check per concrete decision; reuse an existing tool/result whenever sufficient. A new experiment must state which decision it can change and what result ends the experiment. Stop if it cannot materially affect the decision. Prefer updating this index and Issue #6 over creating new documents or scripts.

### Completed decision: planetary motion semantics and cadence

Bounded analysis completed on the existing owner JSON; protocol retained below for reproducibility. See [#7239859530](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7239859530). No new acquisition, script or ephemeris refinement required.

1. Use `planetary_motion/vector_replay.py` with the pinned owner SHA256. Stop on identity/replay failure; report rather than silently repin.
2. Use the already exported vectors at the existing 6/30/60/360-minute intervals and fixed triples. For the five targets, compare apparent versus geometric signed interval rates and second differences at matched endpoints, and compute the joint intersection of resolved rate/change signs across all five under the existing hypothetical endpoint-error scenarios. Report any sign disagreement and the corresponding physical quantity; do not rank by hexagram yield. Apparent geocentric motion is the primary observational candidate because it describes motion as seen from Earth; geometric motion is a control, not a silent replacement.
3. Distinguish the meaning of a moving line before choosing a mapping: existing R-Trend denotes reversal of successive increments; state-transition on signed angular rate denotes a change from direct to retrograde motion or vice versa; rate/change (J-S) denotes opposition of rate and its change, i.e. slowing in the current direction, not necessarily a reversal. Zero/unresolved signs remain unresolved. The latter two are research alternatives, not changes to existing MPH.
4. Stop after comparing cadence suitability, the meaning of the observable and uncertainty sensitivity. If rates are resolved but rate changes are not, report that limitation rather than forcing a moving-line assignment or selecting the longest interval automatically. No calibrated uncertainty or generalization is established by the inspected dates; no new model is frozen.

Concrete example from the existing verified lunar geometry result (SHA256 `9261f9af7c79dc64e0f55d86ca8479a1c8d7ad8b725673bfd6f2922b72df73eb`): using 30-minute point-sample means and half illumination as reference, both inspected days have all 48 negative residual states. On Sep 14 all 47 adjacent increments are positive, so J-S reports 47 oppositions but state-transition reports zero crossings. On Sep 7 all 47 increments are negative and both opposition and crossing counts are zero. This difference is semantics, not a numerical error, and does not establish a preferable encoder. Apply the same distinction to planetary motion before assigning any line codes. No individual cast or personal question is needed as research evidence.

**Result and stopping decision.** Owner input pin matched. 480 epochs, 4800 vectors, 80 summaries and 320 scenario reports replayed, zero disagreements/near-boundary cases. Both dates show four direct planets and retrograde Saturn; all five negative second differences. Apparent/geometric signs identical across 1540 matched target triples. No nominal reversals; J-S opposition four of five at every triple. Joint rate+change counts at h=6/30/60/360min: nominal 238/46/22/2, hypothetical 0.001 arcsec endpoint bounds 0/0/22/2, 0.1 and 1 arcsec all zero. At 0.1 arcsec current-rate signs alone remain fully resolved. This is not actual calibrated uncertainty. The two dates show one joint nominal sign pattern, not a claim of long-term constancy. Keep apparent motion as slow context, not a short-cadence MPH substitute. No time interval, sixth channel or order selected; no model freeze. Further arithmetic is not required. Evidence: [#7239859530](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7239859530).

**Architecture convergence.** The [working architecture decision](classical_mapping/candidate_architecture.md#working-architecture-decision--2026-11-28) separates context, evidence, encoding and reflection. Static production-path inspection confirms an existing post-assembly reference-context boundary. Preserve existing R-Trend and line positions for MPH; Wood remains a financial demo, not a qualified natural phase. No sixth astronomical channel is needed if planetary motion is context only. No live natural-observation profile, threshold or order approved. Owner has now approved Physical Hexagram completion as the active priority. Follow the P3 convergence checkpoint; no additional routine exploratory refinement.

**P3 source/contract desk review (2026-11-28).** [Review and draft observation/uncertainty contract](physical_model/qualification.md#p3-source-eligibility-and-observation-contract-review--2026-11-28): official source-use policy evidence narrowed (especially Oulu noncommercial scope, NAIF kernel terms, USGS R0 and CO-OPS flags); difference-specific bounds and fixed UTC support proposed. Product-specific QC, support, latency, error bounds and intended-use scope remain open. #3 partial and #4 MTS pending evidence explicitly dispositioned. No requests sent, no qualification change, no BT-C access. Stop further routine desk review until a concrete evidence question can be resolved.

**P3 native measurement-support check (2026-11-28).** [Phase-aware support and minimum provider questions](physical_model/qualification.md#p3-measurement-support-closure-boundary--2026-11-28): CO-OPS December 2025 sensor spec distinguishes centered radar/acoustic support; ideal radar full-cover phase is +180s, not unshifted UTC half-hour, and acoustic has gaps. Bounded synthetic geometry only; common phase, actual station channel and source-specific uncertainty remain unapproved. Provider-ready questions recorded, unsent; no routine recapture or new independent evidence.

**P3 engineering boundary and outreach preparation (2026-11-28).** [Gate review, synthetic bound check and three provider drafts](physical_model/qualification.md#p3-engineering-gate-review-and-provider-outreach-preparation--2026-11-28); [two solar drafts](solar_wind/provider_questions.md#p3-outreach-ready-drafts--2026-11-28-unsent). Existing P2 synthetic interface and R-Trend preserved. 3375/3375 synthetic corner-oracle cases agree; no actual-source bounds or Python integration tested. Five provider requests prepared, unsent; owner review and external evidence remain critical path. No BT-C access or readiness change.

**P3 remaining decision boundary (2026-11-28).** [Model-versus-observation scope, M01 official source/rights evidence and outreach decision](physical_model/qualification.md#p3-remaining-decision-boundary--2026-11-28). M01 replay complete within numerical scope; official kernel MD5 published but local bytes not rechecked. Owner scope/outreach authorization and actual product evidence are next; stop routine research commits. No mail sent or qualification change.

**P3 provider outreach (2026-11-28).** [Five inquiries SENT; response pending](physical_model/qualification.md#p3-provider-outreach-sent--2026-11-28). Initial independent noncommercial research scope adopted; derived-only public use still subject to terms. Prior UNSENT entries are historical. No provider approval, qualification change, BT-C access or production change; wait for substantive evidence rather than repeat research.

**Owner-directed experimental implementation.** The previous wait-for-provider prerequisite no longer applies to experimental local casting. Existing public sources, native-label means and R-Trend are used; no new precision study or archival reconstruction. Formal scientific qualification and commercial/public redistribution approval remain separate. See the main README. Physical v0.2 owner live smoke PASS (2026-11-28); P5 three-method live smoke PASS (2026-11-29 Taiwan time). Experimental CLI integration complete; next priority is MPH source/release improvements.

**MPH Wood next stage — owner-approved TWSE + TAIFEX.** Replace the EODHD VTI demo only after the new adapter is verified. Use TWSE TAIEX Total Return Index (government dataset 11871) as the cash-market baseline and TAIFEX TX (dataset 11319) as an additional after-hours observation. Candidate overnight synthetic level = cash total-return index × same-contract night last trade / regular-session last trade. Use completed sessions only; no roll-spread mixing, double-counting, arbitrary cross-market weights, API keys, accounts, automatic fallback, or persistent collection. Night trading-date attribution must be mapped to the actual session start/end, including weekends. Select the latest three chronological eligible observation levels under a fixed schedule, keeping prior cash and associated completed night observations distinct; reject missing expected observations rather than choosing based on their values. On a new cash close, reset to the observed cash index. This is a synthetic market proxy, not a reported TWSE index or prediction. R-Trend and other five lines remain unchanged. Owner cross-month TWSE and TAIFEX dated regular/night probes passed. Live adapter implemented in 10ab541; contract v0.3. Owner Windows end-to-end smoke PASS on 2026-11-29 00:24:03 UTC+8 (baseline 72393f8): TWSE 20 rows, TAIFEX 30 rows, five domains resolved, one QRNG request, complete assembly and Human View. Weekend night attribution and the expected Wood R-Trend line matched the prior manual calculation. Audit-mode, exceptional closures, month/contract rollover and sustained availability are not yet live-verified. No EODHD fallback; legacy saved-record source identity retained. Calendar uses XTAI as a schedule proxy; exceptional closures and publication delays can produce no hexagram.

**Shared runtime diagnostics:** Windows/urllib transport failures now carry a safe code (`http_error`, `request_timeout`, `connection_failed`, or `invalid_response`); HTTP status and Wood component identity are surfaced in no-hexagram outcomes when known. Wood logs per-request latency, payload size and missing session/contract details. Existing acquisition counts, source selection, no-retry/no-fallback policy, observation schedules, R-Trend and exit-status behavior remain unchanged. Static diff verified; owner Windows compile and three-method happy-path live regression PASS (2026-11-29 00:28 UTC+8, baseline ead7824). MPH five domains resolved; six HTTP requests including QRNG succeeded; TWSE 0.295479 s, TAIFEX 0.314235 s, total reported request time 6.207205 s. Wood selected values matched prior successful run. Failure classifications have not been exercised by this successful run; provider uptime is not established. Close basic runtime-diagnostics acceptance; proceed to unified operation/output and App core interface design.

## 1. Current research routing

| Need | Open first | Next action / blocker |
|---|---|---|
| **Physical Hexagram P3 — active priority** | [Provisional six-line contract](physical_model/qualification.md#current-p3-convergence-checkpoint--2026-11-28) | Retain six natural observables, proposed phenomenological order and R-Trend; provisional 30-minute block design only. Resolve provider eligibility/rights/support and uncertainty before freeze. 0/6 qualified; live disabled. |
| Planetary motion (bounded replay complete) | [planetary replay](planetary_motion/vector_replay.py), [#7239859530](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7239859530) | Accepted owner export; slow astronomical context candidate, no short-cadence replacement. External calibration deferred until a concrete design decision. |
| Architecture (working decision) | [Layered architecture](classical_mapping/candidate_architecture.md#working-architecture-decision--2026-11-28) | Preserve current quantum/MPH; astronomy is optional context, not another six-line method. Keep six-domain natural-observation profile offline. Reopen research only for a concrete implementation/qualification decision. |
| Tidal gravity (parked) | [Earth orientation](tidal_gravity/earth_orientation.py), [#7239529486](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7239529486) | Exploratory diagnostics sufficient; no further routine refinement. Independent EOP/Horizons and calibrated joint uncertainty deferred until formal candidate selection or a material discrepancy. |
| Ocean tide | [support review](ocean_tide/station_support.py), [#7223004237](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7223004237) | Station calibration, reference/model uncertainty and estimand selection. |
| Geomagnetism | [native audit](geomagnetism/native_audit.py), [#7223335599](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7223335599) | Provider R0 calibration, decomposition residual, seasonal background and as-of. |
| Cosmic rays | [counting diagnostic](cosmic_ray/counting_uncertainty.py), [#7224018446](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7224018446) | Exposure/calibration/rights; completed correction replay in archive. Do not repeat speculative capture. |
| Solar wind | [provider questions](solar_wind/provider_questions.md), [#7234645446](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7234645446) | Flag definitions, calibration/covariance, sweep/NGP support, publication and rights. Requests unsent. |
| Cross-domain comparison | [model compare](physical_model/compare_models.py), [timescale](physical_model/timescale.py) | Inspected dates only; do not optimize or select by hexagram yield. |

## 2. File catalog

Role labels: **DOC** = research reference; **REPLAY** = completed diagnostic retained for reproducibility; **SHARED** = imported dependency or historical capture helper (not a request to reacquire); **OWNER-DONE** = owner execution reported; **BLOCKED-INPUT** = independent replay cannot proceed without existing artifact. A completed diagnostic is not a qualified physical model.

### Classical mapping and planetary motion

| File | Role | Use / evidence boundary | Issue evidence |
|---|---|---|---|
| [classical_mapping/candidate_architecture.md](classical_mapping/candidate_architecture.md) | DOC | Classical sources, functional/planetary/physical alternatives, encoder semantics | [#7238826420](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7238826420) |
| [planetary_motion/angular_motion.py](planetary_motion/angular_motion.py) | REPLAY | Pinned DE440s export completed and arithmetic accepted; do not recapture | [#7238893578](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7238893578) |
| [planetary_motion/vector_replay.py](planetary_motion/vector_replay.py) | REPLAY | Accepted independent arithmetic replay of pinned B01 JSON | [#7238939530](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7238939530) |
| [classical_mapping/sixth_channel_order.md](classical_mapping/sixth_channel_order.md) | DOC | Sixth-channel options, exhaustive position sensitivity and angular uncertainty | [#7238971766](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7238971766) |
| [planetary_motion/lunar_geometry.py](planetary_motion/lunar_geometry.py) | REPLAY | Geometric illuminated fraction versus M01; uses owner M01 vector JSON | [#7239016918](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7239016918) |

### Tidal gravity

| File | Role | Use / evidence boundary | Issue evidence |
|---|---|---|---|
| [tidal_gravity/formula_check.py](tidal_gravity/formula_check.py) | SHARED | Independent scalar/Decimal formula and synthetic geometry; imported by vector audit | [#7222649080](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222649080) |
| [tidal_gravity/vector_export.py](tidal_gravity/vector_export.py) | SHARED | Original pinned vector export and checks; imported by margin study | [#7236148998](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7236148998) |
| [tidal_gravity/vector_replay.py](tidal_gravity/vector_replay.py) | REPLAY | Independent exported-vector arithmetic and perturbation review | [#7236148998](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7236148998) |
| [tidal_gravity/component_margin.py](tidal_gravity/component_margin.py) | REPLAY | Fixed/varying component gain sensitivity | [#7222856369](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222856369) |
| [tidal_gravity/ephemeris_comparison.py](tidal_gravity/ephemeris_comparison.py) | REPLAY | Optional Moshier cross-model check; separate licensing review before integration | [#7239092340](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7239092340) |
| [tidal_gravity/projection.py](tidal_gravity/projection.py) | REPLAY | Radial/ellipsoidal normal and conditional GM gains | [#7239134571](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7239134571) |
| [tidal_gravity/elastic_response.py](tidal_gravity/elastic_response.py) | REPLAY | Legendre expansion and simplified solid Earth response; distinct estimand | [#7239165876](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7239165876) |
| [tidal_gravity/earth_orientation.py](tidal_gravity/earth_orientation.py) | REPLAY | Alternate terrestrial-frame reconstruction with owner TT/UT1; not independent observed IERS EOP | [#7239529486](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7239529486) |

### Ocean tide

| File | Role | Use / evidence boundary | Issue evidence |
|---|---|---|---|
| [ocean_tide/prediction_capture.py](ocean_tide/prediction_capture.py) | SHARED | Original tide prediction capture and decode; used by residual/support tools | [#7222341927](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222341927) |
| [ocean_tide/residual.py](ocean_tide/residual.py) | SHARED | Datum versus tide residual and coupled-domain comparison; exports tide pin | [#7222341927](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222341927) |
| [ocean_tide/uncertainty.py](ocean_tide/uncertainty.py) | REPLAY | Centered support, observation/reference stress intervals | [#7222916993](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222916993) |
| [ocean_tide/station_support.py](ocean_tide/station_support.py) | REPLAY | Station provenance, prediction temporal support and sensitivity | [#7223004237](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7223004237) |

### Geomagnetism

| File | Role | Use / evidence boundary | Issue evidence |
|---|---|---|---|
| [geomagnetism/observation_operator.py](geomagnetism/observation_operator.py) | SHARED | Scalar F observation-operator sensitivity; imported by native tool | [#7223099565](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7223099565) |
| [geomagnetism/native_capture.py](geomagnetism/native_capture.py) | SHARED | Original native minute/decomposition capture, decoder and URL contract | [#7223185978](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7223185978) |
| [geomagnetism/native_audit.py](geomagnetism/native_audit.py) | REPLAY | Native minute replay, filter compatibility and decomposition closure | [#7223335599](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7223335599) |

### Cosmic rays — neutron-monitor corrected count rate

| File | Role | Use / evidence boundary | Issue evidence |
|---|---|---|---|
| [cosmic_ray/counting_uncertainty.py](cosmic_ray/counting_uncertainty.py) | SHARED | Conditional counting/pressure sensitivity; archived correction chain imports it | [#7223407815](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7223407815) |

### Solar wind — MAG and SWiPS

| File | Role | Use / evidence boundary | Issue evidence |
|---|---|---|---|
| [solar_wind/revision_probe.py](solar_wind/revision_probe.py) | SHARED | Original metadata probe and shared URL/listing/clock helpers | [#7222127629](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222127629) |
| [solar_wind/l2_l3_bridge.py](solar_wind/l2_l3_bridge.py) | SHARED | Packet correspondence, temporal label audit, shared moment parser | [#7222127629](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222127629) |
| [solar_wind/l2_audit.py](solar_wind/l2_audit.py) | REPLAY | September L2 flags, collisions and eligible support | [#7222584812](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222584812) |
| [solar_wind/plasma_coupling.py](solar_wind/plasma_coupling.py) | REPLAY | Proton thermal/magnetic pressure, beta and conditional sensitivity | [#7234128136](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7234128136) |
| [solar_wind/sweep_support.py](solar_wind/sweep_support.py) | REPLAY | Sweep overlap, magnetic magnitude and flag strata | [#7234606790](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7234606790) |
| [solar_wind/provider_questions.md](solar_wind/provider_questions.md) | DOC | Version-specific provider questions; unsent; no approval implied | [#7234645446](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7234645446) |

### Common evidence and physical model

| File | Role | Use / evidence boundary | Issue evidence |
|---|---|---|---|
| [physical_model/qualification.md](physical_model/qualification.md) | DOC | G1–G8/Q qualification review and historical data SHA256 registry; baseline, not live status | [#7222584812](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222584812) |
| [common/capture_audit.py](common/capture_audit.py) | SHARED | Original September parsing and validation primitives | [#7222584812](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222584812) |
| [common/joint_audit.py](common/joint_audit.py) | SHARED | Pinned ZIP validation, shared grids and joint diagnostic | [#7222584812](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222584812) |
| [common/supplement_capture.py](common/supplement_capture.py) | SHARED | Original bounded capture and shared transport; do not recapture | [#7222584812](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222584812) |
| [physical_model/reference_sensitivity.py](physical_model/reference_sensitivity.py) | SHARED | Reference/aggregation analysis and shared series/block functions | [#7222584812](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222584812) |
| [physical_model/time_support.py](physical_model/time_support.py) | SHARED | Support alignment and minute-grid loading | [#7222584812](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222584812) |
| [physical_model/background.py](physical_model/background.py) | SHARED | Fixed versus trailing background; shared reference functions | [#7222584812](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222584812) |
| [physical_model/uncertainty.py](physical_model/uncertainty.py) | REPLAY | Hypothetical uncertainty propagation across domains | [#7222184629](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222184629) |
| [physical_model/compare_models.py](physical_model/compare_models.py) | REPLAY | Compare candidate background/reference semantics without selection | [#7222396402](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222396402) |
| [physical_model/timescale.py](physical_model/timescale.py) | REPLAY | Characteristic timescale diagnostics, not a frozen window | [#7222490785](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222490785) |

## 3. Local artifact routing

All observational captures and generated results remain under `temp/PH_BT_v01/` locally, not in Git. Do not substitute datasets or regenerate a pinned file silently. See [qualification baseline](physical_model/qualification.md#rechecked-artifact-digests-sha256) for the five original September ZIPs and early result digests. The following later pins are recorded from Issue #6; availability and actual bytes must be verified in the execution environment.

| Artifact | SHA256 | Evidence / use |
|---|---|---|
| `physical_m01_vectors_result_v01.json` | `640425e5be4af42c797b21c2dc1d8ca943cf40108bb817c7022864695fab7ad9` | [#7236148998](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7236148998); M01 and lunar replay |
| `cosm_planetary_motion_result_v01.json` | `698adce3ed4532ecb13b712565c2cc15dff4f4484df5b74f89d183383d19921c` | [#7238939530](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7238939530); owner bytes received and verified [#7239859530](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7239859530) |
| `planetary_vector_replay_result.json` | `b7890509a069bd255c0cc7b88bb1b3c590250d14a094b1154db5d61d2c2ffca7` | [#7239859530](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7239859530) |
| `planetary_cadence_result.json` | `ea0a62a34e163fe63ec3d4b29e76e9308ff310b7001814aa28b1b98b595ff85e` | [#7239859530](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7239859530) |
| `PH_BT_d06_native_v01.zip` | `6b07bdab4bb45a75cdfbea79a7c9538a7fa05f7bd63d823e34fb906ca05864c7` | [#7223335599](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7223335599); native audit |
| `PH_BT_d26_correction_v02.zip` | `e0f89b7b8f6963540017dfcaa53622b2f177dbf5bd401a2dc342c262874ea1f3` | [#7224018446](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7224018446); historical correction audit |
| `cosm_lunar_geometry_result_v01.json` | `9261f9af7c79dc64e0f55d86ca8479a1c8d7ad8b725673bfd6f2922b72df73eb` | [#7239016918](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7239016918) |
| `physical_m01_moshier_result_v01.json` | `46bbd83845f701cf9973852b0495b6d743ac409123713d15d58e9b20b3e0e139` | [#7239092340](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7239092340) |
| `physical_m01_projection_result_v01.json` | `193ed28c5f2672b8d9331bc31b9a157ab6face117d3f788252e62291de093f63` | [#7239134571](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7239134571) |
| `physical_m01_elastic_result_v01.json` | `0872be398d6e723ae71a01391a37ef04235fe42a6ee56a11d66fbcac05977ce1` | [#7239165876](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7239165876) |
| `earth_orientation_result.json` | `63b654ef42e3d54d12b6452fc91b1b4e9db932e636566bd629698a5b12ac4dd4` | [#7239529486](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7239529486) |

## 4. Dependency routing

Use absolute imports (`research.<domain>.<module>`) and module execution. The directories are Python namespace packages (no package initialization side effects). Shared capture tools live in `common/`; domain-specific reusable functions remain in their owning module. Do not duplicate or extract numerical algorithms during path-only changes. The main shared chains are:

- September audit -> joint -> reference sensitivity -> time support -> background / uncertainty / model compare / timescale (arrow indicates downstream use, not exclusive dependencies).
- Supplement transport -> SWiPS metadata probe -> SWiPS bridge -> time support; L2 audit also uses the probe.
- D06 operator -> native capture -> native audit.
- Tide background -> tide residual -> D12 support / uncertainty.
- M01 math -> vectors -> margin; joint also supports vector replay. Lunar, Moshier, projection and elastic tools consume the pinned owner vector JSON separately.
- D26 counting -> archived correction v0.1 -> v0.2 -> archived correction audit. Preserve exact archived blobs and use the pinned pre-migration checkout described in the archive README.

## 5. Offline replay (Windows PowerShell)

From the repository root, synchronize and work in the original data directory:

```powershell
git pull --ff-only
$repoRoot = (Get-Location).Path
$oldPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $repoRoot + [IO.Path]::PathSeparator + $oldPythonPath
    Set-Location .\temp\PH_BT_v01
    py -m research.common.capture_audit .\PH_BT_september_capture_v01.zip
    py -m research.common.joint_audit .\PH_BT_september_capture_v01.zip .\PH_BT_september_supplement_v01.zip .\PH_BT_september_D26_v01.zip
    py -m research.physical_model.reference_sensitivity .\PH_BT_september_capture_v01.zip .\PH_BT_september_supplement_v01.zip .\PH_BT_september_D26_v01.zip
} finally {
    Set-Location $repoRoot
    $env:PYTHONPATH = $oldPythonPath
}
```

For a single module from the repository root, pass explicit data paths where its CLI supports them, for example `py -m research.planetary_motion.vector_replay .\temp\PH_BT_v01\cosm_planetary_motion_result_v01.json`. Modules that create relative output files should be run in the original local data directory with the repository root on PYTHONPATH. Do not run a nested script by filename if it imports another research package.


Examples, not a recurring instruction to rerun completed tests. Read the selected script's exact CLI and input pins before running. NumPy/SciPy are required for relevant offline tools; some astronomy diagnostics have additional dependencies. Original capture/transport tools from the archived PH_BT_v01 package must not be reconstructed or replaced.

## 6. Maintenance and evidence boundaries

- Update this index whenever a script is added, superseded, archived or a blocker changes. Record the purpose, input identity, output identity, role and latest Issue #6 evidence in the same change where practical.
- Keep evidence versions immutable. Use a newer version for changed algorithms; distinguish historical and current results. Archive only when the active dependency chain permits, preserving original blobs and historical replay.
- No raw NMDB redistribution. Confirm intended-use rights. Preserve all original captures and BT-C (2026-09-21 UTC) sealed. BT-A/B are already inspected. No production changes, automatic recapture, cast, QRNG fallback or model freeze implied by this index.
- Separate the PH-BT six-domain physical candidate, COSM planetary/functional candidates and existing MPH. Do not treat numerical replay or cultural affinity as physical qualification.

觀象，察變，求真，思己。
