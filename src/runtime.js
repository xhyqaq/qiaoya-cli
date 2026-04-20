const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');

const DEFAULT_RUNTIME_SPEC = 'git+https://github.com/xhyqaq/qiaoya-cli.git#subdirectory=agent-harness';
const PACKAGE_NAME = 'cli-anything-qiaoya';

function commandExistsImpl(command) {
  try {
    const output = execFileSync('which', [command], { encoding: 'utf8' }).trim();
    return { ok: true, detail: output };
  } catch {
    return { ok: false, detail: `${command} not found` };
  }
}

function runImpl(command, args, options = {}) {
  return execFileSync(command, args, {
    encoding: 'utf8',
    stdio: options.capture ? ['ignore', 'pipe', 'pipe'] : 'pipe',
    cwd: options.cwd,
    env: options.env || process.env,
  });
}

function ensureBundleScript({ bundleDir, runtimeHome, platform = process.platform }) {
  const scriptsDir = path.join(bundleDir, 'scripts');
  const targetName = platform === 'win32' ? 'qiaoya.exe' : 'qiaoya';
  const targetPath = path.join(scriptsDir, targetName);
  if (fs.existsSync(targetPath)) {
    return targetPath;
  }

  const venvScriptsDir = path.join(
    runtimeHome,
    'venvs',
    PACKAGE_NAME,
    platform === 'win32' ? 'Scripts' : 'bin',
  );
  const sourcePath = path.join(venvScriptsDir, targetName);
  if (!fs.existsSync(sourcePath)) {
    throw new Error(`pipx 安装完成，但未找到 runtime 脚本: ${sourcePath}`);
  }

  fs.mkdirSync(scriptsDir, { recursive: true });
  try {
    fs.symlinkSync(sourcePath, targetPath);
  } catch {
    fs.copyFileSync(sourcePath, targetPath);
    fs.chmodSync(targetPath, 0o755);
  }
  return targetPath;
}

async function installRuntime({
  runtimeSource = DEFAULT_RUNTIME_SPEC,
  cwd,
  env = process.env,
  bundleDir,
  deps = {},
}) {
  const commandExists = deps.commandExists || commandExistsImpl;
  const run = deps.run || runImpl;
  const ensureScript = deps.ensureBundleScript || ensureBundleScript;

  const python3 = commandExists('python3');
  const pipx = commandExists('pipx');
  if (!python3.ok) {
    throw new Error('缺少 python3，当前 bootstrap 仍依赖 Python runtime');
  }
  if (!pipx.ok) {
    throw new Error('缺少 pipx，无法安装 qiaoya runtime');
  }

  if (!bundleDir) {
    throw new Error('缺少 skill bundle 目录，无法安装 runtime');
  }

  const runtimeHome = path.join(bundleDir, '.runtime');
  const scriptsDir = path.join(bundleDir, 'scripts');
  const installEnv = {
    ...env,
    PIPX_HOME: runtimeHome,
    PIPX_BIN_DIR: scriptsDir,
  };

  try {
    run('pipx', ['uninstall', PACKAGE_NAME], { cwd, env: installEnv });
  } catch {
    // ignore
  }

  run('pipx', ['install', runtimeSource], { cwd, env: installEnv });
  const qiaoyaCommand = ensureScript({
    bundleDir,
    runtimeHome,
    platform: env.__QIAOYA_TEST_PLATFORM__ || process.platform,
  });
  const helpOutput = run(qiaoyaCommand, ['--help'], { cwd, env, capture: true });
  return {
    runtimeCheck: helpOutput,
    scriptPath: qiaoyaCommand,
    runtimeHome,
    source: runtimeSource,
    mode: 'python-runtime',
  };
}

async function getDoctorReport({
  codexHome,
  env = process.env,
  fs = require('node:fs'),
  path = require('node:path'),
}) {
  const bundleDir = path.join(codexHome, 'skills', 'qiaoya');
  const skillPath = path.join(bundleDir, 'SKILL.md');
  const scriptPath = path.join(bundleDir, 'scripts', 'qiaoya');
  const versionPath = path.join(bundleDir, 'VERSION');
  const metaPath = path.join(bundleDir, 'install-meta.json');
  let runtimeDetail = 'qiaoya not found';
  let runtimeOk = false;
  try {
    runtimeDetail = runImpl(scriptPath, ['--help'], { env, capture: true }).split('\n')[0];
    runtimeOk = true;
  } catch {
    runtimeOk = false;
  }

  return {
    python3: commandExistsImpl('python3'),
    pipx: commandExistsImpl('pipx'),
    codexHome: { ok: true, detail: codexHome },
    skillBundle: { ok: fs.existsSync(bundleDir), detail: bundleDir },
    script: { ok: fs.existsSync(scriptPath), detail: scriptPath },
    skill: { ok: fs.existsSync(skillPath), detail: skillPath },
    version: { ok: fs.existsSync(versionPath), detail: versionPath },
    installMeta: { ok: fs.existsSync(metaPath), detail: metaPath },
    runtime: { ok: runtimeOk, detail: runtimeDetail },
  };
}

module.exports = {
  DEFAULT_RUNTIME_SPEC,
  installRuntime,
  getDoctorReport,
};
