# Research tools

Experimental tools for Issue #6. These scripts are separate from the production casting path. No formal source qualification or model freeze is implied.

Keep raw observations, ZIP archives and local results under `temp/PH_BT_v01/`, not in this directory or Git. NMDB provider restrictions apply; do not redistribute raw data without permission. Preserve the original capture and keep BT-C (2026-09-21 UTC) sealed.

## Current workflow (Windows PowerShell)

From the repository root:

```powershell
git pull --ff-only
Set-Location .\temp\PH_BT_v01
py ..\..\research\swips_revision_probe_v01.py --selftest
```

After reviewing source-use terms, and only if the output does not already exist:

```powershell
py ..\..\research\swips_revision_probe_v01.py .\PH_BT_september_capture_v01.zip --acknowledge-research-use
$LASTEXITCODE
```

The probe requests metadata only; preserve its output even on partial failure. No automatic retry or observation download. See [Issue #6](https://github.com/cctsao1008/trng-iching/issues/6) for the fixed research protocol and evidence.

## Offline replay

Run from the same local data directory. NumPy and SciPy are required for the offline numerical tools. All inputs must be the original pinned ZIPs.

```powershell
py ..\..\research\physical_september_audit_v01.py .\PH_BT_september_capture_v01.zip
py ..\..\research\physical_september_joint_v01.py .\PH_BT_september_capture_v01.zip .\PH_BT_september_supplement_v01.zip .\PH_BT_september_D26_v01.zip
py ..\..\research\physical_reference_sensitivity_v01.py .\PH_BT_september_capture_v01.zip .\PH_BT_september_supplement_v01.zip .\PH_BT_september_D26_v01.zip
```

The supplement tool remains available for its original bounded protocol; do not recapture existing results. The original historical capture and archive transport helpers remain in the archived PH_BT_v01 package; do not reconstruct or replace those frozen tools.
