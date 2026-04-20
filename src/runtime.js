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

async function installRuntime({ runtimeSource = DEFAULT_RUNTIME_SPEC, cwd, env = process.env }) {
  const python3 = commandExists('python3');
  const pipx = commandExists('pipx');
  if (!python3.ok) {
    throw new Error('缺少 python3，当前 bootstrap 仍依赖 Python runtime');
  }
  if (!pipx.ok) {
    throw new Error('缺少 pipx，无法安装 qiaoya runtime');
  }

  let installed = '';
  try {
    installed = run('pipx', ['list', '--short'], { cwd, env, capture: true });
  } catch {
    installed = '';
  }

  if (installed.split('\n').some((line) => line.trim().startsWith(PACKAGE_NAME))) {
    try {
      run('pipx', ['uninstall', PACKAGE_NAME], { cwd, env });
    } catch {
      // ignore
    }
  }

  run('pipx', ['install', runtimeSource], { cwd, env });
  const qiaoyaCommand = env.PIPX_BIN_DIR ? path.join(env.PIPX_BIN_DIR, 'qiaoya') : 'qiaoya';
  const helpOutput = run(qiaoyaCommand, ['--help'], { cwd, env, capture: true });
  return { runtimeCheck: helpOutput };
}

async function getDoctorReport({
  codexHome,
  env = process.env,
  fs = require('node:fs'),
  path = require('node:path'),
}) {
  const skillPath = path.join(codexHome, 'skills', 'qiaoya', 'SKILL.md');
  let runtimeDetail = 'qiaoya not found';
  let runtimeOk = false;
  try {
    runtimeDetail = run('qiaoya', ['--help'], { env, capture: true }).split('\n')[0];
    runtimeOk = true;
  } catch {
    runtimeOk = false;
  }

  return {
    python3: commandExists('python3'),
    pipx: commandExists('pipx'),
    codexHome: { ok: true, detail: codexHome },
    skill: { ok: fs.existsSync(skillPath), detail: skillPath },
    runtime: { ok: runtimeOk, detail: runtimeDetail },
  };
}

module.exports = {
  DEFAULT_RUNTIME_SPEC,
  installRuntime,
  getDoctorReport,
};
