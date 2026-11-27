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
