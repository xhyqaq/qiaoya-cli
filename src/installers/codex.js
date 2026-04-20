const fs = require('node:fs');
const path = require('node:path');

function copyDirectory(sourceDir, targetDir) {
  fs.mkdirSync(targetDir, { recursive: true });
  const entries = fs.readdirSync(sourceDir, { withFileTypes: true });
  for (const entry of entries) {
    const sourcePath = path.join(sourceDir, entry.name);
    const targetPath = path.join(targetDir, entry.name);
    if (entry.isDirectory()) {
      copyDirectory(sourcePath, targetPath);
    } else {
      fs.copyFileSync(sourcePath, targetPath);
    }
  }
}

function installCodexSkill({ codexHome, skillSourceDir, force = true }) {
  const targetDir = path.join(codexHome, 'skills', 'qiaoya');
  if (fs.existsSync(targetDir) && force) {
    fs.rmSync(targetDir, { recursive: true, force: true });
  }
  copyDirectory(skillSourceDir, targetDir);
  return { targetDir };
}

module.exports = {
  installCodexSkill,
};
