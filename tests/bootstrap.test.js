const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { main } = require('../src/bootstrap');

function makeLogger() {
  const lines = [];
  return {
    lines,
    log: (...args) => lines.push(args.join(' ')),
    error: (...args) => lines.push(args.join(' ')),
  };
}

test('help prints bootstrap usage', async () => {
  const logger = makeLogger();

  await main(['--help'], {
    logger,
    cwd: process.cwd(),
  });

  assert.match(logger.lines.join('\n'), /npx qiaoya/);
  assert.match(logger.lines.join('\n'), /install/);
  assert.match(logger.lines.join('\n'), /doctor/);
});

test('install copies skill into codex home and runs runtime install', async () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'qiaoya-bootstrap-'));
  const codexHome = path.join(tmp, '.codex');
  const runtimeCalls = [];
  const logger = makeLogger();

  await main(['install', '--codex-home', codexHome, '--runtime-source', './agent-harness'], {
    logger,
    cwd: process.cwd(),
    installRuntime: async (options) => {
      runtimeCalls.push(options);
      return { runtimeCheck: 'ok' };
    },
  });

  const bundleDir = path.join(codexHome, 'skills', 'qiaoya');
  const skillPath = path.join(bundleDir, 'SKILL.md');
  const scriptsDir = path.join(bundleDir, 'scripts');
  const versionPath = path.join(bundleDir, 'VERSION');
  const metaPath = path.join(bundleDir, 'install-meta.json');
  assert.equal(fs.existsSync(skillPath), true);
  assert.equal(fs.existsSync(scriptsDir), true);
  assert.equal(fs.existsSync(versionPath), true);
  assert.equal(fs.existsSync(metaPath), true);
  assert.equal(runtimeCalls.length, 1);
  assert.equal(runtimeCalls[0].runtimeSource, './agent-harness');
  assert.equal(runtimeCalls[0].bundleDir, bundleDir);
  assert.match(fs.readFileSync(skillPath, 'utf8'), /欢迎页课程/);
  assert.equal(JSON.parse(fs.readFileSync(metaPath, 'utf8')).runtime.mode, 'python-runtime');
  assert.match(logger.lines.join('\n'), /qiaoya skill bundle 已安装/);
});

test('doctor reports python and pipx checks', async () => {
  const logger = makeLogger();

  await main(['doctor'], {
    logger,
    cwd: process.cwd(),
    getDoctorReport: async () => ({
      python3: { ok: true, detail: '/usr/bin/python3' },
      pipx: { ok: true, detail: '/usr/bin/pipx' },
      codexHome: { ok: true, detail: '/tmp/.codex' },
      skillBundle: { ok: true, detail: '/tmp/.codex/skills/qiaoya' },
      script: { ok: false, detail: 'missing scripts/qiaoya' },
      version: { ok: true, detail: '/tmp/.codex/skills/qiaoya/VERSION' },
      installMeta: { ok: true, detail: '/tmp/.codex/skills/qiaoya/install-meta.json' },
      runtime: { ok: true, detail: 'Usage: qiaoya' },
    }),
  });

  const output = logger.lines.join('\n');
  assert.match(output, /python3/);
  assert.match(output, /pipx/);
  assert.match(output, /skillBundle/);
  assert.match(output, /script/);
  assert.match(output, /version/);
  assert.match(output, /installMeta/);
  assert.match(output, /runtime/);
});

test('binary runtime mode uses binary installer', async () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'qiaoya-bootstrap-bin-'));
  const codexHome = path.join(tmp, '.codex');
  const logger = makeLogger();
  const binaryCalls = [];

  await main([
    'install',
    '--codex-home', codexHome,
    '--runtime-kind', 'binary',
    '--binary-source', '/tmp/qiaoya-binary',
  ], {
    logger,
    cwd: process.cwd(),
    installBinaryRuntime: async (options) => {
      binaryCalls.push(options);
      return { scriptPath: path.join(codexHome, 'skills', 'qiaoya', 'scripts', 'qiaoya') };
    },
  });

  assert.equal(binaryCalls.length, 1);
  assert.equal(binaryCalls[0].binarySource, '/tmp/qiaoya-binary');
  assert.match(logger.lines.join('\n'), /runtime 已安装到/);
});

test('auto mode falls back to python runtime when binary install fails', async () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'qiaoya-bootstrap-auto-'));
  const codexHome = path.join(tmp, '.codex');
  const logger = makeLogger();
  let pythonCalled = 0;

  await main([
    'install',
    '--codex-home', codexHome,
    '--runtime-source', './agent-harness',
  ], {
    logger,
    cwd: process.cwd(),
    installBinaryRuntime: async () => {
      throw new Error('no release asset');
    },
    installRuntime: async () => {
      pythonCalled += 1;
      return { mode: 'python-runtime', source: './agent-harness', scriptPath: path.join(codexHome, 'skills', 'qiaoya', 'scripts', 'qiaoya') };
    },
  });

  assert.equal(pythonCalled, 1);
  assert.match(logger.lines.join('\n'), /回退到 python runtime/);
});
