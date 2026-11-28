# Research index

Single entry point for [Issue #6](https://github.com/cctsao1008/trng-iching/issues/6). Read this before opening individual scripts or searching the entire issue history. Inventory: 36 retained tools/documents across 7 logical groups, excluding this index and [archive/](archive/README.md). Snapshot: 2026-11-28; baseline commit `6b512f591505cadd4e262d0b61a88b94f60b0e48`.

## 1. Current research routing

| Need | Open first | Next action / blocker |
|---|---|---|
| Current PH-BT gates | [qualification baseline](physical_qualification_v01.md) and the domain updates below | 0/6 qualified; no freeze. Baseline is historical, not a substitute for newer evidence. |
| COSM B02–B05 | [planetary replay](cosm_planetary_replay_v01.py), [#7238939530](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7238939530) | Owner B01 execution succeeded; existing JSON not yet received for independent replay. Upload it; no rerun. |
| COSM B06/B08/B09 | [sixth-channel review](cosm_sixth_channel_order_v01.md), [#7239016918](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7239016918) | Lunar and M01 comparisons complete at diagnostic level; no calibrated planetary uncertainty, sixth channel or line order selected. |
| M01 | [elastic diagnostic](physical_m01_elastic_v01.py), [#7239165876](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7239165876) | Keep rigid direct forcing distinct from gravity response. External ephemeris, independent frame/EOP and calibrated joint uncertainty remain open. |
| D12 | [support review](physical_d12_support_v02.py), [#7223004237](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7223004237) | Station calibration, reference/model uncertainty and estimand selection. |
| D06 | [native audit](physical_d06_native_audit_v01.py), [#7223335599](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7223335599) | Provider R0 calibration, decomposition residual, seasonal background and as-of. |
| D26 | [counting diagnostic](physical_d26_counting_v01.py), [#7224018446](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7224018446) | Exposure/calibration/rights; completed correction replay in archive. Do not repeat speculative capture. |
| D03/D02 | [provider questions](physical_solar_provider_questions_v01.md), [#7234645446](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7234645446) | Flag definitions, calibration/covariance, sweep/NGP support, publication and rights. Requests unsent. |
| Cross-domain comparison | [model compare](physical_model_compare_v01.py), [timescale](physical_timescale_v01.py) | Inspected dates only; do not optimize or select by hexagram yield. |

## 2. File catalog

Role labels: **DOC** = research reference; **REPLAY** = completed diagnostic retained for reproducibility; **SHARED** = imported dependency or historical capture helper (not a request to reacquire); **OWNER-DONE** = owner execution reported; **BLOCKED-INPUT** = independent replay cannot proceed without existing artifact. A completed diagnostic is not a qualified physical model.

### COSM — classical and astronomical candidates

| File | Role | Use / evidence boundary | Issue evidence |
|---|---|---|---|
| [cosm_candidate_architecture_v01.md](cosm_candidate_architecture_v01.md) | DOC | Classical sources, functional/planetary/physical alternatives, encoder semantics | [#7238826420](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7238826420) |
| [cosm_planetary_motion_v01.py](cosm_planetary_motion_v01.py) | OWNER-DONE | Pinned DE440s apparent/geometric planetary vectors and interval diagnostics; do not rerun B01 merely to obtain an existing result | [#7238893578](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7238893578) |
| [cosm_planetary_replay_v01.py](cosm_planetary_replay_v01.py) | BLOCKED-INPUT | Independent arithmetic replay of pinned B01 JSON; first action when supplied | [#7238939530](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7238939530) |
| [cosm_sixth_channel_order_v01.md](cosm_sixth_channel_order_v01.md) | DOC | Sixth-channel options, exhaustive position sensitivity and angular uncertainty | [#7238971766](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7238971766) |
| [cosm_lunar_geometry_v01.py](cosm_lunar_geometry_v01.py) | REPLAY | Geometric illuminated fraction versus M01; uses owner M01 vector JSON | [#7239016918](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7239016918) |

### M01 — astronomical tidal forcing

| File | Role | Use / evidence boundary | Issue evidence |
|---|---|---|---|
| [physical_m01_math_v01.py](physical_m01_math_v01.py) | SHARED | Independent scalar/Decimal formula and synthetic geometry; imported by vector audit | [#7222649080](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222649080) |
| [physical_m01_vectors_v01.py](physical_m01_vectors_v01.py) | SHARED | Original pinned vector export and checks; imported by margin study | [#7236148998](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7236148998) |
| [physical_m01_vector_replay_v01.py](physical_m01_vector_replay_v01.py) | REPLAY | Independent exported-vector arithmetic and perturbation review | [#7236148998](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7236148998) |
| [physical_m01_margin_v01.py](physical_m01_margin_v01.py) | REPLAY | Fixed/varying component gain sensitivity | [#7222856369](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222856369) |
| [physical_m01_moshier_v01.py](physical_m01_moshier_v01.py) | REPLAY | Optional Moshier cross-model check; separate licensing review before integration | [#7239092340](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7239092340) |
| [physical_m01_projection_v01.py](physical_m01_projection_v01.py) | REPLAY | Radial/ellipsoidal normal and conditional GM gains | [#7239134571](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7239134571) |
| [physical_m01_elastic_v01.py](physical_m01_elastic_v01.py) | REPLAY | Legendre expansion and simplified solid Earth response; distinct estimand | [#7239165876](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7239165876) |

### D12 — water level and tide reference

| File | Role | Use / evidence boundary | Issue evidence |
|---|---|---|---|
| [physical_tide_background_v01.py](physical_tide_background_v01.py) | SHARED | Original tide prediction capture and decode; used by residual/support tools | [#7222341927](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222341927) |
| [physical_tide_residual_v01.py](physical_tide_residual_v01.py) | SHARED | Datum versus tide residual and coupled-domain comparison; exports tide pin | [#7222341927](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222341927) |
| [physical_d12_uncertainty_v01.py](physical_d12_uncertainty_v01.py) | REPLAY | Centered support, observation/reference stress intervals | [#7222916993](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222916993) |
| [physical_d12_support_v02.py](physical_d12_support_v02.py) | REPLAY | Station provenance, prediction temporal support and sensitivity | [#7223004237](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7223004237) |

### D06 — geomagnetic field

| File | Role | Use / evidence boundary | Issue evidence |
|---|---|---|---|
| [physical_d06_operator_v01.py](physical_d06_operator_v01.py) | SHARED | Scalar F observation-operator sensitivity; imported by native tool | [#7223099565](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7223099565) |
| [physical_d06_native_v01.py](physical_d06_native_v01.py) | SHARED | Original native minute/decomposition capture, decoder and URL contract | [#7223185978](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7223185978) |
| [physical_d06_native_audit_v01.py](physical_d06_native_audit_v01.py) | REPLAY | Native minute replay, filter compatibility and decomposition closure | [#7223335599](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7223335599) |

### D26 — neutron-monitor corrected count rate

| File | Role | Use / evidence boundary | Issue evidence |
|---|---|---|---|
| [physical_d26_counting_v01.py](physical_d26_counting_v01.py) | SHARED | Conditional counting/pressure sensitivity; archived correction chain imports it | [#7223407815](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7223407815) |

### D03/D02 — solar wind MAG and SWiPS

| File | Role | Use / evidence boundary | Issue evidence |
|---|---|---|---|
| [swips_revision_probe_v01.py](swips_revision_probe_v01.py) | SHARED | Original metadata probe and shared URL/listing/clock helpers | [#7222127629](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222127629) |
| [swips_l2_l3_bridge_v01.py](swips_l2_l3_bridge_v01.py) | SHARED | Packet correspondence, temporal label audit, shared moment parser | [#7222127629](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222127629) |
| [swips_l2_audit_v01.py](swips_l2_audit_v01.py) | REPLAY | September L2 flags, collisions and eligible support | [#7222584812](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222584812) |
| [physical_solar_coupling_v01.py](physical_solar_coupling_v01.py) | REPLAY | Proton thermal/magnetic pressure, beta and conditional sensitivity | [#7234128136](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7234128136) |
| [physical_solar_support_v01.py](physical_solar_support_v01.py) | REPLAY | Sweep overlap, magnetic magnitude and flag strata | [#7234606790](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7234606790) |
| [physical_solar_provider_questions_v01.md](physical_solar_provider_questions_v01.md) | DOC | Version-specific provider questions; unsent; no approval implied | [#7234645446](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7234645446) |

### PH-BT — common evidence and candidate model

| File | Role | Use / evidence boundary | Issue evidence |
|---|---|---|---|
| [physical_qualification_v01.md](physical_qualification_v01.md) | DOC | G1–G8/Q qualification review and historical data SHA256 registry; baseline, not live status | [#7222584812](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222584812) |
| [physical_september_audit_v01.py](physical_september_audit_v01.py) | SHARED | Original September parsing and validation primitives | [#7222584812](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222584812) |
| [physical_september_joint_v01.py](physical_september_joint_v01.py) | SHARED | Pinned ZIP validation, shared grids and joint diagnostic | [#7222584812](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222584812) |
| [physical_september_supplement_v01.py](physical_september_supplement_v01.py) | SHARED | Original bounded capture and shared transport; do not recapture | [#7222584812](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222584812) |
| [physical_reference_sensitivity_v01.py](physical_reference_sensitivity_v01.py) | SHARED | Reference/aggregation analysis and shared series/block functions | [#7222584812](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222584812) |
| [physical_time_support_v01.py](physical_time_support_v01.py) | SHARED | Support alignment and minute-grid loading | [#7222584812](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222584812) |
| [physical_background_v01.py](physical_background_v01.py) | SHARED | Fixed versus trailing background; shared reference functions | [#7222584812](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222584812) |
| [physical_uncertainty_v01.py](physical_uncertainty_v01.py) | REPLAY | Hypothetical uncertainty propagation across domains | [#7222184629](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222184629) |
| [physical_model_compare_v01.py](physical_model_compare_v01.py) | REPLAY | Compare candidate background/reference semantics without selection | [#7222396402](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222396402) |
| [physical_timescale_v01.py](physical_timescale_v01.py) | REPLAY | Characteristic timescale diagnostics, not a frozen window | [#7222490785](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7222490785) |

## 3. Local artifact routing

All observational captures and generated results remain under `temp/PH_BT_v01/` locally, not in Git. Do not substitute datasets or regenerate a pinned file silently. See [qualification baseline](physical_qualification_v01.md#rechecked-artifact-digests-sha256) for the five original September ZIPs and early result digests. The following later pins are recorded from Issue #6; availability and actual bytes must be verified in the execution environment.

| Artifact | SHA256 | Evidence / use |
|---|---|---|
| `physical_m01_vectors_result_v01.json` | `640425e5be4af42c797b21c2dc1d8ca943cf40108bb817c7022864695fab7ad9` | [#7236148998](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7236148998); M01 and lunar replay |
| `cosm_planetary_motion_result_v01.json` | `698adce3ed4532ecb13b712565c2cc15dff4f4484df5b74f89d183383d19921c` | [#7238939530](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7238939530); owner reported digest, bytes pending |
| `PH_BT_d06_native_v01.zip` | `6b07bdab4bb45a75cdfbea79a7c9538a7fa05f7bd63d823e34fb906ca05864c7` | [#7223335599](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7223335599); native audit |
| `PH_BT_d26_correction_v02.zip` | `e0f89b7b8f6963540017dfcaa53622b2f177dbf5bd401a2dc342c262874ea1f3` | [#7224018446](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7224018446); historical correction audit |
| `cosm_lunar_geometry_result_v01.json` | `9261f9af7c79dc64e0f55d86ca8479a1c8d7ad8b725673bfd6f2922b72df73eb` | [#7239016918](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7239016918) |
| `physical_m01_moshier_result_v01.json` | `46bbd83845f701cf9973852b0495b6d743ac409123713d15d58e9b20b3e0e139` | [#7239092340](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7239092340) |
| `physical_m01_projection_result_v01.json` | `193ed28c5f2672b8d9331bc31b9a157ab6face117d3f788252e62291de093f63` | [#7239134571](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7239134571) |
| `physical_m01_elastic_result_v01.json` | `0872be398d6e723ae71a01391a37ef04235fe42a6ee56a11d66fbcac05977ce1` | [#7239165876](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7239165876) |

## 4. Dependency routing

Keep the root flat: existing bare-name imports and root-relative paths depend on it. Logical groups above are not Python packages. The main shared chains are:

- September audit -> joint -> reference sensitivity -> time support -> background / uncertainty / model compare / timescale (arrow indicates downstream use, not exclusive dependencies).
- Supplement transport -> SWiPS metadata probe -> SWiPS bridge -> time support; L2 audit also uses the probe.
- D06 operator -> native capture -> native audit.
- Tide background -> tide residual -> D12 support / uncertainty.
- M01 math -> vectors -> margin; joint also supports vector replay. Lunar, Moshier, projection and elastic tools consume the pinned owner vector JSON separately.
- D26 counting -> archived correction v0.1 -> v0.2 -> archived correction audit. Preserve exact archived blobs and use the documented archive replay path.

## 5. Offline replay (Windows PowerShell)

From the repository root, synchronize and work in the original data directory:

```powershell
git pull --ff-only
Set-Location .\temp\PH_BT_v01
py ..\..\research\physical_september_audit_v01.py .\PH_BT_september_capture_v01.zip
py ..\..\research\physical_september_joint_v01.py .\PH_BT_september_capture_v01.zip .\PH_BT_september_supplement_v01.zip .\PH_BT_september_D26_v01.zip
py ..\..\research\physical_reference_sensitivity_v01.py .\PH_BT_september_capture_v01.zip .\PH_BT_september_supplement_v01.zip .\PH_BT_september_D26_v01.zip
```

Examples, not a recurring instruction to rerun completed tests. Read the selected script's exact CLI and input pins before running. NumPy/SciPy are required for relevant offline tools; some astronomy diagnostics have additional dependencies. Original capture/transport tools from the archived PH_BT_v01 package must not be reconstructed or replaced.

## 6. Maintenance and evidence boundaries

- Update this index whenever a script is added, superseded, archived or a blocker changes. Record the purpose, input identity, output identity, role and latest Issue #6 evidence in the same change where practical.
- Keep evidence versions immutable. Use a newer version for changed algorithms; distinguish historical and current results. Archive only when the active dependency chain permits, preserving original blobs and historical replay.
- No raw NMDB redistribution. Confirm intended-use rights. Preserve all original captures and BT-C (2026-09-21 UTC) sealed. BT-A/B are already inspected. No production changes, automatic recapture, cast, QRNG fallback or model freeze implied by this index.
- Separate the PH-BT six-domain physical candidate, COSM planetary/functional candidates and existing MPH. Do not treat numerical replay or cultural affinity as physical qualification.

觀象，察變，求真，思己。
