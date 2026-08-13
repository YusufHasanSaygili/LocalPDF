param(
  [string]$Configuration = "Release",
  [string]$Runtime = "win-x64"
)

$ErrorActionPreference = "Stop"
$LauncherDirectory = $PSScriptRoot
$RepositoryRoot = (Resolve-Path (Join-Path $LauncherDirectory "..\..")).Path
$BundlePath = Join-Path $LauncherDirectory "bundle.zip"
$PublishDirectory = Join-Path $LauncherDirectory "bin\publish"
$DistributionDirectory = Join-Path $RepositoryRoot "dist"
$ExecutablePath = Join-Path $PublishDirectory "LocalPDF.exe"
$DistributionExecutable = Join-Path $DistributionDirectory "LocalPDF.exe"

Push-Location $RepositoryRoot
try {
  $RepositoryChanges = git status --porcelain
  if ($RepositoryChanges) {
    throw "Commit tracked changes before building so the embedded bundle matches Git HEAD."
  }

  if (Test-Path -LiteralPath $BundlePath) {
    Remove-Item -LiteralPath $BundlePath -Force
  }

  git archive --format=zip --output=$BundlePath HEAD `
    .env.example docker-compose.yml package.json README.md apps/web services/api scripts
  if ($LASTEXITCODE -ne 0) {
    throw "Could not create the embedded application bundle."
  }

  $env:DOTNET_CLI_TELEMETRY_OPTOUT = "1"
  dotnet publish "$LauncherDirectory\LocalPDF.Launcher.csproj" `
    --configuration $Configuration `
    --runtime $Runtime `
    --self-contained true `
    --output $PublishDirectory `
    -p:PublishSingleFile=true `
    -p:IncludeNativeLibrariesForSelfExtract=true `
    -p:DebugType=None `
    -p:DebugSymbols=false
  if ($LASTEXITCODE -ne 0) {
    throw "LocalPDF launcher publish failed."
  }

  New-Item -ItemType Directory -Force -Path $DistributionDirectory | Out-Null
  Copy-Item -LiteralPath $ExecutablePath -Destination $DistributionExecutable -Force
  $Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $DistributionExecutable).Hash.ToLowerInvariant()
  Set-Content -LiteralPath "$DistributionExecutable.sha256" -Value "$Hash  LocalPDF.exe" -Encoding ascii
  Write-Output "Built: $DistributionExecutable"
  Write-Output "SHA-256: $Hash"
}
finally {
  Pop-Location
}
