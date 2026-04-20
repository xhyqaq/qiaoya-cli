const os = require('node:os');
const path = require('node:path');

const { installCodexSkill } = require('./installers/codex');
const { installRuntime, getDoctorReport, DEFAULT_RUNTIME_SPEC } = require('./runtime');

function printHelp(logger) {
  logger.log(`qiaoya agent bootstrap

Usage:
  npx qiaoya
  npx qiaoya install [--codex-home <path>] [--runtime-source <spec-or-path>]
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

async function main(argv = process.argv.slice(2), deps = {}) {
  const logger = deps.logger || console;
  const cwd = deps.cwd || process.cwd();
  const resolved = parseArgs(argv);
  const skillSourceDir = path.resolve(cwd, 'skills', 'qiaoya');
  const runtimeInstaller = deps.installRuntime || installRuntime;
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

  const runtimeResult = await runtimeInstaller({
    runtimeSource: resolved.options.runtimeSource,
    cwd,
    bundleDir: skillInstall.targetDir,
  });

  logger.log(`qiaoya runtime 已安装到 ${runtimeResult.scriptPath || path.join(skillInstall.targetDir, 'scripts', 'qiaoya')}`);
  if (runtimeResult && runtimeResult.runtimeCheck) {
    logger.log('runtime check: ok');
  }
  logger.log('重启 Codex 后新的 qiaoya skill 才会被加载。');
}

module.exports = {
  main,
  parseArgs,
};
