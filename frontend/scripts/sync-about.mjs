// Copies the About-box content from docs/about/ into src/demo/about/ so the Vite
// bundle (and the Docker frontend image, whose build context excludes docs/) can
// read it. docs/about/ is the single source of truth; src/demo/about/ is a mirror
// that a Vitest drift test keeps honest. Without docs/ (Docker build) it is a no-op.
import { cpSync, existsSync, mkdirSync, readdirSync, rmSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const source = join(root, '..', 'docs', 'about');
const target = join(root, 'src', 'demo', 'about');
// Numbered section files and static assets only; the Walkthru steps, the exported
// demo data and RECORDING.md are not About-box content.
const isAboutFile = (name) => /^\d{2}-.+\.md$/.test(name) || name.endsWith('.svg');

if (!existsSync(source)) {
  console.log('sync-about: docs/about not found (Docker build?) - keeping the committed mirror');
  process.exit(0);
}

mkdirSync(target, { recursive: true });
for (const name of readdirSync(target).filter(isAboutFile)) rmSync(join(target, name));
for (const name of readdirSync(source).filter(isAboutFile)) cpSync(join(source, name), join(target, name));
console.log('sync-about: mirrored docs/about -> src/demo/about');
