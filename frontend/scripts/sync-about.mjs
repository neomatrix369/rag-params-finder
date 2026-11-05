// Copies the demo-kit content from docs/about/ into src/demo/ so the Vite bundle
// (and the Docker frontend image, whose build context excludes docs/) can read it.
// docs/about/ is the single source of truth; the src/demo/ copies are mirrors that
// Vitest drift tests keep honest. Without docs/ (Docker build) it is a no-op.
//
// Three things are mirrored:
//   docs/about/*.md               -> src/demo/about/           (About-box sections, Part C1)
//   docs/about/walkthru/*.md      -> src/demo/walkthru/        (Walkthru steps, Part C2)
//   docs/about/demo-results.json  -> src/demo/demo-results.json (bundled demo data, Part C2)
import { copyFileSync, cpSync, existsSync, mkdirSync, readdirSync, rmSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const source = join(root, '..', 'docs', 'about');

if (!existsSync(source)) {
  console.log('sync-about: docs/about not found (Docker build?) - keeping the committed mirror');
  process.exit(0);
}

// Numbered section files and static assets only; the Walkthru steps, the exported
// demo data and RECORDING.md are not About-box content.
const isAboutFile = (name) => /^\d{2}-.+\.md$/.test(name);
const isStepFile = (name) => /^\d{2}-.+\.md$/.test(name);

function mirrorDir(from, to, keep) {
  mkdirSync(to, { recursive: true });
  for (const name of readdirSync(to).filter(keep)) rmSync(join(to, name));
  for (const name of readdirSync(from).filter(keep)) cpSync(join(from, name), join(to, name));
}

// 1) About-box sections + assets.
mirrorDir(source, join(root, 'src', 'demo', 'about'), isAboutFile);

// 2) Walkthru step files (Part C2).
const stepsSource = join(source, 'walkthru');
if (existsSync(stepsSource)) {
  mirrorDir(stepsSource, join(root, 'src', 'demo', 'walkthru'), isStepFile);
}

// 3) Bundled demo results (Part C2 data loader).
const dataSource = join(source, 'demo-results.json');
if (existsSync(dataSource)) {
  copyFileSync(dataSource, join(root, 'src', 'demo', 'demo-results.json'));
}

console.log('sync-about: mirrored docs/about -> src/demo (about, walkthru, demo-results.json)');
