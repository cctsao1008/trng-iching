# Physical Domain Qualification Review v0.1

Status: **EXPLORATORY ONLY / 0 OF 6 QUALIFIED / NO MODEL FREEZE**

This review consolidates Issue #6 evidence through PH-BT characteristic timescale v0.1. It is not a frozen acceptance contract, a source approval, or a production integration change. All dates below are UTC. BT-C (2026-09-21) remains sealed; BT-A (Sep 7) and BT-B (Sep 14) are already inspected, not independent validation. Separate #3/#4 and #6 prospective cohort protocols remain unchanged.

## Review method and scope

Rechecked the five September input ZIP hashes and CRCs and the six recent result JSON hashes against the prior recorded digests. Reopened earlier issue reviews for D06 seasonal backgrounds, D26 slow backgrounds, SOLAR-1 documentation, reference qualification and the production evidence contract. Older underlying raw files and provider PDFs were not reprocessed in this review. No new observation payloads or statistical experiment. Current main.py blob be9f4b859dca050f8d5c74165f2b29dff7928157 retains the model_not_ready branch; astronomy.py blob efe206f6c613c1e33ecc208fccb8e470f922c1a6 retains the candidate rigid radial model. This is read-only source inspection, not a production regression test.

Evidence status: E = evidence exists for part of the criterion, B = specific unresolved blocker, U = insufficient evidence. E does not mean a production gate passed. G1–G8 retain the prior reference qualification review scope; scientific QC is explicitly separated below as Q. No domain passes all gates.

| Domain | G1 quantity semantics | G2 identity | Q scientific QC | G3 time/as-of | G4 reference | G5 uncertainty | G6 replay | G7 independent evaluation | G8 rights |
|---|---|---|---|---|---|---|---|---|---|
| D03 | E | E | B | B | B | B | E | U | E |
| D02 | E | E | B | B | B | B | E | U | E |
| D06 | E | E | B | B | B | B | E | U | U |
| D26 | E | E | B | B | B | B | E | U | B |
| D12 | E | E | E | B | E | B | E | U | U |
| M01 | E | E | E | B | E | B | E | U | U |

G2 and G6 refer to pinned retrospective artifacts and prior replay, not live provenance or independent implementation agreement. For M01, Q means input/model integrity evidence, not measured instrument QC. D12 E on Q refers to verified historical sensitivity only; preliminary-only production policy is unchanged. NOAA embedded unrestricted terms for reviewed SOLAR-1 files are evidence, not a blanket commercial-use determination. All rights gates must match the intended use and redistribution scope. Production approval and joint spatial/time alignment remain separate requirements.

## Domain-specific acceptance work

### D03 — SOLAR-1 MAG L3 magnetic magnitude (nT)
- Estimand: native scalar magnitude, not norm of an averaged vector; distinguish absolute field strength from a regime-relative disturbance.
- Blocker: all 171865 one-second September flag values 0x80000001; documented bit 0 saturation, undefined bit 31; no minute flag. This does not establish actual saturation or an encoding bug. Robust L3 aggregation is not an arithmetic mean.
- Acceptance evidence: provider interpretation and applicable minute QC policy, product-specific calibration and low-frequency drift evidence, temporal support and publication record, justified reference regime and independent validation. Do not strip bits or infer physical accuracy from RTSW numeric matching.

### D02 — SOLAR-1 SWiPS proton thermal pressure (nPa)
- Estimand: n*kB*T using documented units, distinguish absolute thermal pressure from relative plasma regime; retain velocity/context for QC.
- September L3 absent; uncorrected L2 retained as separate retrospective sensitivity. Nov 26 owner manifest: 1431/1431 exact packet pairs, 1421/1421 exact positive n/T/pressure; original November L3 ZIP not independently rejoined in the latest review. Nearest midpoint mapping does not reproduce L3.
- Acceptance evidence: provider flag/backfill/NGP semantics and time support; resolve missing L3 and missing correction/error fields; uncertainty in n,T and their covariance and temporal persistence from calibrated evidence. Separate product-specific validation, no silent L2 substitution or assumed fixed gain. Official simulation regions are not hard uncertainty bounds.

### D06 — USGS BOU F R0 (nT)
- Estimand: total scalar field; quiet-time main/slow field plus diurnal response is a candidate background, not a frozen model.
- Existing Aug/Oct research: 9 August quiet days, October inspected evaluation. Centered quiet-day peak-to-peak 38.92832 vs 21.44419 nT; smooth Fourier variants alter 480–940 of 1487 numerical codes versus original, depending on model. Do not select order by inspected MAE or code yield.
- Acceptance evidence: product-specific R0 calibration/quality and as-of, matched native minute/second support, fixed seasonal quiet-time reference tested against independent quiet and disturbed data with event retention; distinguish R0 from adjusted/definitive products. Published USGS adjusted-data accuracy cannot be transferred to R0.

### D26 — OULU original MCORR_E (counts/s)
- Estimand: corrected station count rate, not raw independent Poisson counts.
- Existing 27-day calibration + 14-day inspected evaluation: first/last calibration slope +0.11242/-0.04298 counts/s/day. Adaptive 3/7-day controls absorb synthetic sustained shifts; fixed control preserves them algebraically, not validated event detection.
- Acceptance evidence: provider definitions, correction factors, raw count/exposure or calibrated rate uncertainty including serial correlation; background preserves independently labeled events, publication history and explicit permission for intended use. NMDB noncommercial/provider restrictions apply; public application or commercial use cannot be presumed approved. No raw redistribution.

### D12 — NOAA 9414290 water level (mm MLLW)
- Two separate estimands: water level relative to MSL 951 mm (1983–2001 datum epoch), or anomaly relative to station harmonic tide prediction. NOAA prediction is a background model, not observed water.
- September verified sensitivity: pairwise 30-min MAE MSL vs tide residual 550.25/135.77 mm and 461.03/167.13 mm; all 480 native residuals positive. No recentering or selection to balance symbols.
- Acceptance evidence: choose intended estimand on physical meaning before independent evaluation, pin datum epoch/model version and station-specific measurement and reference uncertainty; verify flags, time support, preliminary vs verified distinction and as-of. Prediction-residual uncertainty must include model discrepancy appropriate to intended reference, not equate observed residual with error.

### M01 — geometric rigid radial Sun+Moon differential acceleration (microGal)
- Estimand: signed geocentric radial component at fixed WGS84 site (37.8063,-122.4659,0), not total gravity or measured Earth tide. Zero is a mathematically interpretable reference.
- Pinned Skyfield 1.55 and DE440s, component sums and prior replay checked; independent ephemeris computation and complete error budget pending.
- Acceptance evidence: independent arithmetic formulation and test vectors; independent software implementation using pinned geometric Sun/Moon vectors and same frame/time scales/site convention; an external JPL Horizons comparison may corroborate ephemeris vectors but shares DE440/441 family and is not independent observational truth. Quantify numerical, time, position and model sensitivities separately. A rigid model must not be presented as a complete gravimeter response. Establish model version/as-of, rights and reproducible time/frame metadata before prospective evaluation.

## Next bounded work (proposed, not frozen)

1. M01: verify the existing formula against independent high-precision arithmetic and synthetic geometry before attempting real ephemeris-vector comparison. Freeze a separate test specification and tolerance rationale before looking at new comparison results; no observation retrieval for arithmetic tests. Compare fixed 6-min epochs from BT-A/B only if actual vectors available. Record what is shared versus independent. Passing numerical comparison alone is not source qualification.
2. D12: decide explicitly between absolute datum and tidal anomaly estimands; obtain station sensor/algorithm, datum and prediction-version uncertainty evidence. Do not choose based on polarity balance or correlation.
3. Parallel desk work: request provider clarification on D03 flags and D02 calibration/temporal contract; D26 terms and uncertainty; D06 product-specific baseline/support. No message sent or approval assumed by this review.
4. When gates have evidence, preregister estimand, w/b/h, QC, reference, uncertainty, abstention, support/as-of, independent evaluation metrics and stop criteria. Keep BT-C sealed until a scientifically justified candidate and evaluation protocol are frozen. If evidence is unavailable, record blocked rather than invent a parameter.
5. Preserve existing prospective cohort dates and #3/#4 protocols. No live enable, cast or QRNG fallback.

## Current P3 convergence checkpoint — 2026-11-28

Owner approved concentrating development on Physical Hexagram ([priority decision](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7239962627)). The preceding review remains historical evidence. This checkpoint narrows the working design, not the production freeze. Preserve Quantum/MPH and all independent protocols. No additional candidate sources or routine ephemeris refinement.

### Provisional six-line contract for review

Retain the phenomenological order already proposed in [P3A](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7199240093), bottom to top: local water response, modeled tidal forcing, ground magnetic field, ground particle detector, upstream plasma, upstream magnetic field. This is a symbolic grouping (not a causal chain, distance ranking, Five Phases equivalence or claim of independence).

| Line | Observable | Fixed candidate identity / unit | Native input to qualify |
|---|---|---|---|
| 1 | Ocean water level | NOAA 9414290 MLLW, mm | six-minute observed level; qualify preliminary product and support |
| 2 | Tidal gravity | JPL DE440s / Skyfield 1.55, fixed WGS84 (37.8063,-122.4659,0), microGal | six-minute geometric direct radial forcing; modeled, outward positive |
| 3 | Geomagnetic field | USGS BOU native F R0, nT | 1-second source, not derived XYZ nor adjusted F |
| 4 | Cosmic rays | NMDB OULU original MCORR_E, counts/s | one-minute corrected interval rate, not raw Poisson counts |
| 5 | Solar-wind proton thermal pressure | NOAA SOLAR-1 SWiPS native L3 n*kB*T, nPa | native minute product; L2 uncorrected only historical sensitivity, not replacement |
| 6 | Solar-wind magnetic field | NOAA SOLAR-1 MAG native L3 Bt, nT | native minute scalar magnitude, not norm of vector mean |

Working encoder: retain owner-approved leading hypothesis A (R-Trend, [P3E-D](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7207254201)). For three ordered values x0,x1,x2 in the same unit and operator, d1=x1-x0, d2=x2-x1. (--)=8,(-+)=6,(++)=7,(+-)=9. Primary polarity denotes earlier change, relating polarity later change; no forecast. Fixed additive baselines cancel, so no need to solve arbitrary state thresholds for this candidate. Time-varying background subtraction is a different observable and is not silently adopted. Both changes must be resolved using justified difference uncertainty; exact zero or unresolved is not a line. Conservative absolute bounds u0,u1,u2 imply |d1|>u0+u1 and |d2|>u1+u2 for resolved signs; use correlated error cancellation only with evidence. Do not set unknown bounds to zero. Existing exact-Decimal sign implementation is a reusable mathematical component, not a scientific uncertainty gate.

Provisional engineering evaluation support: three successive disjoint 30-minute UTC blocks, common fixed end E and 90-minute total window. This width is a compatible multiple of existing native grids and an already examined diagnostic scale, not an empirically optimized or approved final cadence. Define block statistic as mean over the declared support, with equal weights only for a verified regular equally supported series (modeled point-sample mean explicitly labeled). Interval start/center/end, completion and boundary treatment must be established per product before a live operator exists. All required samples/coverage and QC must pass, no gap compression, no adaptive window search. Request anchor T distinct from data cutoff E and decision time; E determined once by an eventually fixed, justified latency policy, never by success of a cast. Final publication lag, support and uncertainty remain open; no numerical defaults invented. Independent capture may repeat same observation supports; existing process-local formed-time guard remains. Do not assemble a hexagram when any domain is unresolved.

### Concrete implementation boundary and outstanding work

Static review of current sources.py (e36ba43925d2b95c42aacc8e209bdfd2aba210f0): D06/NEST research adapters exist, but return candidate_parsed with native_resolution_verified=false, source_qc_validated=false, historical_as_of_verified=false, publication_time_utc=None and ready_for_cast=false. D06 parser checks station/channel; R0 and support need stronger metadata validation for eventual live use. Existing MPH adapters implement a different three-endpoint contract and cannot silently be treated as qualified block operators. main.py gate remains model_not_ready. No code changes required at this checkpoint.

Rechecked actual stored compare-model and timescale JSON identities against the registry above; these are inspected BT-A/B diagnostics, not new evaluations. Existing September strict native SWiPS L3 unavailable and verified-only water is sensitivity rather than current preliminary policy. Therefore those data cannot demonstrate six-channel live readiness, regardless of nominal R-Trend or J-S resolution. Prior J-S reference results do not select R-Trend cadence. Preserve source IDs and no fallback.

Next actionable gates, in order:
1. Source eligibility and permission: resolve SOLAR-1 MAG flag semantics/minute QC and SWiPS L3 availability/correction/time support; resolve NMDB intended-use permissions and count/exposure uncertainty; resolve USGS R0 and NOAA water support/calibration/publication. Reuse existing provider questions; no request sent or approval inferred.
2. Pin actual product support, lag and bounded uncertainty policy for the six selected observables. Review #3 D3/D4 partial outcome and #4 MTS according to their independent protocols; explicitly disposition unavailable evidence rather than rerun or refit. Owner review of proposed order/encoder/support is required before formal freeze.
3. Freeze the accepted contract and preregister independent evaluation, with no tuning on BT-C. Only after all applicable scientific/source gates pass, proceed to P4 actual integration, then P5 regression and three-method acceptance. No new scripts, capture, cast, or holdout inspection in this checkpoint.

Status: provisional semantic contract specified; P3 OPEN, 0/6 qualified, P4/P5 not started; independent holdout sealed. This supersedes routine refinement priority, not earlier evidence or acceptance gates.

## P3 source eligibility and observation contract review — 2026-11-28

Status: **DRAFT / DESK EVIDENCE ADVANCED / 0 OF 6 QUALIFIED / NO FREEZE**. Decision scope: determine which source-use and observation questions can be closed by authoritative documentation and which require product-specific evidence; define a reviewable difference-uncertainty contract. Stop after these dispositions; no new observations, candidate ranking, calibration experiment, or BT-C access.

### Source-use scope and remaining evidence

Public terms were reviewed on 2026-11-28. These are published-policy findings, not individual supplier approvals. Distinguish local research, public noncommercial service, commercial service and raw redistribution; keep attribution and product provenance. No new raw payloads are published.

| ID | Published evidence / disposition | Remaining qualification blocker |
|---|---|---|
| D12 | NOAA federal-data general public-domain policy, subject to exceptions; API supports preliminary or verified six-minute levels. | Station 9414290 actual sensor, datum continuity, effective measurement support, preliminary QC, differential error and availability. |
| M01 | NAIF allows use and unmodified redistribution of NAIF-distributed kernels, including commercial use subject to its rules; verify the actual DE440s distribution and library licenses separately. | Reuse existing accepted arithmetic/ephemeris diagnostics; quantify relevant time/frame/model difference errors, not gravimeter-response errors. |
| D06 | USGS-produced data public-domain policy; API explicitly defines R0 as internet variation, not adjusted/definitive. | Confirm BOU F R0 provenance, 1-s support, calibration continuity, fatal flags/sentinels and differential uncertainty. |
| D26 | NMDB permits noncommercial use subject to station restrictions and attribution. Oulu explicitly includes research, education and public noncommercial services; commercial use requires contacting its manager. | Confirm intended app scope (including derived-only outputs and redistribution), exact original MCORR_E support/exposure/QC, pressure and efficiency correction uncertainty, revisions and delay. |
| D02 | NOAA general policy and previously reviewed operational metadata support public-data use; no blanket product approval asserted. Official SWiPS L3 minute product is listed. | Exact version L3 support, native availability, corrected n/T meaning, flag validity, covariance and error bounds; no L2 substitution. |
| D03 | Same NOAA policy boundary; operational MAG L3 second/minute products listed. | Version-specific 0x80000001 interpretation and propagation to scalar minute QC, drift and uncertainty; do not strip bits. |

Sources: [NOAA policy](https://www.noaa.gov/office-education/outreach-communication/faq), [CO-OPS API](https://api.tidesandcurrents.noaa.gov/api/dev/), [CO-OPS field definitions](https://api.tidesandcurrents.noaa.gov/api/dev/responseHelp.html), [NAIF rules](https://naif.jpl.nasa.gov/naif/rules.html), [USGS rights](https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits), [USGS API](https://www.usgs.gov/tools/web-service-geomagnetism-data), [NMDB rights/version semantics](https://www.nmdb.eu/nest/statements.html), [Oulu provider terms/corrections](https://cosmicrays.oulu.fi/readme.html), [SOLAR-1 product overview](https://www.ncei.noaa.gov/products/space-weather/swfo).

CO-OPS preliminary flags are O (outlier count), F (flat), R (rate), L (limit); verified flags are I (inferred), F, R, T (limit). The sigma field describes dispersion of 1-s samples, not a calibrated bound on block-to-block change. Proposed conservative preliminary policy: require q=p and F/R/L=0, retain O and require a documented O eligibility rule before use; do not admit verified values in the live preliminary operator. The station's 2024 sediment advisory illustrates why site effects cannot be inferred from nominal sensor accuracy ([station](https://tidesandcurrents.noaa.gov/stationhome.html?id=9414290)); it is not evidence of a current defect. Oulu documents pressure and efficiency corrections and says current-month data are unverified; NMDB original may already contain real-time corrections. Do not model corrected rates as raw Poisson counts or treat original as immutable first-release data.

### Draft common observation and uncertainty contract (owner review required)

- Retain raw water height relative to MLLW, native F R0, corrected neutron rate, native L3 thermal pressure and scalar Bt, and modeled direct radial tidal acceleration. A constant datum offset cancels in R-Trend; tide prediction subtraction or seasonal detrending would change the estimand. No such subtraction is required by this encoder.
- Proposed common UTC support: B0=[E-90m,E-60m), B1=[E-60m,E-30m), B2=[E-30m,E). Distinguish source observation/support start/end, retrieval time, source release/revision (when known), cast anchor T and decision time. All support must be complete by E; no future-support or post-anchor data presented as available at T. Candidate E=floor((T-L)/30m)*30m on UTC grid; L is a single predeclared nonnegative lag derived from all selected products' availability/support evidence, not from a successful cast. L and maximum observation age are unset; unknown release time is not replaced with retrieval time. Prospective acquisition can demonstrate availability by actual retrieval, not historical first release.
- For equally supported aligned full-coverage records use a mean; for verified interval data use support weighting only if the operator and boundary treatment are documented. A 30-min block can nominally contain 5 six-minute labels, 30 one-minute labels, or 1800 one-second labels, but label counts alone do not prove support. Do not split centered/overlapping instrument measurements across blocks without an approved operator. For M01 retain explicitly defined six-minute modeled point samples, not continuous observations. Reject gaps, conflicting duplicates, bad flags, unsupported edge samples and identity/version changes. No adaptive resampling or fallback.
- Use difference-specific uncertainty: for d1=x1-x0 and d2=x2-x1, define nonnegative supported error bounds U1 and U2. A difference is positive only when d-U>0, negative only when d+U<0; equality or interval overlap with zero is unresolved. Unknown uncertainty is unresolved, not zero. Independent bounded block errors u_i give U1=u0+u1, U2=u1+u2 (independence is not required for this conservative triangle bound). If source evidence supports correlated errors, a constant additive bias cancels; a common strictly positive fixed gain preserves sign. Time-varying drift, gain changes, timing, sample support, quantization and correction errors do not automatically cancel. Document any cancellation premise. A statistical coverage interval is not a guaranteed error bound; if adopted later, predeclare coverage and joint error control for all 12 differences without assuming independence. Do not use arbitrary fixed epsilon, observed spread alone or tune by line yield.
- For D02 compute n*kB*T per eligible matched native L3 record, then aggregate the resulting pressure; product of block mean density and temperature is a different operator. Use calibrated joint uncertainty or conservative positive-input interval propagation; do not assume n/T independence. For D26 raw exposure/counting and correction uncertainties must support the rate-difference error; for D12 and D06 distinguish repeatable offsets from temporal errors; for D03 preserve scalar magnitude rather than vector-mean magnitude. M01 uses a pinned model; numerical replay alone does not establish physical-model bounds.
- Only if both differences resolve, map (-,+)=6, (+,+)=7, (-,-)=8, (+,-)=9. Any domain unresolved means no hexagram. Preserve existing process-local guard, no redraw, no changes to Quantum/MPH.

### External evidence and independent dependencies

- Reuse [solar provider questions](../solar_wind/provider_questions.md) for MAG and SWiPS, including exact archived product IDs. Ask additionally for native operational L3 availability and a usable difference-error/support contract.
- Oulu station manager (Ilya.Usoskin@oulu.fi, published provider contact): ask whether the intended public noncommercial symbolic application and eventual commercial derived-only output are allowed under NMDB terms; ask for MCORR_E raw count/exposure, corrections, support, quality and release/revision evidence. No request sent.
- USGS Geomagnetism and NOAA CO-OPS: request only the station/product-specific support, QC, temporal differential uncertainty and availability evidence listed above, rather than a general accuracy guarantee. No requests sent.
- #3 D3/D4: [recorded partial outcome](https://github.com/cctsao1008/trng-iching/issues/3#issuecomment-7210016803), Earth arithmetic reviewed, three measured domains unavailable due to transport failure. Retain as incomplete independent evidence; no rerun/refit.
- #4 MTS-P0: [existing frozen protocol](https://github.com/cctsao1008/trng-iching/issues/4#issuecomment-7197930128) and [readiness review](https://github.com/cctsao1008/trng-iching/issues/4#issuecomment-7207560997); no owner execution report located in current issue evidence. Keep separate, do not reconstruct or replace from #6 retrospective studies.

Exit: owner reviews estimands/order/R-Trend/30-min candidate and intended-use scope; obtain remaining source-specific evidence or explicitly report blocked. Freeze support/latency/uncertainty and independent acceptance protocol before opening BT-C. Stop routine desk review until a concrete unresolved source question can be answered. Formal qualification remains 0/6; no live enable, no production code changes, no raw capture, no new independent validation claimed.

## P3 measurement-support closure boundary — 2026-11-28

Decision: determine whether the proposed 30-minute common support can be represented by native D12 records without splitting measurements. This is a bounded specification/geometry check, not a new physical experiment.

### D12 native support and phase

The [CO-OPS sensor specification, updated December 2025, pp. 1–2](https://tidesandcurrents.noaa.gov/publications/CO-OPS_Measurement_Spec.pdf) distinguishes the six-minute reporting cadence from actual centered measurement support. Primary radar: 360 one-second samples over six minutes; acoustic: 181 one-second samples over about three minutes; primary dual bubbler: 36 five-second samples over three minutes. The document specifies estimated individual accuracy relative to datum of ±20 mm for these sensor classes, with outlier rejection. Prior [station evidence](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7223004237) identified Y1 microwave and U1 tsunami sensors and temporary-station history; it does not establish the actual API channel or configuration at each epoch. No new capture or tide residual replay.

Conditional geometry: ideal radar support [t-180s,t+180s) for UTC labels t divisible by 360s. At an unshifted half-hour block, only four complete native intervals lie inside; assigning all five labels leaks support across a boundary. A fixed +180s phase on the half-hour UTC grid permits five full contiguous native intervals per block (e.g. [12:03,12:33) with centers 12:06,12:12,12:18,12:24,12:30). For three-minute centered support, gaps remain regardless of phase; a full continuous coverage contract is not met by label count. Bounded synthetic enumeration of all 360 integer-second phases: radar full-cover phases={180}; acoustic full-cover phases={} under ideal 180s support. At phase 0/180 radar counts 4/5; this checks geometry only, not sensor behavior. The provider's exact discrete endpoint convention and actual support remain to be confirmed.

Candidate revision for owner review: E=phi+floor((T-L-phi)/1800s)*1800s with phi fixed only after native support compatibility across all six domains is confirmed. Example phi=180s is not approved; minute-centered records may require a different phase and make exact common tiling impossible. If no common full-support phase exists, report incompatibility before freeze; explicitly choose an evidence-supported native-support statistic or change the contract with owner approval, not silent interpolation, splitting, per-source shifting or gap compression. Modeled M01 samples remain labeled point estimates, not continuous observations. The previous unshifted E formula is a draft superseded by this conditional phase-aware candidate only.

If ±20 mm were a justified bound for every eligible D12 native measurement of the selected estimand, a convex block mean would retain a conservative ±20 mm error bound, and a difference would have ±40 mm by the triangle inequality; equality at 40 mm is unresolved. This is a conditional calculation, not a calibrated hard limit or production threshold. The published value is estimated accuracy, not a guarantee; support, station effects and revisions must be addressed. Do not divide by sqrt(5) absent independence and an appropriate statistical model. Prior ±20 mm stress tests remain exploratory.

### Other source evidence and action boundary

- D26: [Oulu terms/corrections](https://cosmicrays.oulu.fi/readme.html) specify the pressure coefficient -0.74%/mb; [station metadata](https://www.nmdb.eu/station_information/OULU_1964-04-01.html) lists a claimed barometer accuracy of 0.1 mb and nominal solar-minimum count rate 115/s. At fixed coefficient a hypothetical 0.1 mb error yields exp(0.00074)-1 ≈ 0.074% relative pressure-correction error, not total corrected-rate uncertainty. This is not a new Poisson estimate or proof of calibration at the selected epochs; reuse existing counting diagnostics. Need actual exposure, correction provenance, temporal covariance and QC.
- D06: [USGS API](https://www.usgs.gov/tools/web-service-geomagnetism-data) supports BOU F, R0 internet variation and 1-s cadence. [USGS product overview](https://www.usgs.gov/tools/geomag-plots) distinguishes uncorrected variation from calibrated archive products. Neither establishes native F R0 measurement support or error bounds. Do not transfer adjusted/definitive specifications.
- D02/D03: official OSPO search-indexed notices [Nov 12 MAG calibration](https://ospo.noaa.gov/data/messages/2026/11/MSG_20261112_1402.html) and [Nov 20 SOLAR-1 distribution update](https://ospo.noaa.gov/data/messages/2026/11/MSG_20261120_1334.html) indicate operational exceptions exist. Full notice retrieval failed in this review; do not infer affected exact periods, current availability or the September flag cause. Provider QC and version-specific support remain blocked.

### Provider-ready minimum questions (unsent)

Use one bounded request per product/team, referencing the actual candidate identity. Describe the application as a research-stage symbolic representation of physical change, not forecasting or a safety-critical service. No commercial scope or permission assumed.

| Team | Questions that can close specific gates |
|---|---|
| NOAA CO-OPS ([Stakeholder Services](https://tidesandcurrents.noaa.gov/contact.html), Tide.Predictions@noaa.gov) | For station 9414290 preliminary MLLW six-minute API: actual primary sensor/model/location and handover history; exact support and label convention; outlier-count eligibility and sigma provenance (prior constant 62 mm); short-interval difference accuracy/calibration; preliminary release/revisions and outages. |
| USGS Geomagnetism ([program contact](https://www.usgs.gov/programs/geomagnetism/connect)) | BOU F R0 1-s: native scalar origin and sampling/averaging support, clock convention, invalid flags/sentinels, changes of calibration and short-interval differential error, release/revision contract. |
| Oulu / NMDB (Ilya.Usoskin@oulu.fi) | OULU original MCORR_E: exposure/raw count mapping, exact interval labels, applied pressure/efficiency corrections and QC, short-interval rate-difference uncertainty and revision/delay; permitted noncommercial app/derived-only outputs and commercial permission process if applicable. |
| NOAA MAG / SWiPS | Reuse exact-version questions in [provider_questions.md](../solar_wind/provider_questions.md). Add availability/operational notice and native support questions; do not infer minute validity or substitute L2. |

M01 needs no repeat of the completed exploratory vector diagnostics; define relevant model-difference error scope at contract review. Stop desk research on the listed provider questions unless new authoritative evidence is received. No email sent. Next: owner review of phase-aware candidate and use scope, provider answers, then freeze/evaluation only if gates pass. Formal qualification remains 0/6, P3 OPEN, BT-C sealed, P4/P5 not started. No production code changed.

## P3 engineering gate review and provider outreach preparation — 2026-11-28

Decision: identify the minimum new engineering boundary, validate its mathematical condition without provider data, and prepare the outstanding evidence requests. No model freeze or production implementation.

### Engineering boundary and bounded synthetic check

Inspected iching.py blob 7440256aaac7a1c760f66c900d4ad0cdd3bec06a and sources.py blob e36ba43925d2b95c42aacc8e209bdfd2aba210f0. Existing line_from_trend compares Decimal values and rejects exact ties; it does not implement a calibrated error gate. physical_candidate_from_trends explicitly accepts synthetic fixtures only, checks ordered non-overlapping completed supports but does not require common contiguous support across domains, source qualification or calibrated bounds; it deliberately returns ready_for_cast=false. Preserve that P2 interface and do not relabel it as P3 validation. The future P4 path must validate identity, QC, support, availability and difference-specific bounds before calling the existing line_from_trend and cast_from_lines. No changes to shared R-Trend or Quantum/MPH.

Bounded algebra check executed in a transient JavaScript isolate: all triples x_i in {-2,-1,0,1,2} and nonnegative block error bounds u_i in {0,1,2}, using exact small integers. Compare sign gate d1=x1-x0, U1=u0+u1 and d2=x2-x1, U2=u1+u2 against an independent enumeration of all eight corner assignments of (e0,e1,e2) in [-u0,u0] x [-u1,u1] x [-u2,u2]. The oracle requires a single strict nonzero sign pair at every corner. Because each difference is affine, extrema occur at corners, including zero boundary cases. Shared middle error is kept consistent across differences. Result: 3375/3375 agreement, 0 mismatches, 410 resolved and 2965 unresolved; line counts 6=183, 7=22, 8=22, 9=183. Counts are synthetic diagnostics, not cast-frequency estimates or tuning criteria. This verifies the conservative rectangular-bound rule only; no statistical coverage assumption, actual-source error estimate, or executed Python implementation is claimed. Stop this algebra check; P2 assembly was already accepted and does not need repetition.

P4 interface acceptance (draft): unknown/missing/nonfinite/negative bounds, exact equality, failed source QC, incomplete/overlapping/misaligned support, stale or unavailable-by-anchor evidence, or identity/version mismatch must not reach six-line assembly. Distinguish malformed configuration/execution errors from legitimate unresolved observations. When the provider supplies justified difference-specific bounds directly, use those rather than forcing a sum of absolute bounds. Do not insert guessed defaults. Exact arithmetic and numeric representation must be reviewed during actual integration. M01 still requires an error scope appropriate to the modeled direct radial quantity, not a full gravimeter uncertainty model. No new ephemeris studies in this checkpoint.

### Ready-to-review external inquiries (UNSENT)

The following concise drafts and the two exact-version solar drafts in [provider questions](../solar_wind/provider_questions.md) are the next actionable evidence requests. No messages sent, no account accessed, no affiliation or commercial commitment asserted. Recipient contacts were checked against official public pages where retrievable. Personal project only; no employer data, raw observation attachments or sealed dates included.

**D12 — NOAA CO-OPS**

To: Tide.Predictions@noaa.gov (official [Stakeholder Services](https://tidesandcurrents.noaa.gov/contact.html), general oceanographic product/data inquiries)

Subject: Station 9414290 preliminary water level — measurement support and short-term accuracy

Dear CO-OPS Stakeholder Services,

I am developing an independent research project that represents changes in natural observations as symbolic patterns, not as a forecast. I would appreciate clarification on the preliminary six-minute MLLW water-level product for station 9414290.

1. Which primary sensor and deployment produced this API product in September 2026 and currently? Does its timestamp denote the center of the measurement interval, and what are the exact interval boundaries?
2. What outlier-count eligibility rule and sigma interpretation apply to preliminary records? In previously inspected records, sigma was consistently 0.062 m; is this expected for the relevant product?
3. Is there a documented short-term differential accuracy or uncertainty for differences between adjacent 30-minute averages of native measurements? How should datum shifts, calibration changes and preliminary quality flags be handled?
4. What are the normal publication delay, revision behavior, and recommended way to identify records available at a given time?

A reference to existing documentation or the appropriate technical contact would be very helpful. Thank you for your time.

**D06 — USGS Geomagnetism**

To: klewis@usgs.gov (program group leader, [official program contact](https://www.usgs.gov/programs/geomagnetism/connect); request routing to product expert)

Subject: Boulder BOU F R0 one-second data — native support and quality

Dear USGS Geomagnetism team,

I am working on an independent research project representing short-term changes in natural observations. Could you direct me to the documentation or technical contact for BOU native scalar F, R0 internet variation data at one-second cadence?

Specifically, I would like to confirm the native scalar measurement origin, exact time support and timestamp convention, invalid values and QC rules, calibration discontinuities, and any documented uncertainty applicable to differences of adjacent 30-minute averages. Is there a documented operational publication/revision policy for this product? I understand that R0 is not definitive or adjusted data and do not intend to apply definitive-product accuracy to it.

Thank you for your assistance.

**D26 — Oulu neutron monitor**

To: Ilya.Usoskin@oulu.fi ([Oulu station data contact](https://cosmicrays.oulu.fi/), [terms](https://cosmicrays.oulu.fi/readme.html))

Subject: OULU MCORR_E one-minute data — support, uncertainty and intended use

Dear Dr. Usoskin,

I am developing an independent research-stage application that converts natural physical changes into symbolic patterns for reflection. It does not claim to forecast physical events or personal outcomes.

For the OULU original MCORR_E one-minute NMDB product, could you clarify the exact interval label and effective exposure, the relationship between raw counts and corrected rates, applicable QC and pressure/efficiency corrections, and any uncertainty guidance for differences of adjacent 30-minute averages? Is the publication and revision behavior documented?

I also want to ensure the intended use respects Oulu and NMDB terms. Would a public noncommercial application displaying derived symbolic outputs and proper attribution, without redistributing raw records, be permitted? If a commercial version were considered in the future, what permission process would apply? No commercial permission is assumed.

Thank you for your guidance.

### Stop and handoff

External product-specific evidence remains the critical path. Owner review of intended-use scope, time/support and encoder candidate still required. The drafts are prepared for review, not sent; no additional search for the same questions unless new evidence appears. No new independent data, no BT-C access, no production code, no readiness change. P3 OPEN / 0 of 6 qualified / P4 and P5 not started.

## P3 remaining decision boundary — 2026-11-28

- M01 is a model-defined geometric direct radial acceleration, not an instrument observation or complete Earth tide. The [480-epoch independent exported-vector replay](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7236148998) completed its fixed numerical scope (max gravity replay discrepancy 5.20739e-10 microGal against 1e-6 microGal arithmetic tolerance). Do not promote that tolerance to a physical-model bound. No requirement to model elastic response or ocean loading for this estimand. Retain the pinned site/kernel/frame/time definition; only remaining uncertainty relevant to the selected model and common observation contract is in scope. The earlier pending replay text is historical.
- New G8 evidence for M01: [official NAIF planetary directory](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/) lists de440s.bsp, and [official checksums](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/aa_checksums.txt) list MD5 3917ee56769db332790c751e2168843d. This is a separate provider identity check to perform against local bytes at release, not a substitute for the existing SHA256 pin or a verified local MD5. [NAIF rules](https://naif.jpl.nasa.gov/naif/rules.html) allow use, including commercial use under stated terms, and unmodified kernel redistribution; acknowledge producers, do not imply endorsement or support. [Skyfield 1.55](https://pypi.org/project/skyfield/1.55/) declares MIT; [jplephem project](https://github.com/brandon-rhodes/python-jplephem/) declares MIT and [2.24 packaging evidence](https://github.com/macports/macports-ports/blob/master/python/py-jplephem/Portfile) corroborates. The exact installed distribution license files and full transitive dependency notices remain release checks; no new download, hash calculation or dependency change. G8 evidence strengthened, not blanket app approval.
- For the five observed products, the last outreach-ready drafts already specify missing evidence; no further desk review or new retrospective captures are justified without new evidence. Recommended initial intended-use scope for owner decision: independent noncommercial research and derived-only public reflection output, no raw-data redistribution; future monetization separate. This is a proposal, not owner approval or provider permission. Do not silently relax scientific uncertainty, replace a source or authorize public release.
- Next action is owner authorization of intended-use scope and whether to send the five prepared requests. No external mail sent. No need for local owner reruns. P3 remains OPEN / 0 of 6 qualified, BT-C sealed, P4/P5 not started. Report blocked rather than generating additional routine research commits while awaiting evidence.

## P3 provider outreach sent — 2026-11-28

Owner authorized proceeding after the noncommercial scope/outreach proposal. Initial scope: independent noncommercial research; any public derived-only application remains subject to applicable terms and provider evidence. No commercial authorization assumed.

All five prepared inquiries were sent individually from the owner's connected mail account on 2026-11-28; each send returned a SENT result. Contacts rechecked against official sources before sending, including MAG L3 metadata via indexed official content. Messages retained the prepared technical questions and added explicit identification of TRNG I Ching as I Ching-inspired symbolic research for personal reflection without predictive-validity claims. No attachments, employer information, raw data, or BT-C material sent. Earlier UNSENT sections are retained as historical drafts, superseded by this status.

| Domain | Provider | Inquiry | Status |
|---|---|---|---|
| D12 | NOAA CO-OPS | Station 9414290 preliminary water level — measurement support and short-term accuracy | SENT / response pending |
| D06 | USGS Geomagnetism | Boulder BOU F R0 one-second data — native support and quality | SENT / response pending |
| D26 | University of Oulu | OULU MCORR_E one-minute data — support, uncertainty and intended use | SENT / response pending |
| D03 | NOAA NCEI MAG | SOLAR-1 operational MAG L3 — flag interpretation and minute scalar QC | SENT / response pending |
| D02 | NOAA NCEI SWiPS | SOLAR-1 SWiPS operational L3 — moment QC, support and availability | SENT / response pending |

SENT confirms submission through the mail account, not recipient delivery or provider approval. Keep private mailbox identifiers and correspondence out of Git. For each substantive response, record product/version scope, official reference, supported gate change and unresolved items; do not publish private correspondence without permission. No duplicate requests or routine re-captures while awaiting evidence. M01 numerical replay remains completed within its existing scope; remaining model/contract evidence is separate. P3 OPEN / 0 of 6 qualified / BT-C sealed / no live enable or model freeze. P4/P5 not started.

## Experimental implementation scope — owner-directed convergence

The owner directed proceeding with available public data without requiring provider replies or calibrated uncertainty as a prerequisite. This supersedes earlier readiness gating for experimental local research. Profile physical-rtrend-label-mean-v0.1 retains the six quantities and order, uses existing NOAA operational RTSW JSON instead of the retrospective daily L3 files, and uses three fixed UTC 30-minute native-label means with a fixed 30-minute lag before flooring. Require complete unique eligible labels and two nonzero changes per domain. No continuous-support reconstruction, calibrated difference bound, fallback or QRNG. Prior qualification remains historical; formal scientific and commercial/public redistribution approval are separate. Deleted temporary datasets need not be restored; any later reacquisition is a new snapshot. No BT-C access. Live owner smoke and regression pending.

**Live profile v0.2:** D06 uses INTERMAGNET/BGS IAGA-2002 native BOUF minute observations (same USGS Boulder station and scalar quantity), after repeated USGS direct API timeout/404 and successful owner BGS HTTP 200 in 2.917453 s. Provisional values accepted, 99999/88888 placeholders excluded, all 90 labels required. UTC date-spanning requests cover both dates if needed. Earlier D06 one-second research adapter retained for historical use; live source and cadence explicitly versioned, other quantities and R-Trend unchanged. Full live smoke PASS on 2026-11-28 (owner Windows run; see below).

### Physical v0.2 live acceptance smoke — PASS

Owner Windows live run, 2026-11-28 15:49:08 UTC (23:49:08 UTC+8), code baseline c21e9aa. Fixed label window [13:30, 15:00) UTC. D12 15/15, M01 15/15, D06 90/90, D26-NEST 90/90, D02 90/90, D03 90/90; all candidate_resolved (375 total labels). INTERMAGNET returned 1440 rows and selected all 90 required eligible BOUF labels. Six-line assembly, reference context, record validation, Human View and local classical text completed. This demonstrates experimental P4 end-to-end functionality on the observed window, not general availability or scientific predictive validity. P5 three-method regression pending; no additional precision study or provider-response prerequisite. No raw observation archive or individual cast record saved by this documentation update.

## Evidence references

- [Prior G1–G8 review](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7211017000)
- [D06 seasonal and continuity](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7213956226)
- [D26 slow background](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7214291417)
- [SOLAR-1 official document review](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7219326431)
- [Production evidence contract](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7219755032)
- [L2/L3 bridge](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222127629)
- [Uncertainty stress](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222184629)
- [Tide residual](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222341927)
- [Candidate comparison](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222396402)
- [Timescale](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222490785)
- [NOAA SOLAR-1](https://www.ncei.noaa.gov/products/space-weather/swfo)
- [USGS product definitions](https://www.usgs.gov/tools/web-service-geomagnetism-data), [adjusted data validation](https://www.usgs.gov/publications/adjusted-geomagnetic-data-theoretical-basis-and-validation)
- [NMDB usage terms](https://www.nmdb.eu/nest/statements.html)
- [NOAA 9414290 datums](https://tidesandcurrents.noaa.gov/datums.html?datum=MLLW&epoch=0&id=9414290&units=1), [API](https://api.tidesandcurrents.noaa.gov/api/dev/)
- [JPL Horizons manual](https://ssd.jpl.nasa.gov/horizons/manual.html)

## Rechecked artifact digests (SHA256)

| Local artifact | SHA256 |
|---|---|
| PH_BT_september_capture_v01.zip | 5b1cbb91618b69941194d7732e1e2ef097b0b9a1e82160a7765ee00d11e27d4c |
| PH_BT_september_supplement_v01.zip | a45409520294d92b06926698a9d409ef357ecf16959695827a9cacc8e22daea3 |
| PH_BT_september_D26_v01.zip | 06910270e8242f59fb51ada8af7cbb30af4dabfcded9afe85014841f5cd1f5fe |
| PH_BT_swips_l2_capture_v01.zip | 7175fa28e9bd8dd29257301779cee970bfd9742eaf4d1e45f86815ae5cc05194 |
| PH_BT_tide_background_v01.zip | dd1bef739c2b17d8ce92516f0d6f124a71af2a2cc26de78d832eb5c023b278d3 |
| physical_background_result_v01.json | 6511fd0349408736c8819e75fb80f28037223c37300237338042c94aa76db9ec |
| physical_uncertainty_result_v01.json | 1d3a38c3a82bd1453aa31a61dadf2a042ab155dac2f6e50686c2bbb65c451410 |
| physical_model_compare_result_v01.json | 96594e3f9a98c6171ec889d564552917d79cf6976614d05caf20ae1a33ba02c3 |
| physical_timescale_result_v01.json | d09146953b2ddf18156d5aa71a09cac0851f7b577508100ad148da55bdb7073f |
| physical_tide_residual_result_v01.json | d23548b6627d9776b77aeef42003a0d7fcfb320f2d2410c5d73081da1e6a4742 |
| physical_time_support_result_v01.json | ae79c3cc48069503b00af34873f5fdc762bf745e19f74c2777892dae8c9e572d |

Acknowledgment: NMDB database (www.nmdb.eu), EU FP7 contract 213007, and the Oulu neutron monitor PIs, Sodankyla Geophysical Observatory, University of Oulu, Finland. Only aggregate evidence and references are recorded here.

觀象，察變，求真，思己。
