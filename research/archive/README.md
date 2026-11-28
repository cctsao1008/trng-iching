# Archived research tools

Archived from main at commit `8979f4fcc5b13fcd0564ee1bdd09543efbe9bd1a`. Original Git blobs and file bytes are preserved; this is not a new model version.

| File | Reason |
|---|---|
| physical_d26_correction_v01.py | Superseded failed acquisition (incorrect minute parameter names); retained for v0.2 regression and historical provenance. |
| physical_d26_correction_v02.py | Completed one-shot correction capture; kept together with v0.1 because it imports it. |
| physical_d26_correction_audit_v01.py | Completed offline audit; archived with its direct dependencies to preserve the original code and replay chain. |
| swips_l2_capture_v01.py | Completed one-shot L2 capture; the current offline audit remains in the parent directory. |

Do not repeat acquisition. Archived scripts are evidence, not active entry points. To reproduce the D26 offline audit using the original local ZIPs from `temp/PH_BT_v01`, add the parent research directory to PYTHONPATH temporarily (archive script directory is already on Python's import path):

```powershell
$oldPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = (Resolve-Path ..\..\research).Path + [IO.Path]::PathSeparator + $oldPythonPath
    py ..\..\research\archive\physical_d26_correction_audit_v01.py .\PH_BT_september_D26_v01.zip .\PH_BT_d26_correction_v02.zip
} finally {
    $env:PYTHONPATH = $oldPythonPath
}
```

No raw data moved into Git. Historical commands in Issue #6 refer to their original commit paths; use the pinned commit for exact-checkout replay. Do not redistribute NMDB raw observations.
