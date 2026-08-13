param([Parameter(Mandatory = $true)][string]$Destination)
$ErrorActionPreference = "Stop"
python "$PSScriptRoot\backup.py" --destination $Destination
exit $LASTEXITCODE

