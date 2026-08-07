// eslint.complexity.config.js — complexity-only config for complexity-report.sh
// Scans src/ for cyclomatic complexity violations; does not replace .eslintrc.cjs.
module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  parser: '@typescript-eslint/parser',
  plugins: ['@typescript-eslint'],
  rules: {
    complexity: ['error', 10],
  },
  ignorePatterns: ['dist', 'node_modules', 'coverage', '*.config.*', '*.d.ts'],
};
