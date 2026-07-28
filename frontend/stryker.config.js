// @ts-check
/** @type {import('@stryker-mutator/api/core').PartialStrykerOptions} */
const config = {
  testRunner: 'vitest',
  // Nightly budget: pure logic only (DECISIONS #163 / Slice 44 Residual §4).
  // Screens/components/chrome stay out of mutate — coverage floors own that surface.
  mutate: [
    'src/utils/**/*.ts',
    'src/services/**/*.ts',
    'src/hooks/**/*.ts',
    '!src/**/*.test.*',
    '!src/test/**',
  ],
  reporters: ['html', 'json', 'clear-text', 'progress'],
  htmlReporter: { fileName: 'reports/mutation/index.html' },
  jsonReporter: { fileName: 'reports/mutation/mutation-report.json' },
  coverageAnalysis: 'perTest',
  thresholds: { high: 80, low: 60, break: null },
  timeoutMS: 30000,
  concurrency: 4,
  // JS equivalent of residual Should "ignoreConstants/ignoreStringLiterals"
  // (.NET option names); skip static + string-literal mutants for Nightly budget.
  ignoreStatic: true,
  mutator: {
    excludedMutations: ['StringLiteral'],
  },
}
export default config
