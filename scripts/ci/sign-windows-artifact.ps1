# Used by src-tauri/tauri.artifact-signing.conf.json during bundling, including
# the app, sidecars, installer helpers, temporary NSIS uninstaller, and installer.
# Set BATCHALIGN_SIGNING_METADATA and BATCHALIGN_SIGNING_DLIB to local files.
# Optional BATCHALIGN_SIGNTOOL overrides signtool.exe discovery.
# Prepend the absolute scripts/ci directory to PATH so the bundler and its
# temporary uninstaller-signing process can find batchalign-sign-windows.cmd.
# Run: just batchalign gui build release --config src-tauri/tauri.artifact-signing.conf.json
# Release verification must inspect extracted/installed payload signatures too;
# a valid outer installer signature alone does not establish payload trust.
param([Parameter(Mandatory=$true,Position=0)][string]$Path)
$ErrorActionPreference='Stop'
$file=(Get-Item -LiteralPath $Path).FullName
$existing=Get-AuthenticodeSignature -LiteralPath $file
if($existing.Status -eq 'Valid'){
    Write-Output "Already signed: $file"
    exit 0
}
if($existing.Status -ne 'NotSigned'){
    throw "Refusing to replace an invalid or unsupported signature: $file ($($existing.Status))"
}
# NSIS supplies its generated uninstaller as a .tmp PE file. Do not filter by
# extension: SignTool identifies the format, and we verify its result below.
foreach($variable in @('BATCHALIGN_SIGNING_METADATA','BATCHALIGN_SIGNING_DLIB')){
    $value=[Environment]::GetEnvironmentVariable($variable)
    if(!$value -or !(Test-Path -LiteralPath $value -PathType Leaf)){
        throw "Set $variable to the required local Artifact Signing file"
    }
}
$tool=$env:BATCHALIGN_SIGNTOOL
if(!$tool){
    $command=Get-Command signtool.exe -ErrorAction SilentlyContinue
    if($command){$tool=$command.Source}
}
if(!$tool){
    $sdk=Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\10\bin'
    $candidate=Get-ChildItem -LiteralPath $sdk -Directory -ErrorAction SilentlyContinue |
        Where-Object {$_.Name -match '^\d+\.\d+\.\d+\.\d+$'} |
        Sort-Object {[version]$_.Name} -Descending |
        ForEach-Object {Join-Path $_.FullName 'x64\signtool.exe'} |
        Where-Object {Test-Path -LiteralPath $_ -PathType Leaf} |
        Select-Object -First 1
    $tool=$candidate
}
if(!$tool){throw 'Install the Windows SDK or set BATCHALIGN_SIGNTOOL'}
# AzureCliCredential must be able to discover az from the signing client.
if(!(Get-Command az -ErrorAction SilentlyContinue)){
    $azureBin=Join-Path $env:ProgramFiles 'Microsoft SDKs\Azure\CLI2\wbin'
    if(Test-Path -LiteralPath (Join-Path $azureBin 'az.cmd')){
        $env:PATH=$azureBin+';'+$env:PATH
    }
}
& $tool sign /fd SHA256 /tr http://timestamp.acs.microsoft.com /td SHA256 /d Batchalign /dlib $env:BATCHALIGN_SIGNING_DLIB /dmdf $env:BATCHALIGN_SIGNING_METADATA $file
if($LASTEXITCODE -ne 0){throw "Artifact Signing failed: $file"}
& $tool verify /pa /all $file
if($LASTEXITCODE -ne 0){throw "Signature verification failed: $file"}
$signed=Get-AuthenticodeSignature -LiteralPath $file
if($signed.Status -ne 'Valid' -or !$signed.TimeStamperCertificate){
    throw "Missing valid timestamped signature: $file"
}
