// @ts-check
/** @type {import('@stryker-mutator/api/core').PartialStrykerOptions} */
const config = {
  testRunner: 'vitest',
  mutate: ['src/**/*.ts', 'src/**/*.tsx', '!src/**/*.test.*', '!src/test/**'],
  reporters: ['html', 'json', 'clear-text'],
  htmlReporter: { fileName: 'reports/mutation/index.html' },
  jsonReporter: { fileName: 'reports/mutation/mutation-report.json' },
  coverageAnalysis: 'perTest',
  thresholds: { high: 80, low: 60, break: null },
  timeoutMS: 30000,
  concurrency: 2,
}
export default config
