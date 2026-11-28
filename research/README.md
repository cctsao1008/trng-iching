# Research tools

Experimental tools for [Issue #6](https://github.com/cctsao1008/trng-iching/issues/6). Separate from the production casting path. No formal source qualification or model freeze is implied.

## Organization

- This directory: ongoing diagnostics, shared dependencies and reproducible evidence tools.
- [archive/](archive/README.md): superseded or completed one-shot tools and their historical replay chain. Do not use these for new acquisition.
- Keep raw observations, ZIP archives and local results under `temp/PH_BT_v01/`, not in this directory or Git. NMDB provider restrictions apply; do not redistribute raw data without permission. Preserve original captures; BT-C (2026-09-21 UTC) remains sealed.

## Current priorities

- COSM: `cosm_planetary_motion_v01.py` has already produced the owner B01 JSON. Use `cosm_planetary_replay_v01.py` on the pinned result when provided; do not rerun the capture unnecessarily.
- M01: retain the math, vector, projection, alternative ephemeris and elastic-response diagnostics; independent frame/EOP, external ephemeris and calibrated uncertainty remain open.
- PH-BT: use existing pinned records for offline analysis. Provider quality, calibration, availability and rights blockers remain open. Qualification remains 0/6.

## Offline replay (Windows PowerShell)

From the repository root:

```powershell
git pull --ff-only
Set-Location .\temp\PH_BT_v01
py ..\..\research\physical_september_audit_v01.py .\PH_BT_september_capture_v01.zip
py ..\..\research\physical_september_joint_v01.py .\PH_BT_september_capture_v01.zip .\PH_BT_september_supplement_v01.zip .\PH_BT_september_D26_v01.zip
py ..\..\research\physical_reference_sensitivity_v01.py .\PH_BT_september_capture_v01.zip .\PH_BT_september_supplement_v01.zip .\PH_BT_september_D26_v01.zip
```

NumPy and SciPy are required for relevant offline tools. Use original pinned inputs. `swips_revision_probe_v01.py`, `physical_september_supplement_v01.py`, `physical_d06_native_v01.py`, `physical_tide_background_v01.py` and `swips_l2_l3_bridge_v01.py` remain here because current replay tools import their shared functions. Their historical acquisition entry points are not a request to recapture data. The original historical capture and archive transport helpers remain in the archived PH_BT_v01 package; do not reconstruct or replace those frozen tools.

See Issue #6 for the fixed research protocol, versioned evidence and execution details.
