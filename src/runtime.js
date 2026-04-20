const { execFileSync } = require('node:child_process');
const path = require('node:path');

const DEFAULT_RUNTIME_SPEC = 'git+https://github.com/xhyqaq/qiaoya-cli.git#subdirectory=agent-harness';
const PACKAGE_NAME = 'cli-anything-qiaoya';

function commandExists(command) {
  try {
    const output = execFileSync('which', [command], { encoding: 'utf8' }).trim();
    return { ok: true, detail: output };
  } catch {
    return { ok: false, detail: `${command} not found` };
  }
}

function run(command, args, options = {}) {
  return execFileSync(command, args, {
    encoding: 'utf8',
    stdio: options.capture ? ['ignore', 'pipe', 'pipe'] : 'pipe',
    cwd: options.cwd,
    env: options.env || process.env,
  });
}

async function installRuntime({ runtimeSource = DEFAULT_RUNTIME_SPEC, cwd, env = process.env, bundleDir }) {
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
  const qiaoyaCommand = path.join(scriptsDir, 'qiaoya');
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
    runtimeDetail = run(scriptPath, ['--help'], { env, capture: true }).split('\n')[0];
    runtimeOk = true;
  } catch {
    runtimeOk = false;
  }

  return {
    python3: commandExists('python3'),
    pipx: commandExists('pipx'),
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
