# PH-BT solar-wind provider evidence requests v0.1

Status: OPEN / UNSENT / EXPLORATORY ONLY. This is an evidence request, not a revised QC policy, production change, or model freeze. BT-C remains sealed. The only data considered are previously inspected UTC 2026-09-07 and 2026-09-14. No new observations are requested.

## Exact archived products

The following IDs and date_created attributes were re-read from the pinned original NetCDF files, after re-running the sweep support diagnostic. They identify the files actually used, not a current archive version or first real-time release.

| Product ID (without .nc.gz) | date_created UTC | Delay after nominal next midnight |
|---|---|---|
| oe_mag-l3_solar1_s20260907T000000Z_e20260907T235959Z_p20260908T021448Z_pub | 2026-09-08T02:14:50.781Z | 02:14:50.781 |
| oe_mag-l3_solar1_s20260914T000000Z_e20260914T235959Z_p20260916T022311Z_pub | 2026-09-16T02:23:14.341Z | 26:23:14.341 |
| oe_swips-l2_solar1_s20260907T000000Z_e20260907T235959Z_p20260908T021650Z_pub | 2026-09-08T02:16:50.992Z | 02:16:50.992 |
| oe_swips-l2_solar1_s20260914T000000Z_e20260914T235959Z_p20260916T022512Z_pub | 2026-09-16T02:25:12.449Z | 26:25:12.449 |

The archive daily files are retrospective artifacts. A creation timestamp is neither first publication nor proof that the corresponding real-time packet was unavailable earlier. No historical as-of claim is supported by these timestamps alone.

## MAG — NCEI STP Magnetometer team

Contact: swx.mag@noaa.gov (official dataset metadata: https://www.ncei.noaa.gov/metadata/geoportal/rest/metadata/item/gov.noaa.ncei.swx%3Amag-l3-swfo/html).

Subject: SOLAR-1 operational MAG L3 flag interpretation and minute QC

- All 171,865 second records in the two exact files above have flag bit pattern 0x80000001. The embedded flag_values and flag_masks define bit 0 as sensor_saturated, and do not define bit 31 as a separate flag; the good_quality mask is 4294967295. What are the intended meanings of these bits in these product versions? Is the constant value expected or a known processing/encoding issue?
- What QC propagation and sample eligibility rules apply to b_gse_sphr_min, which has no independent minute flag in these files? Which flags are fatal, suspect, or informational for scalar magnetic magnitude?
- What calibration, low-frequency drift and uncertainty evidence applies to the operational L3 scalar magnitude, and how should time support and correlation of errors be represented?
- What is the relationship between these daily files and operational real-time releases, including original availability timestamps and revisions?

Acceptance evidence: version-specific definitions, explicit minute QC policy, uncertainty scope, and publication/support contract. Numerical agreement with another source is not a substitute for flag semantics.

## SWiPS — NCEI STP Particles team

Contact: swx.particles@noaa.gov (official L2 dataset metadata: https://www.ncei.noaa.gov/access/metadata/landing-page/bin/iso?id=gov.noaa.ncei.swx%3Aswips-l2-swfo).

Subject: SOLAR-1 SWiPS L2 flags, proton moment uncertainty and time support

- The flags variable has no attributes in the two exact operational L2 files above. What is the authoritative bitmask or enum definition, particularly value 8? Which values are eligible for physical proton n, T and velocity analysis? How does backfill affect validity?
- In the retained unique midpoint-bin strata (positive uncorrected moments, no backfill), flag 0/8 temperature medians are 100257/454754 K on Sep 7 and 70335/174648 K on Sep 14. This is an association only; is flag 8 tied to a physical regime, fitting condition, or processing status?
- Under what conditions are uncorrected proton moments valid? What do the missing corrected moments and error fields mean in these versions? Are calibrated density/temperature uncertainty, covariance and temporal dependence available?
- What are the physical support of sweep_start_time, sweep_mid_time and sweep_end_time, effective response weighting, and the precise L2-to-L3 nearest-grid-point timing rule? What are the operational release/revision times versus daily archive creation times?

Acceptance evidence: authoritative flag policy, moment semantics, applicable calibrated uncertainty and time/as-of contract. Do not infer flag meaning from temperature association or choose P1 by coverage.

## Immediate technical follow-up

- M01 real 480-epoch vector replay remains outstanding. The existing physical_m01_vectors_v01.py is the next locally executable independent consistency check; it does not require new observation dates.
- D03/D02 remain blocked at scientific QC. Do not strip high bits, accept flag 8 by inference, or replace operational data with retrospective science data silently.
- No messages sent. No raw data attached or redistributed. No changes to production, no new issue or model freeze. Formal qualification remains 0/6.

Evidence: [qualification review v0.1](physical_qualification_v01.md), [sweep support script](physical_solar_support_v01.py), [Issue #6 sweep support results](https://github.com/cctsao1008/trng-iching/issues/6#issuecomment-7234606790).
