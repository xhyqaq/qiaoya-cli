const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const {
  getPlatformTarget,
  getBinaryFileName,
  installBinaryRuntime,
} = require('../src/binary');

test('platform target maps current platform tuple', () => {
  const target = getPlatformTarget({ platform: 'darwin', arch: 'arm64' });
  assert.deepEqual(target, {
    platform: 'darwin',
    arch: 'arm64',
    target: 'darwin-arm64',
    extension: '',
  });
});

test('binary file name uses platform target and qiaoya basename', () => {
  const name = getBinaryFileName({ platform: 'win32', arch: 'x64' });
  assert.equal(name, 'qiaoya-windows-x64.exe');
});

test('installBinaryRuntime copies local binary into bundle scripts path', async () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'qiaoya-binary-'));
  const bundleDir = path.join(tmp, 'bundle');
  const scriptsDir = path.join(bundleDir, 'scripts');
  const fakeBinary = path.join(tmp, 'qiaoya-darwin-arm64');
  fs.mkdirSync(scriptsDir, { recursive: true });
  fs.writeFileSync(fakeBinary, '#!/bin/sh\necho qiaoya-binary\n', { mode: 0o755 });

  const result = await installBinaryRuntime({
    bundleDir,
    binarySource: fakeBinary,
    platform: 'darwin',
    arch: 'arm64',
  });

  assert.equal(result.scriptPath, path.join(scriptsDir, 'qiaoya'));
  assert.equal(fs.existsSync(result.scriptPath), true);
  assert.match(fs.readFileSync(result.scriptPath, 'utf8'), /qiaoya-binary/);
});
