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

**Shared runtime diagnostics:** Windows/urllib transport failures now carry a safe code (`http_error`, `request_timeout`, `connection_failed`, or `invalid_response`); HTTP status and Wood component identity are surfaced in no-hexagram outcomes when known. Wood logs per-request latency, payload size and missing session/contract details. Existing acquisition counts, source selection, no-retry/no-fallback policy, observation schedules, R-Trend and exit-status behavior remain unchanged. Static diff verified; owner Windows compile and three-method happy-path live regression PASS (2026-11-29 00:28 UTC+8, baseline ead7824). MPH five domains resolved; six HTTP requests including QRNG succeeded; TWSE 0.295479 s, TAIFEX 0.314235 s, total reported request time 6.207205 s. Wood selected values matched prior successful run. Failure classifications have not been exercised by this successful run; provider uptime is not established. Close basic runtime-diagnostics acceptance. Owner clarified that this is a personal research and casting tool, not a product. App architecture, framework selection, App development, distribution, commercial release and App-specific API refactoring are outside the current scope. Maintain the existing Python CLI, three casting methods, classical references and concise human/JSON outputs. Further changes should address concrete research or usage needs rather than speculative product requirements.

## Information dynamics — exact structural baselines (2026-11-29)

Current scope is personal research using the three working CLI methods. Do not recover deleted artifacts, rerun D3/D4, reopen source precision studies, or develop product interfaces. Earlier readiness statements below are historical. Issue #3 remains the source-evidence record; #4 is the symbolic-information research track. Experimental Physical v0.2 and MPH contract v0.3 are live-smoke accepted.

### Four-state alphabets

For fair independent bits, the three-coin line probabilities in order (6,7,8,9) are (1,3,3,1)/8. For three IID continuous levels, enumerate their six equally likely ordinal permutations under the existing R-Trend mapping: (2,1,1,2)/6. For independent symmetric nonzero increments (a distinct null model), all four states have probability 1/4. These are hypothetical analytical baselines, not empirical distributions for the actual sources. No frequency balancing or model changes.

| Baseline | Line entropy (bits) | Moving-line probability |
|---|---:|---:|
| Fair three-coin | 1.811278 | 1/4 |
| IID continuous levels / R-Trend | 1.918296 | 2/3 |
| Independent symmetric nonzero increments / R-Trend | 2 | 1/2 |

If lines are mutually independent under their respective nulls, joint entropy is 10.867669 bits for Quantum, 11.402757 for MPH with five IID-level R-Trend lines and one fair quantum line, and 11.509775 for six IID-level R-Trend lines. Expected moving counts are respectively 1.5, 43/12 (3.583333), and 4. These are conditional on the artificial independence assumptions; actual line dependence and time dependence are unmeasured. Alphabet capacity 12 bits is not entropy. Given all resolved deterministic source inputs, Physical has zero conditional entropy; MPH has 1.811278 bits from its independent ideal quantum top line, conditional on the five resolved inputs and a successful draw. Unconditional observed entropy can be nonzero in both.

### Temporal transitions for a shared increment

Let consecutive R-Trend triples be (a,b,c) and (b,c,d). The second sign of the first line is exactly the first sign of the next. For nonzero changes this allows only 8 of 16 directed line transitions (including self-transitions). Exact enumeration of all 24 ordinal permutations of four IID continuous levels gives joint transition counts:

| From / To | 6 | 7 | 8 | 9 |
|---|---:|---:|---:|---:|
| 6 | 0 | 3 | 0 | 5 |
| 7 | 0 | 1 | 0 | 3 |
| 8 | 3 | 0 | 1 | 0 |
| 9 | 5 | 0 | 3 | 0 |

Divide entries by 24 for joint probabilities, or by row totals for one-step conditional probabilities. Same-code probability = 2/24 = 1/12. Conditional one-step entropy = 0.906715 bits, not a proven entropy rate or Markov model. This algebraic constraint applies only where the next actual selected triple shifts by exactly one observation and preserves both shared values. Repeated identical windows are deterministic; non-overlapping or revised windows are different cases. Current MPH domains may advance on different grids, Wood on completed market events, and Physical uses fixed half-hour block means. Do not force cross-domain synchronization. Within the applicable shared-window case, a reversal line (6 or 9) must transition to a different line. None of this establishes predictive power about external events.

### Hexagram transition graph — exact structural checkpoint

Represent a primary hexagram as a bottom-to-top six-bit vector P and its relating hexagram as R. Each four-state line maps bijectively to the pair (P_i,R_i): 6=(0,1), 7=(1,1), 8=(0,0), 9=(1,0). Exhaustive independent Python enumeration of the four-state product (4^6 = 4096) gives all 64 x 64 ordered pairs exactly once. Hamming distance d(P,R) equals moving-line count. The single-line-change graph is the six-dimensional hypercube Q6: 64 vertices, degree 6, 192 undirected edges. Its distance shells per vertex have sizes (1,6,15,20,15,6,1). Allowing multiple simultaneous changes gives 4096 ordered pairs including 64 self-loops; this is an intra-cast graph, not an observed temporal graph. King Wen numbers are labels rather than coordinates or metric distances.

For independent lines, the intra-cast Hamming-distance generating polynomial is the product of ((1-p_i)+p_i z), with p_i the moving probability. Under the earlier ideal nulls the three polynomials are ((3+z)/4)^6 (Quantum), ((1+2z)/3)^5 (3+z)/4 (MPH), ((1+2z)/3)^6 (Physical). The exact coefficient distributions from rational polynomial convolution are:

| Moving count | Quantum % | MPH % | Physical % |
|---:|---:|---:|---:|
| 0 | 17.79785 | 0.30864 | 0.13717 |
| 1 | 35.59570 | 3.18930 | 1.64609 |
| 2 | 29.66309 | 13.37449 | 8.23045 |
| 3 | 13.18359 | 28.80658 | 21.94787 |
| 4 | 3.29590 | 32.92181 | 32.92181 |
| 5 | 0.43945 | 18.10700 | 26.33745 |
| 6 | 0.02441 | 3.29218 | 8.77915 |

These are IID-level R-Trend and fair-bit null distributions, not measured frequencies or an objective for model tuning.

**Temporal bridge identity.** For R-Trend on (a,b,c), P_i = 1[b>a], R_i = 1[c>b]. If the next resolved triple is exactly (b,c,d) with the same shared values, then P_i(t+1) = R_i(t). Thus when all six physical lines advance by exactly one shared-increment step, the previous relating hexagram equals the next primary hexagram. This is an algebraic identity independent of probability assumptions, not prediction of the next measurement or of external events. It requires nonzero increments and identical overlapping values; it is not valid for arbitrary casts. A repeated identical window instead has P(t+1)=P(t), R(t+1)=R(t). With revisions, missingness, different sampling grids or larger shifts, the bridge is not assured.

For each line shifted by one observation, exactly two four-state successors are structurally possible (8 of 16 directed edges); an unconstrained quantum line allows four. If all deterministic domains shift exactly once and all combinatorial possibilities are allowed, a current four-state six-line vector permits the following maximum successor counts:

| Framework | Next four-state vectors | Directed edges over 4096 states | Next primary hexagrams |
|---|---:|---:|---:|
| Quantum, independent new entropy | 4096 | 16777216 | 64 |
| MPH, all five observed triples shifted once | 128 | 524288 | 2 |
| Physical, all six triples shifted once | 64 | 262144 | 1 |

Actual support can be smaller due to dependence, no-hexagram outcomes or source constraints. For partial shifts apply the bridge only to shifted lines; unchanged deterministic triples retain their original line; no forced synchronization. In Physical v0.2, a 30-minute forward block-window shift with unchanged shared block means meets this condition. In MPH v0.3 the market events, exact 30-minute endpoint spacing and native labels make such a simultaneous shift non-guaranteed. Quantum top line is not subject to the R-Trend bridge.

Even IID continuous levels do not establish a first-order Markov process for sign sequences: P(next positive | last positive) = 1/3, but P(next positive | last two positive) = 1/4 (strict monotone order probabilities 1/6 and 1/24 respectively). Do not raise a fitted one-step transition matrix to powers as a validated temporal forecast. The intrinsic Hamming graph and the temporal four-state graph must be kept distinct.

### Information persistence — exact overlap baselines (2026-11-29)

Let L_t be R-Trend of three consecutive levels and L_(t+k) the shifted triple. Enumerate all ordinal permutations of 3+k IID continuous levels for k=0,1,2,3 (6,24,120,720 cases, respectively). Equal permutation weights follow from the IID continuous assumption. Independent Python enumeration used the existing sign-to-line map. Joint count matrices in line order (6,7,8,9) are diagonal (2,1,1,2) for k=0; the 24-count matrix above for k=1; and for k=2:

| From / To | 6 | 7 | 8 | 9 |
|---|---:|---:|---:|---:|
| 6 | 16 | 4 | 9 | 11 |
| 7 | 9 | 1 | 6 | 4 |
| 8 | 4 | 6 | 1 | 9 |
| 9 | 11 | 9 | 4 | 16 |

At k=3 the 720-count matrix is the outer product of (2,1,1,2) with itself times 20. The marginal H(L)=1.918295834 bits in all cases. I(L_t;L_(t+k))=H(L_(t+k))-H(L_(t+k)|L_t); this is statistical information about the next encoded line, not a proportion of the original physical information or a causal effect.

| Shift k | Shared levels | Conditional entropy (bits) | Mutual information (bits) | Same-code probability |
|---:|---:|---:|---:|---:|
| 0 | 3 | 0 | 1.918295834 | 1 |
| 1 | 2 | 0.906715377 | 1.011580457 | 1/12 |
| 2 | 1 | 1.811558548 | 0.106737286 | 17/60 |
| >=3 | 0 | 1.918295834 | 0 | 5/18 |

Normalized mutual information I/H is 100%, 52.733%, 5.564%, 0%. Equality probability and mutual information are not equivalent; shared-increment reversal constraints can make repeated symbols rare despite dependence. A single shared level still induces dependence through its ordinal rank. Disjoint levels are independent only under the stipulated IID null; real physical and market processes may retain memory. A separate symmetric IID-increment null yields two independent fair sign bits per line and mutual information (2,1,0,0) for k=(0,1,2,>=3); do not confuse this with IID levels.

For six mutually independent line processes under the IID-level null, joint mutual information is additive; Quantum with independent fresh samples contributes zero between casts, MPH contributes the sum of its five observation-line terms, Physical the sum of its six. For an ideal common shift k:

| Shift | Quantum bits | MPH bits | Physical bits |
|---:|---:|---:|---:|
| 0 | 0 | 9.591479 | 11.509775 |
| 1 | 0 | 5.057902 | 6.069483 |
| 2 | 0 | 0.533686 | 0.640424 |
| >=3 | 0 | 0 | 0 |

No claim of independent actual domains, empirical entropy rate, or forecasting accuracy.

**Actual schedule interpretation (static runtime inspection).** Physical v0.2 selects three 30-minute bins ending at floor_30min(anchor-30min). If shared block values are unchanged, compare the two selected window ends, not merely cast timestamps: difference 0/30/60/>=90 minutes corresponds to k=0/1/2/>=3. MPH Metal, Water, Fire and Earth use exact selected labels (t-60min,t-30min,t); their latest label may move by a native increment much shorter than 30 minutes. A 1- or 6-minute endpoint shift can therefore share no exact labels while the overall observation spans overlap substantially. The overlap permutation null is not a calibrated model of those time-separated observations. Exact 30-/60-minute selected-label shifts share two/one labels, respectively, assuming unchanged values. Wood advances by completed cash/night events, not fixed elapsed intervals. Classify each domain separately; only identical values/identities establish deterministic persistence, and revised source data invalidate the shared-value bridge. No-hexagram outcomes remain outside the four-state alphabet. Do not count repeated windows as independent natural-observation samples; repeated use of the CLI itself remains allowed under the existing guard.

### Cross-domain information coupling — bounded analytical checkpoint

Reopened existing evidence rather than reconstructing removed input archives:
- [Water/Earth 24-hour probe](https://github.com/cctsao1008/trng-iching/issues/3#issuecomment-7177522383): SF water-level differences versus same-site modeled radial differential acceleration, Pearson r at 6/30/60/180 min = .460117/.521271/.523389/.524458 (all preliminary parsed records, exact pair counts 240/236/231/211). With the same SF water series and Taiwan radial model: .139563/.166247/.175902/.185063. This is a local descriptive comparison, not independent observations of gravity, a causal estimate, or a measured mutual-information result.
- [Solar coupling replay](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7234128136): two inspected dates, P1 30-minute blocks (41/39 complete blocks, 38/32 adjacent increments); magnetic pressure vs proton thermal pressure level r=.543688/-.077588, increment r=-.134006/-.380742. Magnetic pressure is B²/(2μ0), not the runtime Metal observable Bt itself. P1 historical screening is distinct from current runtime QC. No fixed correlation sign, pressure equilibrium, or long-term conclusion. The two source domains describe a common plasma environment; water and Earth share astronomical forcing but ocean response is not a direct measurement of radial acceleration.

**Independent-in-time Gaussian increment toy model.** At each of two successive intervals, paired domain increments (X_j,Y_j) are zero-mean nondegenerate jointly Gaussian, with correlation rho, and pairs across intervals are independent. This is an IID-increment model, not the IID-level null above, not a fit to the source records, and not a calibrated model of actual domains. The sign mismatch probability is q=acos(rho)/pi (Gaussian angular symmetry). Each sign is fair; one interval contributes 1-h2(q) bits of mutual information, where h2 is binary entropy. Since the two intervals are independent and R-Trend is bijective on the two sign bits, I(L_X;L_Y)=2[1-h2(q)]. Same-line probability is (1-q)^2; complementary-line probability is q^2 (6↔9, 7↔8). At rho=±1 use the limiting perfectly dependent case.

| rho | Sign mismatch q | Line mutual information (bits) | Same-line probability |
|---:|---:|---:|---:|
| 0 | .500000 | 0 | .250000 |
| .25 | .419569 | .037494 | .336900 |
| .50 | .333333 | .163408 | .444444 |
| .75 | .230053 | .443791 | .592818 |
| .90 | .143566 | .812994 | .733479 |
| 1 | 0 | 2 | 1 |

Python evaluated the closed form and independently re-enumerated the prior overlap null matrices to confirm their reported values. Negative rho has the same mutual information as positive |rho| but exchanges same and complementary tendencies. Do not substitute historical Pearson r into this formula as an empirical line MI estimate: actual increments may not be Gaussian, independent across intervals, synchronized, or symmetrically distributed.

**Six-line implication.** The joint entropy equals sum of marginal entropies minus total correlation TC = sum H(L_i)-H(L_1,...,L_6). For an illustrative four-state uniform increment null with only two independent coupled pairs (Metal/Fire and Water/Earth) and all other groups independent, joint entropy is 12-I(M;F)-I(W;E) bits. MPH with an independent fair three-coin top line instead has baseline 10+1.811278 bits before subtracting these two pair MI terms. This subtraction is exact only for the stipulated pair-factorized distribution. Pairwise MI alone cannot recover six-way total correlation. Counterexample: U,V independent uniform two-bit symbols and W=U XOR V; every pair is independent but H(U,V,W)=4 bits instead of 6. This is a mathematical illustration, not a proposed mapping or a physical claim.

**Disposition.** Existing evidence supports studying the two physical pairs; neither provides an empirical R-Trend 4x4 contingency table from the material reopened here. No six-domain joint dataset, new measured MI, inferred coupling strength, causal relation, or Five Phases correspondence established. Reuse only aligned existing data if a concrete future empirical question warrants it; do not reconstruct deleted artifacts, start routine monitoring, optimize frequencies, change source/model, or pursue product work. The structural graph, overlap-conditioned persistence and cross-domain coupling analytical checkpoints are complete. Continue using the three verified experimental methods without modification.

## Classical synthesis — Xiang, Shu, Bian, Shi and Wei (2026-11-29)

**Purpose:** Return the completed mathematical/physical investigations to the classical question of how a person observes change and responds to it. The five categories (象、數、變、時、位) are our comparative framework, not a claim that the received Yi defines an exclusive five-part taxonomy. Distinguish the Zhouyi judgment and line texts from the interpretive Yi Zhuan (Xici, Tuan, Xiang, Wenyan). This is a reading of selected received passages, not a complete textual-critical study or a proof that ancient authors anticipated information theory.

### Classical source crosswalk

| Dimension | Received-text anchor | Modern analogy and project result | Boundary |
|---|---|---|---|
| Xiang 象 — representation | [Xici I, ch. 8](https://zh.wikisource.org/wiki/易傳/繫辭上): 象其物宜; [Xici II, ch. 2](https://zh.wikisource.org/w/index.php?title=易傳/繫辭下&oldid=2611136): observation of heaven, earth, self and things | Feature abstraction: R-Trend maps two signed differences to a four-state line. This retains ordinal direction while discarding magnitude, level and intervening path. Distinct input histories can have the same symbol. | Symbolic analogy is not scientific equivalence. The whole observable cannot be reconstructed from the symbol; no physical Five Phases correspondence is demonstrated. |
| Shu 數 — numerical structure | [Xici I, ch. 10](https://zh.wikisource.org/wiki/易傳/繫辭上): 極其數，遂定天下之象 | Binary six-line alphabet 64; four-state six-line alphabet 4096; 12-bit maximum capacity; Hamming graph, theoretical distributions, entropy and total correlation characterize structure. | Capacity is not actual entropy or meaning. Traditional numerical/cosmological and divinatory interpretations are not Shannon measures; modern encoding is our construction. |
| Bian 變 — change | [Xici I, ch. 3](https://zh.wikisource.org/wiki/易傳/繫辭上): 爻者，言乎變者也; [Xici II, ch. 7](https://zh.wikisource.org/w/index.php?title=易傳/繫辭下&oldid=2611136): 變動不居 | Primary-to-relating Hamming distance equals moving-line count. The R-Trend temporal bridge is exact only for identical overlapping values shifted by one step. Information persistence and coupling show that symbols are neither necessarily independent nor uniformly distributed. | Classical change includes transformation and adaptation in human affairs. The mathematical bridge is retrospective encoding, not a universal rule of divination or a forecast. A moving line is a reversal of sampled increments, not proof that a state threshold was crossed. |
| Shi 時 — time and timeliness | [Gen, Tuan](https://zh.wikisource.org/wiki/周易/艮): 時止則止，時行則行 | Quantum uses the sample reception time; MPH uses a common request anchor with native endpoint schedules; Physical uses a fixed lagged half-hour-bin window. Identical time labels alone do not establish identical data; different domains have different update rates. | Classical timeliness includes suitability of action to circumstances, not merely clock timestamps. Calendar context and astronomical information do not dictate a quantitative casting interval or predict a fortunate event. |
| Wei 位 — position and relation | [Xici II, ch. 8](https://zh.wikisource.org/w/index.php?title=易傳/繫辭下&oldid=2611136): 二與四同功而異位，其善不同; [Qian](https://zh.wikisource.org/w/index.php?title=周易/乾&oldid=2404991): first and upper yang line judgments differ | An ordered six-component state, not an unordered bag. Permuting unequal line codes changes the primary and/or relating pair even if marginal entropy or moving count is unchanged. Physical and MPH have distinct explicitly fixed orders. | The classical position includes stages, appropriateness, and relationships (such as centrality and correspondence in traditional commentary), not only an array index. The modern domain-to-position assignments are experimental design choices, not prescribed by the Zhouyi. |

The Qian example makes the distinction concrete: all six primary polarities are yang, but the first, fifth and upper line texts describe different situations. Binary value alone does not decide meaning, auspiciousness or action. Classical line names using nine/six must not be confused with the runtime four-state codes assigning six/nine to moving lines and seven/eight to nonmoving lines.

### Synthesis: observation, symbol, interpretation and action

Observation -> declared representation -> ordered changing symbol -> classical text and actual circumstances -> human reflection and choice.

The first stages are auditable numerical operations. Interpretation is a contextual and philosophical act, and the person's judgment is not supplied by a probability distribution. The ancient texts include divinatory aspirations (for example Xici II, ch. 9, concerning knowledge of what is to come); our personal research scope neither denies that historical intent nor claims to have scientifically established it. A true random source is not evidence of a hidden channel carrying future events or the questioner's intention.

- **觀象 (observe patterns):** maintain the distinction between observation, model, entropy source and symbolic representation.
- **察變 (discern change):** distinguish internal primary/relating transformation, actual temporal evolution and contextual interpretation.
- **求真 (seek truth):** preserve source meaning and uncertainty, accept repeated or unresolved outcomes, and do not select favorable symbols or force a scientific equivalence.
- **思己 (reflect within):** let the text raise questions about circumstances, timing, role, responsibility and available action; the reader retains interpretation and decision-making.

The completed theoretical comparisons support understanding the instrument, not ranking the three methods by divinatory truth or empirical predictive accuracy. Do not infer that more entropy is more wisdom, or that continuity implies greater authenticity. Retain all three established experimental CLI methods unchanged. The main study now returns to reading the received Zhouyi and Yi Zhuan in concrete situations rather than extending statistical studies for their own sake. No new cast, source acquisition, runtime edit, archive recovery, product roadmap or prescriptive interpretation engine is needed.

## Classical reading I — Tai, Pi, Jiji and Weiji (2026-11-29)

After the five-dimension synthesis, return to the received text, using the repository's [Zhouyi corpus](../data/zhouyi.json). Reopened entries 11, 12, 63 and 64 (judgment, six lines, Tuan and Xiang). The following is a contextual comparative reading, not a new casting rule or a comprehensive commentary tradition. Preserve the corpus's original character forms in quotations. No new cast or statistical experiment.

### Tai 泰 and Pi 否 — connection and obstruction

| Hexagram | Upper/lower trigram | Bottom-to-top binary vector | Tuan's relational image |
|---|---|---|---|
| 11 Tai 地天泰 | Kun / Qian | 111000 | 天地交而萬物通也，上下交而其志同也。 |
| 12 Pi 天地否 | Qian / Kun | 000111 | 天地不交而萬物不通也，上下不交而天下无邦也。 |

Both have three yin and three yang lines; both polarity complementation and reversal of six positions take one into the other. The relationship of components matters, not merely their counts. In modern systems thinking this is an analogy to interactions, communication and organization, not a claim that the received Yi formulated network science. Tai 9.3 (无平不陂，无往不復) cautions against treating favorable conditions as permanent; Pi 9.6 (傾否，先否後喜) presents the possibility of an obstruction ending. Do not infer inevitable reversal within a fixed interval or predict a real outcome from a symbolic pair. These are adjacent received King Wen hexagrams, not an actual successive-cast record.

### Jiji 既濟 and Weiji 未濟 — completion and the unfinished

| Hexagram | Upper/lower trigram | Bottom-to-top binary vector | Judgment excerpt |
|---|---|---|---|
| 63 Jiji 水火既濟 | Kan / Li | 101010 | 初吉終亂。 |
| 64 Weiji 火水未濟 | Li / Kan | 010101 | 小狐汔濟，濡其尾，无攸利。 |

Again both have three yin and three yang lines and are related by complementation and position reversal. The Tuan for Jiji says 剛柔正而位當也 and 終止則亂，其道窮也; Weiji says 雖不當位，剛柔應也. Using the conventional odd-yang/even-yin position convention, Jiji has six corresponding polarities and Weiji none, yet this does not reduce the text to a score of six versus zero. All three corresponding pairs of lines (1/4, 2/5, 3/6) have opposite polarity in both. Jiji's Great Image advises 思患而豫防之; Weiji's Great Image advises 慎辨物居方. Completion still demands care; incompletion is a situation requiring discrimination, not synonymous with failure. A systems analogy is the distinction between a currently functioning configuration and its sustainable operation under changing conditions. It is not a theorem of engineering reliability or a forecast.

### Reflection through the five dimensions

- Xiang: examine the received image of interaction, obstruction, crossing and completion before projecting it onto a personal problem.
- Shu: equal yin/yang counts do not imply equal ordered states or meanings; retain the exact structure without assigning a goodness score.
- Bian: consider changing conditions, not an assumption of permanent success or failure.
- Shi: distinguish the present situation from readiness for action or the need to continue maintaining an achieved result.
- Wei: inspect one's role, relationships, obligations and capacity to act; position is not sufficient by itself to determine the judgment.

The four principles remain 觀象，以知萬物；察變，以明其勢；求真，以辨其理；思己，以正其行. Apply the text to a real question only with its context, actual evidence and the reader's own judgment. Do not invent a divinatory event, enforce a single interpretation, or turn the paired hexagrams into a predictive transition matrix. This chapter adds textual reflection rather than additional statistical research. The next natural reading topic is 屯/蒙 (beginnings and learning), if the owner chooses to continue. The current emblem and runtime files are unchanged.

## Historical astronomy and omen studies — owner-selected Tian Guan Shu priority (2026-11-29)

**Research direction — AI-assisted interdisciplinary synthesis (2026-11-29).** Owner-endorsed approach: use AI and modern tools to integrate classical Yi studies, historical astronomy and omenology, modern astronomy and physics, history and philology, Earth and life sciences, and information and systems science. Proceed through literature review, cross-reference, reconstruction, hypothesis development and synthesis as complementary modes. Seek agreements and contradictions, verify against independent evidence, and preserve provenance, alternative explanations and unresolved questions. AI-generated associations are hypotheses, not proof. The objective is original, revisable understanding, not accumulating summaries or repeating completed computations. Initial topics: 贏縮/見伏, 五星聚于東井 and 天人感應. See [research strategy and illustrated workflow](https://github.com/cctsao1008/trng-iching/issues/7#issuecomment-7243764560), including the owner's original statement. Existing three casting methods and personal CLI research scope remain unchanged.

> 究天人之際，通古今之變，成一家之言。
>
> 以古典文獻為根，以現代科學為器，以 AI 為研究助手，以求真為目的。

Active reading and research log: [Issue #7](https://github.com/cctsao1008/trng-iching/issues/7). TC-01B textual reading: [four palaces, mansions and terrestrial divisions](https://github.com/cctsao1008/trng-iching/issues/7#issuecomment-7243443543). Subsequent primary-text notes are recorded in that issue.

**TC-01A–TC-06 initial thematic reading complete.** See [illustrated synthesis](https://github.com/cctsao1008/trng-iching/issues/7#issuecomment-7243588705). The owner PDF's 124 passages have been covered by thematic reading. Explicit planetary Five Phases correspondences are historical; current MPH proxies, six-line order and R-Trend are experimental. Distinguish trend reversal, reference-relative departure and anomaly; preserve the existing three methods. The prior planetary-motion replay remains the bounded numerical result, not a short-cadence replacement. Recommended next concrete question: reconstruct the historical meanings and reference conventions of 贏縮 and 見伏 before any further numerical or model decision. The §73 discrepancy, historical star identifications and celestial-human hypotheses remain unresolved.

The owner prioritizes Sima Qian's Shiji, chapter 27, Tian Guan Shu (史記・天官書) over Yisi Zhan as the primary reference for historical observation and metaphysical research. Supersede the proposed routine paired-hexagram philosophical reading sequence as the active direction. Start with the source text, not new casting rules.

- Owner-provided preferred reading text: [Chinese Text Project — Shiji, Tian Guan Shu](https://ctext.org/shiji/tian-guan-shu/zh). Direct web retrieval initially returned HTTP 403; the owner subsequently supplied a 26-page PDF print, enabling the full initial thematic reading. Edition collation remains outstanding; Wikisource is a separately identified auxiliary text.
- Received text: [Wikisource, chapter 27, revision 7904116](https://zh.wikisource.org/w/index.php?title=史記/卷027&oldid=7904116); [Shiji Jijie, chapter 27](https://ctext.org/wiki.pl?chapter=744666&if=en). Distinguish Sima Qian's text from later 集解、索隱、正義 annotations and textual variants.
- Historical study: [史家的天官傳統─《史記》中的天官星占傳承](https://ndltd.ncl.edu.tw/cgi-bin/gs32/gsweb.cgi?o=dnclcdr&s=id%3D%22102NCHU5493010%22.&searchmode=basic).
- Initial textual anchor: 太史公曰 passage distinguishes ordinary planetary retrograde motion and regular celestial phenomena from changes deemed beyond normal bounds (凡天變，過度乃占). This is historically situated observation and omen reasoning, not a calibrated modern anomaly detector. The same text also advances celestial-human correspondences and retrospectively pairs celestial events with political affairs; neither celestial calculation nor historical pairing alone establishes predictive validity.
- Reading sequence: celestial organization (five palaces, stellar offices, lunar mansions and Dipper); Sun/Moon and five planets (appearance, motion, normal course, 贏縮); exceptional celestial and atmospheric phenomena; division of terrestrial regions and omen interpretation; historical cases and the author's concluding method. Compare with modern astronomical observables only after identifying the original term, historical reference frame and interpretation. Yisi Zhan and Kaiyuan Zhanjing remain secondary comparative references, not the active starting point.

No new statistical experiment, acquisition, cast, model adjustment or product development. This is a research-direction decision and initial passage review, not a completed chapter-by-chapter reading.

## TC-01 — Tian Guan Shu: central palace, Taiyi and the Northern Dipper

Primary reading source: owner-provided PDF print of [Chinese Text Project, Shiji, Tian Guan Shu](https://ctext.org/shiji/tian-guan-shu/zh), printed 2026-11-29 01:56 Taiwan time, 26 pages, numbered paragraphs 1–124, SHA256 `6537c80a68af3f059a2739c4b25dc20ed4a8e5319196c15302ad3c3d013bdfe4`. The Chinese text is primary; the page labels the English translation as AI/user-assisted, and it is not independent scholarly corroboration. The owner-supplied PDF resolves access to this reading text but not the edition-collation question. Do not redistribute the PDF; cite paragraph and page numbers and the original URL.

### Reading checkpoint

- §§1–2, p.1: central palace, Tianji, Taiyi and Zigong establish a celestial center and a surrounding star-office order analogous to the imperial court. Do not identify the ancient Tianji/Taiyi star with present-day Polaris without historical star identification and epoch evidence.
- §3, p.1: Northern Dipper (北斗七星), 杓、衡、魁 and 昏、夜半、平旦; 斗為帝車 and 分陰陽、建四時、均五行、移節度、定諸紀. The text explicitly links observed stellar configuration, time, season, direction and symbolic order. These clauses do not supply a modern numerical rule for producing six lines. The Dipper's apparent orientation depends on observer location, time and epoch; do not map a modern clock time or month to an ancient direction without reconstructing the relevant convention.
- §§4–6, pp.1–2: stellar appearance, color, proximity, presence and motion become traditional omen inputs; 文昌宮、三能、輔星、招搖、天鋒 illustrate symbolic attribution. Apparent color or motion alone does not establish changes in physical stellar properties or human affairs.
- §8, p.2: 攝提 is described in relation to the Dipper handle and establishment of seasonal timing. §110, p.22: winter-solstice signs include day length and natural indicators, but 要決晷景 explicitly gives a decisive role to gnomon shadow. These provide complementary source-text examples of calendrical observation; modern astronomical calculation is a different measurement method.
- §§111, 121–123, pp.22–26: the author's concluding framework distinguishes fixed reference star groups (經), moving five planets (緯), and transient atmospheric phenomena (客氣); regular retrograde motion and eclipses have known patterns. 凡天變，過度乃占 is an explicit contextual distinction between ordinary patterns and departures warranting omen interpretation, not a numerical anomaly threshold. §120 also presents retrospective omen/event associations; the author's claim of correspondence is historical testimony, not independently validated foreknowledge.
- §§101, 104–110, pp.20–22: observation extends beyond celestial bodies to fields, settlement conditions, animals, crops, weather and seasonal signs. This broadens the meaning of observing phenomena, without establishing equivalence to our particular MPH market or solar-wind mappings.

### Working interpretation

Distinguish three observation classes: reference frame (relatively fixed star groups), periodic dynamics (Sun, Moon and five planets), and transient phenomena (clouds, wind, halos and unusual appearances). This is a modern organizational reading of the Chinese text, not a taxonomy asserted to be exhaustive or a new casting rule. Observe the reference, understand regularity, recognize departure, then study historical symbolic interpretation separately. Keep ancient physical/cosmological descriptions distinct from modern astronomy and claims about human affairs.

TC-01 is an initial primary-text reading of the central palace and Northern Dipper, not a complete reconstruction of the five palaces or their historical stars. Next: read §§7–24 and §67 to recover the four directional palaces and lunar-mansion/region correspondences from the same PDF; retain ambiguities rather than silently assign modern stars. No new acquisition, code changes, statistical work or casting. Existing three methods remain unchanged.

## 1. Current research routing

| Need | Open first | Next action / blocker |
|---|---|---|
| **Physical Hexagram — implemented** | [Experimental v0.2 acceptance](physical_model/qualification.md#physical-v02-live-acceptance-smoke--pass) | Basic live acceptance complete; no additional routine qualification work for personal experimental use. |
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
