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
  const skillSource = path.join(process.cwd(), 'skills', 'qiaoya');
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

  const skillPath = path.join(codexHome, 'skills', 'qiaoya', 'SKILL.md');
  assert.equal(fs.existsSync(skillPath), true);
  assert.equal(runtimeCalls.length, 1);
  assert.equal(runtimeCalls[0].runtimeSource, './agent-harness');
  assert.match(fs.readFileSync(skillPath, 'utf8'), /欢迎页课程/);
  assert.match(logger.lines.join('\n'), /Codex skill 已安装/);
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
      skill: { ok: false, detail: 'missing' },
      runtime: { ok: true, detail: 'qiaoya 1.0.0' },
    }),
  });

  const output = logger.lines.join('\n');
  assert.match(output, /python3/);
  assert.match(output, /pipx/);
  assert.match(output, /runtime/);
});
