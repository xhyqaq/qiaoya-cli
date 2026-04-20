const os = require('node:os');
const path = require('node:path');
const fs = require('node:fs');

const { installCodexSkill } = require('./installers/codex');
const { installRuntime, getDoctorReport, DEFAULT_RUNTIME_SPEC } = require('./runtime');
const { installBinaryRuntime } = require('./binary');
const { version: packageVersion } = require('../package.json');

function printHelp(logger) {
  logger.log(`qiaoya agent bootstrap

Usage:
  npx qiaoya
  npx qiaoya install [--codex-home <path>] [--runtime-source <spec-or-path>] [--binary-source <file-or-url>] [--runtime-kind auto|python|binary]
  npx qiaoya doctor [--codex-home <path>]
  npx qiaoya --help

Commands:
  install   安装 Codex skill 与 qiaoya runtime
  doctor    检查 python3、pipx、Codex skill 与 runtime
  help      显示帮助
`);
}

function parseArgs(argv) {
  const args = [...argv];
  const options = {
    agent: 'codex',
    codexHome: path.join(os.homedir(), '.codex'),
    runtimeSource: DEFAULT_RUNTIME_SPEC,
    binarySource: null,
    runtimeKind: 'auto',
    force: true,
  };

  let command = 'install';
  if (args[0] && !args[0].startsWith('-')) {
    command = args.shift();
  }

  while (args.length > 0) {
    const token = args.shift();
    if (token === '--help' || token === '-h') {
      command = 'help';
      continue;
    }
    if (token === '--agent') {
      options.agent = args.shift() || options.agent;
      continue;
    }
    if (token === '--codex-home') {
      options.codexHome = path.resolve(args.shift() || options.codexHome);
      continue;
    }
    if (token === '--runtime-source') {
      options.runtimeSource = args.shift() || options.runtimeSource;
      continue;
    }
    if (token === '--binary-source') {
      options.binarySource = args.shift() || options.binarySource;
      continue;
    }
    if (token === '--runtime-kind') {
      options.runtimeKind = args.shift() || options.runtimeKind;
      continue;
    }
    if (token === '--force') {
      options.force = true;
      continue;
    }
  }

  return { command, options };
}

function printDoctorReport(report, logger) {
  Object.entries(report).forEach(([name, item]) => {
    logger.log(`${item.ok ? 'OK' : 'FAIL'} ${name}: ${item.detail}`);
  });
}

function writeBundleMetadata(bundleDir, runtimeResult) {
  const versionPath = path.join(bundleDir, 'VERSION');
  const metaPath = path.join(bundleDir, 'install-meta.json');
  fs.writeFileSync(versionPath, `${packageVersion}\n`, 'utf8');
  fs.writeFileSync(
    metaPath,
    JSON.stringify(
      {
        packageVersion,
        installedAt: new Date().toISOString(),
        runtime: {
          mode: runtimeResult.mode || 'python-runtime',
          source: runtimeResult.source || null,
          scriptPath: runtimeResult.scriptPath || null,
          runtimeHome: runtimeResult.runtimeHome || null,
        },
      },
      null,
      2,
    ),
    'utf8',
  );
}

async function main(argv = process.argv.slice(2), deps = {}) {
  const logger = deps.logger || console;
  const cwd = deps.cwd || process.cwd();
  const resolved = parseArgs(argv);
  const skillSourceDir = path.resolve(cwd, 'skills', 'qiaoya');
  const runtimeInstaller = deps.installRuntime || installRuntime;
  const binaryInstaller = deps.installBinaryRuntime || installBinaryRuntime;
  const doctorReporter = deps.getDoctorReport || getDoctorReport;

  if (resolved.command === 'help') {
    printHelp(logger);
    return;
  }

  if (resolved.command === 'doctor') {
    const report = await doctorReporter({
      codexHome: resolved.options.codexHome,
    });
    printDoctorReport(report, logger);
    return;
  }

  if (resolved.options.agent !== 'codex') {
    throw new Error(`当前仅支持 agent=codex，收到: ${resolved.options.agent}`);
  }

  const skillInstall = installCodexSkill({
    codexHome: resolved.options.codexHome,
    skillSourceDir,
    force: resolved.options.force,
  });
  logger.log(`qiaoya skill bundle 已安装到 ${skillInstall.targetDir}`);

  let runtimeResult;
  const runtimeKind = resolved.options.runtimeKind;
  const binaryRequested = runtimeKind === 'binary' || (runtimeKind === 'auto' && !!resolved.options.binarySource);

  if (binaryRequested || runtimeKind === 'auto') {
    try {
      runtimeResult = await binaryInstaller({
        bundleDir: skillInstall.targetDir,
        binarySource: resolved.options.binarySource || undefined,
      });
      logger.log('binary runtime 安装成功');
    } catch (error) {
      if (runtimeKind === 'binary') {
        throw error;
      }
      logger.log(`binary runtime 安装失败，回退到 python runtime: ${error.message}`);
    }
  }

  if (!runtimeResult) {
    runtimeResult = await runtimeInstaller({
      runtimeSource: resolved.options.runtimeSource,
      cwd,
      bundleDir: skillInstall.targetDir,
    });
    logger.log('python runtime 安装成功');
  }

  writeBundleMetadata(skillInstall.targetDir, runtimeResult);

  logger.log(`qiaoya runtime 已安装到 ${runtimeResult.scriptPath || path.join(skillInstall.targetDir, 'scripts', 'qiaoya')}`);
  if (runtimeResult && runtimeResult.runtimeCheck) {
    logger.log('runtime check: ok');
  }
  logger.log('qiaoya 脚本现在已经可直接使用。');
  logger.log('如果当前 Codex 会话还没发现这个新 skill，重启或开启新会话后会稳定生效。');
}

module.exports = {
  main,
  parseArgs,
};
