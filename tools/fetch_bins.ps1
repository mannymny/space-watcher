param(
    [string]$BinDir = (Join-Path $PSScriptRoot "..\\bin"),
    [switch]$Force
)

$ErrorActionPreference = "Stop"

function Download-File {
    param(
        [Parameter(Mandatory=$true)][string]$Url,
        [Parameter(Mandatory=$true)][string]$Dest
    )
    if ((Test-Path $Dest) -and -not $Force) {
        return
    }
    Write-Host "[download] $Url"
    Invoke-WebRequest -Uri $Url -OutFile $Dest -UseBasicParsing -Headers @{ "User-Agent" = "Mozilla/5.0" }
}

function Ensure-Dir {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

function Get-SevenZip {
    param([string]$TempRoot)
    $seven = Get-Command 7z,7zr -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($seven) { return $seven.Path }
    $seven = Join-Path $TempRoot "7zr.exe"
    Download-File "https://www.7-zip.org/a/7zr.exe" $seven
    return $seven
}

function Test-ZipFile {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return $false }
    $len = (Get-Item $Path).Length
    if ($len -lt 1024) { return $false }
    $bytes = Get-Content -Path $Path -Encoding Byte -TotalCount 2
    if ($bytes.Count -lt 2) { return $false }
    return ($bytes[0] -eq 0x50 -and $bytes[1] -eq 0x4B)
}

Ensure-Dir $BinDir

$tempRoot = Join-Path $env:TEMP ("space_watcher_bins_" + [Guid]::NewGuid().ToString("N"))
Ensure-Dir $tempRoot

try {
    # yt-dlp
    $ytUrl = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
    Download-File $ytUrl (Join-Path $BinDir "yt-dlp.exe")

    # ffmpeg (try multiple sources)
    $ffSources = @(
        "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
        "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    )
    $ffExe = $null
    foreach ($ffUrl in $ffSources) {
        $ffZip = Join-Path $tempRoot "ffmpeg.zip"
        if (Test-Path $ffZip) { Remove-Item $ffZip -Force }
        Download-File $ffUrl $ffZip
        if (-not (Test-ZipFile $ffZip)) { continue }
        $ffOut = Join-Path $tempRoot "ffmpeg"
        if (Test-Path $ffOut) { Remove-Item $ffOut -Recurse -Force }
        Ensure-Dir $ffOut
        $seven = Get-SevenZip $tempRoot
        & $seven x $ffZip ("-o" + $ffOut) -y | Out-Null
        $ffExe = Get-ChildItem -Path $ffOut -Recurse -Filter "ffmpeg.exe" | Select-Object -First 1
        if ($ffExe) { break }
    }
    if (-not $ffExe) { throw "ffmpeg.exe not found after extraction." }
    Copy-Item -Path $ffExe.FullName -Destination (Join-Path $BinDir "ffmpeg.exe") -Force

    # mpv (latest release from zhongfly/mpv-winbuild)
    $mpvApi = "https://api.github.com/repos/zhongfly/mpv-winbuild/releases/latest"
    $mpvRelease = Invoke-RestMethod -Uri $mpvApi -Headers @{ "User-Agent" = "space-watcher" }
    $mpvAsset = $mpvRelease.assets | Where-Object { $_.name -match '^mpv-x86_64-(?!v3).*\.7z$' } | Select-Object -First 1
    if (-not $mpvAsset) {
        $mpvAsset = $mpvRelease.assets | Where-Object { $_.name -match '^mpv-x86_64-.*\.7z$' } | Select-Object -First 1
    }
    if (-not $mpvAsset) { throw "mpv-x86_64*.7z asset not found in latest mpv-winbuild release." }

    $mpv7z = Join-Path $tempRoot $mpvAsset.name
    Download-File $mpvAsset.browser_download_url $mpv7z

    $seven = Get-SevenZip $tempRoot

    $mpvOut = Join-Path $tempRoot "mpv"
    Ensure-Dir $mpvOut
    & $seven x $mpv7z ("-o" + $mpvOut) -y | Out-Null

    $mpvExe = Get-ChildItem -Path $mpvOut -Recurse -Filter "mpv.exe" | Select-Object -First 1
    if (-not $mpvExe) { throw "mpv.exe not found after extraction." }
    Copy-Item -Path (Join-Path $mpvExe.Directory.FullName "*") -Destination $BinDir -Force

    Write-Host "[ok] Binaries are in: $BinDir"
} finally {
    try {
        Remove-Item -Path $tempRoot -Recurse -Force
    } catch {
        # ignore cleanup errors
    }
}
