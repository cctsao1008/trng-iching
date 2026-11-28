# COSM-B08/B09 — Sixth-channel and line-order semantics v0.1

Status: CANDIDATE REVIEW / SYNTHETIC ENUMERATION ONLY / NOT FROZEN. Follow-up to #7238939530. Owner reported B01 JSON SHA256 698adce3ed4532ecb13b712565c2cc15dff4f4484df5b74f89d183383d19921c, but the JSON bytes are still absent in this turn. B02–B05 actual vector replay and data analysis remain pending. No substitute observations or fabricated results.

## B08: sixth channel

Textual anchors: [Huainanzi Tianwen Xun](https://zh.wikisource.org/zh-hant/淮南子/天文訓) explicitly maps Five Planets to Five Phases, also discusses Sun and Moon; [Zhouyi Zhengyi, Shuogua](https://zh.wikisource.org/zh-hant/周易正義/09.02) explains doubled Three Powers. Neither establishes a unique sixth planet/channel or Five-Phase-to-six-position rule.

| Candidate | Estimand / rationale | Limitation |
|---|---|---|
| QRNG | Existing modern MPH stochastic channel | Not classical astronomy, no intrinsic reason for top position, not a measured macro-state |
| Sun–Moon relative geometry | Defined geocentric angular separation or oriented longitude difference, distinct estimands; lunar phase context | Circular coordinate, explicit frame/orientation/reference needed; rate can remain one-sided; do not force polarity changes |
| M01 | Geometric rigid radial Sun+Moon differential acceleration at fixed WGS84 site | Different physical dimension from planetary angular motion, local site and Earth orientation; not measured solid-earth tide |
| Five-planet aggregate | Derived multivariate system state | Reuses same five inputs, weighting/reference must be justified; cannot claim sixth independent observation |

Prefer examining M01 and Sun–Moon geometry for a purely astronomical candidate, retain existing QRNG for legacy MPH. No sixth source selected. Sun and Moon together are not automatically a single measured channel; any scalar compression needs physical semantics. No independence requirement asserted without evidence. Do not turn availability, variation rate or symbolic balance into a reason to add random fallback.

Read actual main.py blob be9f4b859dca050f8d5c74165f2b29dff7928157, lines 463–472, and iching.py blob 7440256aaac7a1c760f66c900d4ad0cdd3bec06a, lines 89–101, 125–143: legacy QRNG sixth three-bit group maps 6+popcount. All eight possible groups enumerated, multiplicities 6:1,7:3,8:3,9:1. Conditional on equally likely independent fair bits, primary yang and relating yang each 1/2, moving 1/4. Not an empirical verification of provider entropy or independence from physical channels. With five fixed physical codes and fixed QRNG top placement, at most four distinct primary/relating pairs are possible from that group, not 4096.

## B09: line order

Actual deterministic exhaustive JavaScript enumeration: 4096 synthetic bottom-to-top arrays in {6,7,8,9}^6; 720 permutations of six labeled channels plus 120 permutations with channel six fixed at top. Primary bit 1 iff code in {7,9}; relating bit 1 iff code in {6,7}. Ordered pair of six-bit words bijective to four-valued line array. No actual cast or divination interpretation.

For n permuted channels with multiplicities m6,m7,m8,m9, distinct ordered primary/relating pairs = n! / product(m_i!). Distinct primary words = n! / ((m6+m8)! (m7+m9)!). Fixed positions are unchanged. Verified both formulae for every array and both permutation regimes, zero failures. Moving-line count invariant for every permutation; moving-line positions need not be invariant.

| Synthetic scope | Min/max distinct pairs | Sum over 4096 arrays | Arrays with one pair | Min/max distinct primary words | Primary sum |
|---|---|---:|---:|---|---:|
| All six permuted | 1/180 | 387136 | 4 | 1/20 | 59136 |
| Sixth fixed | 1/60 | 126016 | 16 | 1/10 | 32256 |

Compare two explicit planetary order conventions with the same abstract sixth channel X, bottom-to-top:
- A: Venus, Jupiter, Mercury, Mars, Saturn, X (reuse existing phase order Metal/Wood/Water/Fire/Earth; compatibility of positions only, not old observations).
- B: Mercury, Venus, Mars, Jupiter, Saturn, X (ascending nominal heliocentric orbital scale among five planets, not instantaneous geocentric distance or classical line rule).
- permutation B from A: zero-based [2,0,3,1,4,5].

Across all 4096 equally enumerated synthetic arrays: primary changes 3584, relating changes 3584, ordered pair changes 4032, moving-position mask changes 3584. No change in moving count. These proportions describe exhaustive abstract inputs, not empirical frequencies or a selection criterion.

Minimal reproduction: enumerate six-tuples over range(6,10), permutations of range(6); apply permutation to tuple; encode pair as primary_integer*64+relating_integer, with bottom-to-top bits at positions 0..5. Filter p[5]==5 for fixed top. Compare set cardinalities with factorial formula and compare A with permutation [2,0,3,1,4,5]. No random sampling.

Other order candidates: traditional enumeration, seasonal scheme with earth at center, Three Powers grouping. Each needs independent semantic justification; center is not a unique position in a linear even-length array. No order selected. A default based solely on enum/source iteration order is not a scientific decision. Any future configuration must pin domain identity, order, encoding, reference/support and version before independent evaluation; do not optimize by resulting hexagrams, moving frequencies or favorable readings.

## B06 partial: uncertainty contract

[JPL DE440/DE441 paper and abstract](https://ssd.jpl.nasa.gov/doc/de440_de441.html) describes numerically integrated orbits fitted to observations, including spacecraft ranging and VLBA; a pinned kernel and independent arithmetic do not imply exact positions. No per-epoch calibrated angular bound inferred from published fit residuals or the current synthetic 0.001/0.1/1 arcsec scenarios.

For a projected position vector p in a fixed ecliptic plane and additive projected vector error with norm <= E, if E < |p|, the largest possible angular deviation is asin(E/|p|) (tangent to the uncertainty disk). If E >= |p|, longitude may be undefined and this bound is not usable. This only covers a bounded geometric vector error in a fixed frame. Apparent longitude adds light-time/aberration/deflection and frame conventions; no transfer of the geometric bound without a justified model. For distinct endpoint bounds e0,e1,e2 on a unique angular branch, absolute increment error <= e1+e2, second difference <= e0+2e1+e2. Rate and second-difference bounds divide by h and h^2 respectively. Shared errors can cancel; do not assume independence or calibrated confidence from worst-case scenarios. Frame, ephemeris, target semantics, time scale, numerical uncertainty and model discrepancy must be distinguished. Actual B06 calibration and independent external comparison remain open.

## State and next action

B08 and B09 bounded conceptual/combinatorial reviews completed; sixth domain and position choice remain unresolved. B06 mathematical contract extended, actual uncertainty evidence outstanding. B02–B05 require existing owner JSON, no rerun needed. B10 independent validation and integration not authorized by this note. PH-BT qualification 0/6, BT-C sealed, no production change, no new observation acquisition, no cast, no freeze.

觀象，察變，求真，思己。
