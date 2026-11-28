# Archived research tools

Archived from main at commit `8979f4fcc5b13fcd0564ee1bdd09543efbe9bd1a`. Original script blobs and bytes are preserved. Do not repeat acquisition. See [migration.json](../migration.json) for the active path migration.

| File | Reason |
|---|---|
| physical_d26_correction_v01.py | Superseded failed capture; retained for regression provenance. |
| physical_d26_correction_v02.py | Completed one-shot correction capture. |
| physical_d26_correction_audit_v01.py | Completed offline audit; kept with original direct dependencies. |
| swips_l2_capture_v01.py | Completed one-shot L2 capture. |

These historical scripts still use the original bare module names. For exact offline replay, use the pinned pre-migration commit `ff3cd1c1c9a8bc8cda0ad4ad353b24b8246b5f69` in a separate detached worktree; do not modify archived imports or switch the current main checkout. From the repository root, with the original local data directory present:

```powershell
$repoRoot = (Get-Location).Path
$legacy = Join-Path $env:TEMP "trng-iching-research-legacy"
git worktree add --detach $legacy ff3cd1c1c9a8bc8cda0ad4ad353b24b8246b5f69
if ($LASTEXITCODE -ne 0) { throw "Legacy worktree setup failed" }
$oldPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = (Join-Path $legacy "research") + [IO.Path]::PathSeparator + $oldPythonPath
    Set-Location (Join-Path $repoRoot "temp\PH_BT_v01")
    py (Join-Path $legacy "research\archive\physical_d26_correction_audit_v01.py") .\PH_BT_september_D26_v01.zip .\PH_BT_d26_correction_v02.zip
} finally {
    Set-Location $repoRoot
    $env:PYTHONPATH = $oldPythonPath
}
```

No raw data moved into Git. Keep original captures locally; no NMDB raw redistribution. Historical Issue #6 commands refer to their original commit paths. The worktree command is documented, not executed in this refactor.
