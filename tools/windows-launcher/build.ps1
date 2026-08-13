param(
  [string]$Configuration = "Release",
  [string]$Runtime = "win-x64"
)

$ErrorActionPreference = "Stop"
$LauncherDirectory = $PSScriptRoot
$RepositoryRoot = (Resolve-Path (Join-Path $LauncherDirectory "..\..")).Path
$DesktopRuntimeDirectory = Join-Path $RepositoryRoot "tools\desktop-runtime"
$BuildRoot = Join-Path $DesktopRuntimeDirectory "build"
$BundleStage = Join-Path $BuildRoot "bundle"
$ApiDistribution = Join-Path $BuildRoot "api"
$PyInstallerWork = Join-Path $BuildRoot "pyinstaller"
$BundlePath = Join-Path $LauncherDirectory "bundle.zip"
$PublishDirectory = Join-Path $LauncherDirectory "bin\publish"
$DistributionDirectory = Join-Path $RepositoryRoot "dist"
$DistributionExecutable = Join-Path $DistributionDirectory "LocalPDF.exe"

function Reset-BuildDirectory([string]$Path) {
  $ResolvedBuildRoot = [IO.Path]::GetFullPath($BuildRoot).TrimEnd('\') + '\'
  $ResolvedTarget = [IO.Path]::GetFullPath($Path)
  if (-not $ResolvedTarget.StartsWith($ResolvedBuildRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to reset a directory outside the desktop build root: $ResolvedTarget"
  }
  if (Test-Path -LiteralPath $ResolvedTarget) {
    Remove-Item -LiteralPath $ResolvedTarget -Recurse -Force
  }
  New-Item -ItemType Directory -Force -Path $ResolvedTarget | Out-Null
}

Push-Location $RepositoryRoot
try {
  $RepositoryChanges = git status --porcelain
  if ($RepositoryChanges) {
    throw "Commit tracked changes before building so the embedded runtime matches Git HEAD."
  }

  Reset-BuildDirectory $BundleStage
  Reset-BuildDirectory $ApiDistribution
  Reset-BuildDirectory $PyInstallerWork

  Write-Output "Building embedded Python API runtime..."
  uv sync --project services\api --python 3.12 --all-extras
  if ($LASTEXITCODE -ne 0) { throw "Python dependency sync failed." }
  uv pip install --python services\api\.venv\Scripts\python.exe pyinstaller==6.15.0
  if ($LASTEXITCODE -ne 0) { throw "PyInstaller setup failed." }
  uv run --project services\api pyinstaller `
    --noconfirm --clean --onedir --name LocalPDF.Api `
    --distpath $ApiDistribution --workpath $PyInstallerWork `
    --specpath $BuildRoot --paths services\api `
    --collect-all pikepdf --collect-all pymupdf `
    tools\desktop-runtime\api_entry.py
  if ($LASTEXITCODE -ne 0) { throw "Desktop API packaging failed." }

  Write-Output "Building embedded web interface..."
  Push-Location (Join-Path $RepositoryRoot "apps\web")
  try {
    npm ci
    if ($LASTEXITCODE -ne 0) { throw "Web dependency installation failed." }
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "Web production build failed." }
  }
  finally {
    Pop-Location
  }

  $ApiStage = Join-Path $BundleStage "api"
  $WebStage = Join-Path $BundleStage "web"
  $RuntimeStage = Join-Path $BundleStage "runtime"
  New-Item -ItemType Directory -Force -Path $ApiStage, $WebStage, $RuntimeStage | Out-Null
  Copy-Item -Path (Join-Path $ApiDistribution "LocalPDF.Api\*") -Destination $ApiStage -Recurse -Force
  Copy-Item -Path (Join-Path $RepositoryRoot "apps\web\.next\standalone\*") -Destination $WebStage -Recurse -Force
  New-Item -ItemType Directory -Force -Path (Join-Path $WebStage ".next\static") | Out-Null
  Copy-Item -Path (Join-Path $RepositoryRoot "apps\web\.next\static\*") `
    -Destination (Join-Path $WebStage ".next\static") -Recurse -Force
  $PublicDirectory = Join-Path $RepositoryRoot "apps\web\public"
  if (Test-Path -LiteralPath $PublicDirectory) {
    Copy-Item -LiteralPath $PublicDirectory -Destination (Join-Path $WebStage "public") -Recurse -Force
  }

  $NodeExecutable = (Get-Command node -ErrorAction Stop).Source
  Copy-Item -LiteralPath $NodeExecutable -Destination (Join-Path $RuntimeStage "node.exe") -Force

  if (Test-Path -LiteralPath $BundlePath) { Remove-Item -LiteralPath $BundlePath -Force }
  Add-Type -AssemblyName System.IO.Compression.FileSystem
  [IO.Compression.ZipFile]::CreateFromDirectory(
    $BundleStage,
    $BundlePath,
    [IO.Compression.CompressionLevel]::Optimal,
    $false
  )

  Write-Output "Building Windows desktop executable..."
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
  if ($LASTEXITCODE -ne 0) { throw "LocalPDF desktop publish failed." }

  New-Item -ItemType Directory -Force -Path $DistributionDirectory | Out-Null
  Copy-Item -LiteralPath (Join-Path $PublishDirectory "LocalPDF.exe") `
    -Destination $DistributionExecutable -Force
  $Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $DistributionExecutable).Hash.ToLowerInvariant()
  Set-Content -LiteralPath "$DistributionExecutable.sha256" `
    -Value "$Hash  LocalPDF.exe" -Encoding ascii
  Write-Output "Built: $DistributionExecutable"
  Write-Output "SHA-256: $Hash"
}
finally {
  Pop-Location
}
