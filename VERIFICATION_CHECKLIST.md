# Progress Feedback Verification Checklist

## Pre-Verification Setup

1. **Start backend server:**
   ```bash
   uvicorn server.main:app --reload --port 8001
   ```

2. **Start frontend dev server:**
   ```bash
   cd frontend && npm run dev
   ```

3. **Ensure you have:**
   - At least one experiment in the database
   - Experiment with multiple queries for SearchExplorer testing

**Optional smoke checks** (backend + data prerequisites):

- **Atlas Local:** [MongoDB Setup → Path B](docs/user-guide/mongodb-setup.md#path-b--atlas-local-docker) — `./start-services.sh --local`, then submit `example-mongodb-local.yaml`
- **SIE sweep:** [SIE Setup → verification](docs/user-guide/sie-setup.md#6-verify-the-sie-sweep) — gateway or Docker warm, then `example-mongodb-sie.yaml`

## Test Cases

### ✅ Test 1: SearchExplorerScreen Re-Query Progress

**Steps:**
1. Navigate to `/` (Experiments list)
2. Click on any experiment to view details
3. Click "Explore Results" to open SearchExplorerScreen
4. Wait for initial load to complete (LoadingFeedbackPanel shows, then hides)
5. **Action:** Change the query filter in the dropdown at the top
6. **Expected:** LoadingFeedbackPanel re-appears immediately
7. **Verify:**
   - [ ] Panel title shows "Refreshing results…" (not "Loading results…")
   - [ ] Subtitle shows "Re-fetching explorer data (query filter changed or refresh triggered)."
   - [ ] Progress bar appears and shows byte-level progress
   - [ ] Activity feed shows fetch milestones
   - [ ] Panel disappears when load completes
   - [ ] New results appear correctly

**Success Criteria:** Users see clear visual feedback during query filter changes

---

### ✅ Test 2: ExperimentsScreen Polling Indicator

**Steps:**
1. Navigate to `/` (Experiments list)
2. Wait for initial load to complete (LoadingFeedbackPanel shows, then disappears)
3. Keep the page open for at least 3 seconds
4. **Expected:** Subtle "Syncing..." indicator appears briefly at bottom
5. **Verify:**
   - [ ] Indicator shows blue pulsing dot + "Syncing..." text
   - [ ] Indicator appears every 2 seconds (EXPERIMENTS_POLL_MS)
   - [ ] Indicator disappears after poll completes (~100-500ms)
   - [ ] Indicator does NOT show during initial load (only after `initialLoadDone`)
   - [ ] No full LoadingFeedbackPanel during polling (unless explicitly triggered)

**Success Criteria:** Non-intrusive indicator shows polling activity without blocking UI

---

### ✅ Test 3: SearchExplorerScreen Polling Indicator

**Steps:**
1. Start a long-running experiment (status: "running")
2. Navigate to SearchExplorer for that experiment
3. Wait for initial load to complete
4. Keep the page open and watch top-right area
5. **Expected:** "Syncing..." indicator appears every 2 seconds while experiment is running
6. **Verify:**
   - [ ] Indicator shows in top-right corner
   - [ ] Indicator appears every 2 seconds (DETAIL_POLL_MS)
   - [ ] Indicator disappears after poll completes
   - [ ] Indicator stops appearing when experiment status changes to "complete"
   - [ ] Data updates correctly during polling (new runs appear in table)

**Success Criteria:** Background polling visible but non-intrusive

---

### ✅ Test 4: No Regression on Initial Loads

**Test 4a: ExperimentsScreen Initial Load**
1. Refresh browser (Cmd+R or Ctrl+R)
2. **Expected:** LoadingFeedbackPanel appears immediately
3. **Verify:**
   - [ ] Panel shows "Loading experiments" title
   - [ ] Progress bar shows byte-level progress
   - [ ] Activity feed shows fetch steps
   - [ ] Panel disappears when data loads
   - [ ] Polling indicator starts appearing after initial load

**Test 4b: ExperimentDetailScreen Initial Load**
1. Navigate to any experiment detail page
2. **Expected:** LoadingFeedbackPanel appears during hydration
3. **Verify:**
   - [ ] Panel shows "Loading experiment detail" title
   - [ ] Progress bar and activity feed work
   - [ ] Panel disappears when hydration completes
   - [ ] Live phase progress indicators work (if experiment is running)

**Test 4c: SearchExplorerScreen Initial Load**
1. Navigate to SearchExplorer for any experiment
2. **Expected:** LoadingFeedbackPanel appears
3. **Verify:**
   - [ ] Panel shows "Loading results…" title (not "Refreshing")
   - [ ] Subtitle shows initial load message (not refresh message)
   - [ ] Progress bar and activity feed work
   - [ ] Panel disappears when explorer data loads

**Success Criteria:** Initial loading experience unchanged from before

---

### ✅ Test 5: Large Payload Handling

**Steps:**
1. Create an experiment with 50+ runs and large results (~10MB response)
2. Navigate to SearchExplorer
3. **Expected:** Progress bar shows incremental byte progress
4. **Verify:**
   - [ ] Progress bar starts at 0% and increments visibly
   - [ ] "Payload" section shows bytes received / total bytes
   - [ ] Percentage updates as data streams in
   - [ ] Activity feed shows milestones
   - [ ] Panel doesn't disappear prematurely (waits for full payload)
5. Change query filter
6. **Expected:** Same progress behavior on re-query
7. **Verify:**
   - [ ] Panel re-appears with "Refreshing results…" title
   - [ ] Progress bar resets and shows new download progress
   - [ ] All progress indicators work correctly on re-query

**Success Criteria:** Large payloads show clear incremental progress

---

### ✅ Test 6: Mutual Exclusion (No Conflicting Indicators)

**Steps:**
1. Navigate to ExperimentsScreen
2. Wait for initial load
3. Trigger a manual refresh (implementation-dependent)
4. **Verify:**
   - [ ] When LoadingFeedbackPanel shows → PollingIndicator hidden
   - [ ] When PollingIndicator shows → LoadingFeedbackPanel hidden
   - [ ] Never both visible simultaneously

**Repeat for SearchExplorerScreen:**
1. Navigate to SearchExplorer
2. Wait for initial load
3. Change query filter (triggers full panel)
4. **Verify:**
   - [ ] During re-query load → full panel shows, no polling indicator
   - [ ] After load, during background polling → polling indicator shows, no panel
   - [ ] Mutual exclusion maintained

**Success Criteria:** Only one type of indicator visible at a time

---

### ✅ Test 7: State Cleanup on Unmount

**Steps:**
1. Navigate to ExperimentsScreen
2. Wait for polling to start (see "Syncing..." indicator at least once)
3. Navigate away to a different route
4. **Open browser DevTools console**
5. Check for errors or warnings
6. **Verify:**
   - [ ] No "Can't perform a React state update on an unmounted component" warnings
   - [ ] No console errors related to state updates
   - [ ] No memory leaks visible in React DevTools

**Repeat for SearchExplorerScreen:**
1. Navigate to SearchExplorer with a running experiment
2. Wait for polling to start
3. Navigate back to experiments list
4. **Verify:** Same as above (no unmount warnings/errors)

**Success Criteria:** Clean unmount with no lingering state updates

---

## Regression Test Suite

Run these to ensure no breaking changes:

### TypeScript Compilation
```bash
cd frontend
npm run typecheck
# Expected: 0 errors
```

### Build Production Bundle
```bash
cd frontend
npm run build
# Expected: Successful build, no warnings
```

### Linting
```bash
cd frontend
npm run lint
# Expected: 0 errors (warnings OK if pre-existing)
```

---

## Performance Checks

### 1. Network Tab Inspection

**ExperimentsScreen:**
- [ ] Initial load: 1 request to `GET /experiments`
- [ ] Polling: 1 request every 2s to `GET /experiments` (while page is open)
- [ ] No duplicate or excessive requests

**SearchExplorerScreen:**
- [ ] Initial load: 1 request to `GET /experiments/{id}/explore`
- [ ] Re-query: 1 request to `GET /experiments/{id}/explore?query=...`
- [ ] Polling (running experiment): 2 requests every 2s (experiment status + explore data)
- [ ] No requests when experiment is complete/failed

### 2. React DevTools Profiler

**Before/After Comparison:**
- [ ] No significant increase in re-render count
- [ ] Polling state updates don't trigger unnecessary child re-renders
- [ ] LoadingFeedbackPanel memoization working (if applicable)

---

## Edge Cases

### Edge Case 1: Rapid Query Filter Changes
**Steps:**
1. Navigate to SearchExplorer
2. Rapidly change query filter 5 times in a row
3. **Verify:**
   - [ ] LoadingFeedbackPanel shows for each change
   - [ ] No race conditions (final data matches final selected query)
   - [ ] Activity feed shows all fetch attempts or correctly aborts prior ones
   - [ ] No memory leaks from abandoned requests

### Edge Case 2: Network Failure During Polling
**Steps:**
1. Navigate to ExperimentsScreen
2. Wait for polling to start
3. **Disable network** (DevTools → Network → Offline)
4. Wait 5 seconds
5. **Re-enable network**
6. **Verify:**
   - [ ] Polling indicator still appears during failed attempts
   - [ ] Error state handled gracefully (no crashes)
   - [ ] Polling recovers when network returns
   - [ ] No infinite error loops

### Edge Case 3: Long-Running Query (>30s)
**Steps:**
1. Create experiment with massive dataset (100+ runs, large results)
2. Navigate to SearchExplorer
3. **Expected:** Progress bar shows incremental updates for full duration
4. **Verify:**
   - [ ] Stall watcher warnings appear if >10s with no progress
   - [ ] Activity feed shows "Waiting for first byte..." message
   - [ ] Progress bar indeterminate animation while waiting
   - [ ] Eventual completion or clear error message

---

## Sign-Off Checklist

Before marking complete:
- [ ] All 7 main test cases pass
- [ ] All regression tests pass
- [ ] All edge cases handled correctly
- [ ] No console errors or warnings
- [ ] TypeScript compilation clean
- [ ] Build succeeds
- [ ] Performance acceptable (no noticeable slowdowns)
- [ ] UX feels responsive and informative

**Verified by:** ________________
**Date:** ________________
**Branch:** feat/loading-feedback-to-user
**Commit:** ________________
