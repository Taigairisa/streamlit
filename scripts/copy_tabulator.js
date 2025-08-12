const fs = require('fs');
const path = require('path');

function ensureDir(p) {
  if (!fs.existsSync(p)) {
    fs.mkdirSync(p, { recursive: true });
  }
}

function copyFile(src, dest) {
  ensureDir(path.dirname(dest));
  fs.copyFileSync(src, dest);
  console.log(`Copied: ${src} -> ${dest}`);
}

function main() {
  const root = process.cwd();
  const nm = path.join(root, 'node_modules', 'tabulator-tables', 'dist');
  const jsSrc = path.join(nm, 'js', 'tabulator.min.js');
  const cssSrc = path.join(nm, 'css', 'tabulator.min.css');

  const jsDest = path.join(root, 'static', 'vendor', 'tabulator', 'js', 'tabulator.min.js');
  const cssDest = path.join(root, 'static', 'vendor', 'tabulator', 'css', 'tabulator.min.css');

  if (!fs.existsSync(jsSrc) || !fs.existsSync(cssSrc)) {
    console.error('tabulator-tables is not installed or files are missing.');
    process.exit(0);
  }

  copyFile(jsSrc, jsDest);
  copyFile(cssSrc, cssDest);
}

main();

