$ErrorActionPreference = "Stop"

$TrackedPrivateEnv = git ls-files ".env" ".env.*" | Where-Object { $_ -ne ".env.example" }
if ($TrackedPrivateEnv) {
  Write-Error "Private environment file is tracked: $TrackedPrivateEnv"
  exit 1
}

$Pattern = "BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{20,}"
$Findings = git grep -n -I -E $Pattern -- . ":(exclude).env.example"
if ($LASTEXITCODE -eq 0) {
  $Findings
  Write-Error "Potential secret found in tracked content."
  exit 1
}
if ($LASTEXITCODE -gt 1) {
  Write-Error "Secret scan command failed."
  exit $LASTEXITCODE
}

Write-Output "Secret scan passed."
exit 0

