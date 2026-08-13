param(
  [Parameter(Mandatory = $true)][string]$Archive,
  [Parameter(Mandatory = $true)][string]$Destination,
  [switch]$VerifyOnly
)
$ErrorActionPreference = "Stop"
$Arguments = @("$PSScriptRoot\restore.py", "--archive", $Archive, "--destination", $Destination)
if ($VerifyOnly) { $Arguments += "--verify-only" }
python @Arguments
exit $LASTEXITCODE

