const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { installRuntime } = require('../src/runtime');

test('installRuntime links venv qiaoya into skill bundle when pipx bin dir stays empty', async () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'qiaoya-runtime-'));
  const bundleDir = path.join(tmp, 'bundle');
  const scriptsDir = path.join(bundleDir, 'scripts');
  const runtimeHome = path.join(bundleDir, '.runtime');
  const venvBinDir = path.join(runtimeHome, 'venvs', 'cli-anything-qiaoya', 'bin');
  const venvScript = path.join(venvBinDir, 'qiaoya');

  fs.mkdirSync(scriptsDir, { recursive: true });
  fs.mkdirSync(venvBinDir, { recursive: true });
  fs.writeFileSync(venvScript, '#!/bin/sh\necho qiaoya\n', { mode: 0o755 });

  const calls = [];
  const result = await installRuntime({
    runtimeSource: './agent-harness',
    cwd: tmp,
    bundleDir,
    env: process.env,
    deps: {
      commandExists: (command) => ({ ok: true, detail: `/mock/${command}` }),
      run: (command, args) => {
        calls.push([command, ...args]);
        if (command === 'pipx') {
          return '';
        }
        if (command === path.join(scriptsDir, 'qiaoya')) {
          return 'Usage: qiaoya [OPTIONS] COMMAND [ARGS]...\n';
        }
        throw new Error(`unexpected command: ${command} ${args.join(' ')}`);
      },
    },
  });

  assert.equal(result.scriptPath, path.join(scriptsDir, 'qiaoya'));
  assert.equal(result.runtimeHome, runtimeHome);
  assert.equal(fs.existsSync(path.join(scriptsDir, 'qiaoya')), true);
  assert.deepEqual(
    calls.slice(0, 2),
    [
      ['pipx', 'uninstall', 'cli-anything-qiaoya'],
      ['pipx', 'install', './agent-harness'],
    ],
  );
});
