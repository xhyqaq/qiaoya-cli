const fs = require('node:fs');
const path = require('node:path');
const https = require('node:https');
const { execFileSync } = require('node:child_process');

const DEFAULT_RELEASE_BASE_URL = 'https://github.com/xhyqaq/qiaoya-cli/releases/download';
const DEFAULT_RELEASE_LATEST_BASE_URL = 'https://github.com/xhyqaq/qiaoya-cli/releases/latest/download';

function getPlatformTarget({ platform = process.platform, arch = process.arch } = {}) {
  const platformMap = {
    darwin: 'darwin',
    linux: 'linux',
    win32: 'windows',
  };
  const normalizedPlatform = platformMap[platform];
  if (!normalizedPlatform) {
    throw new Error(`不支持的平台: ${platform}`);
  }

  const normalizedArch = arch === 'x64' ? 'x64' : arch === 'arm64' ? 'arm64' : null;
  if (!normalizedArch) {
    throw new Error(`不支持的架构: ${arch}`);
  }

  return {
    platform: normalizedPlatform,
    arch: normalizedArch,
    target: `${normalizedPlatform}-${normalizedArch}`,
    extension: normalizedPlatform === 'windows' ? '.exe' : '',
  };
}

function getBinaryFileName({ platform = process.platform, arch = process.arch } = {}) {
  const target = getPlatformTarget({ platform, arch });
  return `qiaoya-${target.target}${target.extension}`;
}

function copyExecutable(sourcePath, targetPath) {
  fs.mkdirSync(path.dirname(targetPath), { recursive: true });
  fs.copyFileSync(sourcePath, targetPath);
  fs.chmodSync(targetPath, 0o755);
}

function runBinaryHelp(scriptPath) {
  return execFileSync(scriptPath, ['--help'], {
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  });
}

function isRemoteSource(value) {
  return typeof value === 'string' && /^https?:\/\//i.test(value);
}

function buildReleaseDownloadUrl({
  releaseBaseUrl = DEFAULT_RELEASE_BASE_URL,
  latestBaseUrl = DEFAULT_RELEASE_LATEST_BASE_URL,
  version = 'latest',
  assetName,
}) {
  if (version === 'latest') {
    return `${latestBaseUrl}/${assetName}`;
  }
  return `${releaseBaseUrl}/${version}/${assetName}`;
}

function downloadToFile(url, targetPath) {
  return new Promise((resolve, reject) => {
    fs.mkdirSync(path.dirname(targetPath), { recursive: true });
    const file = fs.createWriteStream(targetPath, { mode: 0o755 });
    https.get(url, (response) => {
      if (response.statusCode !== 200) {
        file.close();
        fs.rmSync(targetPath, { force: true });
        if (response.statusCode === 404) {
          reject(new Error(`release 二进制资产尚未就绪: HTTP ${response.statusCode}`));
          return;
        }
        reject(new Error(`下载二进制失败: HTTP ${response.statusCode}`));
        return;
      }
      response.pipe(file);
      file.on('finish', () => {
        file.close(() => resolve(targetPath));
      });
    }).on('error', (error) => {
      file.close();
      fs.rmSync(targetPath, { force: true });
      reject(error);
    });
  });
}

async function installBinaryRuntime({
  bundleDir,
  binarySource,
  releaseBaseUrl = DEFAULT_RELEASE_BASE_URL,
  version = 'latest',
  platform = process.platform,
  arch = process.arch,
}) {
  if (!bundleDir) {
    throw new Error('缺少 skill bundle 目录，无法安装 binary runtime');
  }
  const scriptsDir = path.join(bundleDir, 'scripts');
  const targetName = platform === 'win32' ? 'qiaoya.exe' : 'qiaoya';
  const targetPath = path.join(scriptsDir, targetName);

  if (binarySource) {
    if (isRemoteSource(binarySource)) {
      await downloadToFile(binarySource, targetPath);
      return {
        scriptPath: targetPath,
        source: binarySource,
        mode: 'remote-binary',
        runtimeCheck: runBinaryHelp(targetPath),
      };
    }
    copyExecutable(binarySource, targetPath);
    return {
      scriptPath: targetPath,
      source: binarySource,
      mode: 'local-binary',
      runtimeCheck: runBinaryHelp(targetPath),
    };
  }

  const assetName = getBinaryFileName({ platform, arch });
  const downloadUrl = buildReleaseDownloadUrl({
    releaseBaseUrl,
    version,
    assetName,
  });
  await downloadToFile(downloadUrl, targetPath);
  return {
    scriptPath: targetPath,
    source: downloadUrl,
    mode: 'remote-binary',
    runtimeCheck: runBinaryHelp(targetPath),
  };
}

module.exports = {
  DEFAULT_RELEASE_BASE_URL,
  DEFAULT_RELEASE_LATEST_BASE_URL,
  getPlatformTarget,
  getBinaryFileName,
  buildReleaseDownloadUrl,
  installBinaryRuntime,
};
