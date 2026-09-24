// eslint.complexity.config.js — complexity-only config for complexity-report.sh
// Scans src/ for cyclomatic (≤10) and cognitive (≤15) complexity; does not replace .eslintrc.cjs.
module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  parser: '@typescript-eslint/parser',
  plugins: ['@typescript-eslint', 'sonarjs'],
  rules: {
    complexity: ['error', 10],
    'sonarjs/cognitive-complexity': ['error', 15],
  },
  ignorePatterns: ['dist', 'node_modules', 'coverage', '*.config.*', '*.d.ts'],
};
