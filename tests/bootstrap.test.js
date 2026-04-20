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
  assert.equal(fs.existsSync(skillPath), true);
  assert.equal(fs.existsSync(scriptsDir), true);
  assert.equal(runtimeCalls.length, 1);
  assert.equal(runtimeCalls[0].runtimeSource, './agent-harness');
  assert.equal(runtimeCalls[0].bundleDir, bundleDir);
  assert.match(fs.readFileSync(skillPath, 'utf8'), /欢迎页课程/);
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
      runtime: { ok: true, detail: 'Usage: qiaoya' },
    }),
  });

  const output = logger.lines.join('\n');
  assert.match(output, /python3/);
  assert.match(output, /pipx/);
  assert.match(output, /skillBundle/);
  assert.match(output, /script/);
  assert.match(output, /runtime/);
});
