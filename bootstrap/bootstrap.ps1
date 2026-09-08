$ErrorActionPreference = "Stop"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Installing uv..."
    $uvInstaller = (
        Invoke-WebRequest -UseBasicParsing https://astral.sh/uv/install.ps1
    ).Content
    if ([string]::IsNullOrWhiteSpace($uvInstaller)) {
        throw "The uv installer download was empty."
    }
    Invoke-Expression $uvInstaller
    $env:Path = "$env:USERPROFILE\.local\bin;$env:USERPROFILE\.cargo\bin;$env:Path"
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw (
        "uv was installed, but it is not available on PATH. " +
        "Start a new shell and rerun this script."
    )
}

$batchalignRequirement = 'batchalign[all]>=0.10'
$installedTools = uv tool list
if ($LASTEXITCODE -ne 0) {
    throw "Unable to inspect installed uv tools."
}

$batchalignTool = $installedTools | Select-String '^batchalign v\S+'
if ($batchalignTool) {
    Write-Host "Upgrading batchalign[all]..."
    uv tool install --upgrade --python=3.11 --prerelease=allow $batchalignRequirement
} else {
    Write-Host "Installing batchalign[all]..."
    uv tool install --python=3.11 --prerelease=allow $batchalignRequirement
}

if ($LASTEXITCODE -ne 0) {
    throw "Unable to install batchalign[all]."
}

Write-Host "Batchalign is ready."
