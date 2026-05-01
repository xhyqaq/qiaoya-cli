$ErrorActionPreference = "Stop"

$ReleaseBaseUrl = if ($env:QIAOYA_RELEASE_BASE_URL) { $env:QIAOYA_RELEASE_BASE_URL } else { "https://code.xhyovo.cn/downloads/qiaoya/latest" }
$Agents = if ($env:QIAOYA_AGENTS) { $env:QIAOYA_AGENTS } else { "auto" }
$ProjectDir = if ($env:QIAOYA_PROJECT_DIR) { $env:QIAOYA_PROJECT_DIR } else { "" }

function Get-AssetName {
  $arch = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString().ToLowerInvariant()
  switch ($arch) {
    "x64" { return "qiaoya-windows-amd64.exe" }
    "arm64" { return "qiaoya-windows-arm64.exe" }
    default { throw "暂不支持当前架构: $arch" }
  }
}

function Get-Checksum($checksumsPath, $assetName) {
  foreach ($line in Get-Content $checksumsPath) {
    $parts = $line.Trim() -split "\s+"
    if ($parts.Length -ge 2 -and $parts[1] -eq $assetName) {
      return $parts[0]
    }
  }
  throw "checksums.txt 中未找到 $assetName"
}

$assetName = Get-AssetName
$tmpDir = Join-Path ([System.IO.Path]::GetTempPath()) ("qiaoya-install-" + [System.Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tmpDir | Out-Null

try {
  $binaryPath = Join-Path $tmpDir "qiaoya.exe"
  $checksumsPath = Join-Path $tmpDir "checksums.txt"

  Write-Host "下载 qiaoya: $assetName"
  Invoke-WebRequest -Uri "$ReleaseBaseUrl/$assetName" -OutFile $binaryPath
  Invoke-WebRequest -Uri "$ReleaseBaseUrl/checksums.txt" -OutFile $checksumsPath

  $expected = Get-Checksum $checksumsPath $assetName
  $actual = (Get-FileHash -Algorithm SHA256 $binaryPath).Hash.ToLowerInvariant()
  if ($actual -ne $expected.ToLowerInvariant()) {
    throw "SHA256 校验失败: $assetName"
  }

  if ($ProjectDir) {
    & $binaryPath install --agents $Agents --project-dir $ProjectDir
  } else {
    & $binaryPath install --agents $Agents
  }

  Write-Host ""
  Write-Host "安装完成。请重启 Codex / Claude Code，或在 Cursor / Windsurf 项目里重新加载规则。"
} finally {
  Remove-Item -Recurse -Force $tmpDir -ErrorAction SilentlyContinue
}
