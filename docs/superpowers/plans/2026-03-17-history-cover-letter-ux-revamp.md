# History Cover Letter UX Revamp Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Revamp the cover letter history page with richer cards (inline status pipeline, match bar), a two-row preview header with metadata strip, and a tabbed preview pane showing cover letter text or fit analysis.

**Architecture:** All changes are in `frontend/src/routes/history/+page.svelte`. Add helper functions, a `STATUS_PIPELINE` constant, `previewTab` state, and rewrite the cover letter card and preview pane markup. No backend changes, no new files.

**Tech Stack:** SvelteKit (Svelte 5 runes), Tailwind CSS 4

---

## Chunk 1: Helpers, Constants, State

### Task 1: Add helpers, STATUS_PIPELINE, previewTab state

**Files:**
- Modify: `frontend/src/routes/history/+page.svelte`

- [ ] **Step 1: Read the current file**

Open `frontend/src/routes/history/+page.svelte` and locate:
- The `<script>` block (lines 1–175)
- The existing `STATUS_OPTIONS` constant (around line 48)
- The existing `displayCompany` function (around line 170)

- [ ] **Step 2: Add `STATUS_PIPELINE` constant**

After the existing `STATUS_OPTIONS` constant, add:

```typescript
const STATUS_PIPELINE = [
  { value: 'applied',      label: 'Applied',      activeClass: 'bg-blue-500/20 text-blue-600 border border-blue-500/40' },
  { value: 'interviewing', label: 'Interviewing',  activeClass: 'bg-amber-500/20 text-amber-600 border border-amber-500/40' },
  { value: 'offer',        label: 'Offer',         activeClass: 'bg-green-500/20 text-green-600 border border-green-500/40' },
  { value: 'rejected',     label: 'Rejected',      activeClass: 'bg-red-500/20 text-red-600 border border-red-500/40' },
];
```

- [ ] **Step 3: Add `previewTab` state + reset effect**

After the existing `let selectedCl` line, add:

```typescript
let previewTab = $state<'letter' | 'analysis'>('letter');
```

After the existing `$effect` block (the one that loads data), add:

```typescript
$effect(() => {
  if (selectedCl) previewTab = 'letter';
});
```

- [ ] **Step 4: Add `displayRole`, `scoreColor`, `scoreBarColor`, `formatDateShort` helpers**

After the existing `displayCompany` function, add:

```typescript
function displayRole(entry: GeneratedCoverLetterEntry): string {
  const firstLine = entry.job_description.split('\n')[0].trim();
  if (!firstLine) return '';
  return firstLine.length > 50 ? firstLine.slice(0, 47) + '…' : firstLine;
}

function scoreColor(score: number): string {
  if (score >= 70) return 'bg-green-500/10 text-green-600';
  if (score >= 40) return 'bg-yellow-500/10 text-yellow-600';
  return 'bg-red-500/10 text-red-600';
}

function scoreBarColor(score: number): string {
  if (score >= 70) return 'bg-green-500';
  if (score >= 40) return 'bg-yellow-500';
  return 'bg-red-500';
}

function formatDateShort(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}
```

- [ ] **Step 5: Verify no TypeScript errors**

```bash
cd frontend && bun run check 2>&1 | head -30
```

Expected: 0 errors (or only pre-existing warnings).

- [ ] **Step 6: Commit**

```bash
rtk git add frontend/src/routes/history/+page.svelte
rtk git commit -m "feat: add history CL helpers and previewTab state"
```

---

## Chunk 2: Card Redesign

### Task 2: Replace CL card with inline status pipeline + match bar

**Files:**
- Modify: `frontend/src/routes/history/+page.svelte`

- [ ] **Step 1: Locate the card block**

Find the `{#each clItems as entry}` block inside the `{#if tab === 'cover-letter'}` section. It starts with a `<div class="flex items-start gap-2">` wrapping a checkbox and a `<button>`.

- [ ] **Step 2: Replace the entire card**

Find and replace this exact block (the full button + its wrapper div, for each entry):

```svelte
              <div class="flex items-start gap-2">
                <input
                  type="checkbox"
                  class="mt-3 rounded"
                  checked={selectedClIds.has(entry.id)}
                  onchange={() => {
                    const s = new Set(selectedClIds);
                    if (s.has(entry.id)) s.delete(entry.id); else s.add(entry.id);
                    selectedClIds = s;
                  }}
                />
                <button
                  onclick={() => selectedCl = entry}
                  class="flex-1 text-left border rounded-lg p-3 transition-colors hover:bg-accent
                    {selectedCl?.id === entry.id ? 'border-primary bg-accent' : 'bg-card'}"
                >
                  <div class="flex items-center justify-between gap-2">
                    <span class="text-sm font-medium truncate">{displayCompany(entry)}</span>
                    <div class="flex items-center gap-1.5 shrink-0">
                      {#if entry.match_score !== null}
                        <span class="text-xs px-1.5 py-0.5 rounded font-medium
                          {entry.match_score >= 70 ? 'bg-green-500/10 text-green-600'
                           : entry.match_score >= 40 ? 'bg-yellow-500/10 text-yellow-600'
                           : 'bg-red-500/10 text-red-600'}">{entry.match_score}%</span>
                      {/if}
                      {#if entry.tone && entry.tone !== 'professional'}
                        <span class="text-xs bg-muted border border-border rounded px-1.5 py-0.5 capitalize">{entry.tone}</span>
                      {/if}
                      {#if entry.profile_color && entry.profile_icon}
                        <span class="flex items-center gap-1 text-xs text-muted-foreground">
                          <span class="w-2 h-2 rounded-full" style="background:{entry.profile_color}"></span>
                          {entry.profile_icon}
                        </span>
                      {/if}
                    </div>
                  </div>
                  <div class="text-xs text-muted-foreground mt-0.5">{formatDate(entry.created_at)}</div>
                  <!-- Status dropdown -->
                  <div class="mt-2 flex items-center gap-2" role="presentation" onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.stopPropagation()}>
                    <select
                      class="text-xs bg-background border border-border rounded px-2 py-1"
                      value={entry.application_status ?? ''}
                      onchange={(e) => handleClStatusChange(entry.id, (e.target as HTMLSelectElement).value || null)}
                    >
                      {#each STATUS_OPTIONS as opt}
                        <option value={opt.value ?? ''} disabled={!opt.value && !!entry.application_id}>{opt.label}</option>
                      {/each}
                    </select>
                    {#if entry.application_id}
                      <a href="/tracker" class="text-[10px] text-primary hover:underline" title="View in Tracker">📌 Tracked</a>
                    {/if}
                  </div>
                </button>
              </div>
```

Replace with this new block. **Note:** inactive status pills use `<span role="button" tabindex="0">` to avoid nesting `<button>` inside `<button>` (invalid HTML):

```svelte
              <div class="flex items-start gap-2">
                <input
                  type="checkbox"
                  class="mt-3 rounded"
                  checked={selectedClIds.has(entry.id)}
                  onchange={() => {
                    const s = new Set(selectedClIds);
                    if (s.has(entry.id)) s.delete(entry.id); else s.add(entry.id);
                    selectedClIds = s;
                  }}
                />
                <button
                  onclick={() => selectedCl = entry}
                  class="flex-1 text-left border rounded-lg p-3 transition-colors hover:bg-accent
                    {selectedCl?.id === entry.id ? 'border-primary bg-accent' : 'bg-card'}"
                >
                  <!-- Row 1: company + badges -->
                  <div class="flex items-center justify-between gap-2">
                    <span class="text-sm font-semibold truncate">{displayCompany(entry)}</span>
                    <div class="flex items-center gap-1.5 shrink-0">
                      {#if entry.match_score !== null}
                        <span class="text-xs px-1.5 py-0.5 rounded font-medium {scoreColor(entry.match_score)}">{entry.match_score}%</span>
                      {/if}
                      {#if entry.tone && entry.tone !== 'professional'}
                        <span class="text-xs bg-muted border border-border rounded px-1.5 py-0.5 capitalize">{entry.tone}</span>
                      {/if}
                      {#if entry.profile_color && entry.profile_icon}
                        <span class="flex items-center gap-1 text-xs text-muted-foreground">
                          <span class="w-2 h-2 rounded-full" style="background:{entry.profile_color}"></span>
                          {entry.profile_icon}
                        </span>
                      {/if}
                    </div>
                  </div>

                  <!-- Row 2: role snippet + date -->
                  <div class="flex items-center justify-between mt-0.5 gap-2">
                    {#if displayRole(entry)}
                      <span class="text-xs text-muted-foreground truncate flex-1">{displayRole(entry)}</span>
                    {/if}
                    <span class="text-xs text-muted-foreground shrink-0 ml-auto">{formatDateShort(entry.created_at)}</span>
                  </div>

                  <!-- Row 3: match score bar -->
                  {#if entry.match_score !== null}
                    <div class="mt-2 bg-muted rounded-full h-1 overflow-hidden">
                      <div class="h-1 rounded-full {scoreBarColor(entry.match_score)}" style="width:{entry.match_score}%"></div>
                    </div>
                  {/if}

                  <!-- Row 4: status pipeline + tracked badge -->
                  <!-- Uses span[role=button] to avoid nesting <button> inside <button> (invalid HTML) -->
                  <div
                    class="mt-2 flex items-center gap-1 flex-wrap"
                    role="presentation"
                    onclick={(e) => e.stopPropagation()}
                    onkeydown={(e) => e.stopPropagation()}
                  >
                    {#each STATUS_PIPELINE as s}
                      {#if entry.application_status === s.value}
                        <span class="text-xs px-2 py-0.5 rounded-full font-medium {s.activeClass}">{s.label}</span>
                      {:else}
                        <span
                          role="button"
                          tabindex="0"
                          class="text-xs px-2 py-0.5 rounded-full border border-border text-muted-foreground hover:bg-accent transition-colors cursor-pointer"
                          onclick={() => handleClStatusChange(entry.id, s.value)}
                          onkeydown={(e) => e.key === 'Enter' && handleClStatusChange(entry.id, s.value)}
                        >{s.label}</span>
                      {/if}
                    {/each}
                    {#if entry.application_id}
                      <a href="/tracker" class="text-[10px] text-primary hover:underline ml-1" title="View in Tracker">📌 Tracked →</a>
                    {/if}
                  </div>
                </button>
              </div>
```

- [ ] **Step 3: Verify the page renders**

Start or check the dev server:
```bash
cd frontend && bun dev
```

Navigate to `http://localhost:5173/history` → Cover Letters tab. Expected:
- Each card shows company name + match score badge + tone badge (if non-professional)
- Match score progress bar appears below role snippet
- 4 pill buttons at bottom (Applied, Interviewing, Offer, Rejected)
- Active status pill is colored, inactive are ghost

- [ ] **Step 4: Verify no TypeScript/Svelte warnings**

```bash
cd frontend && bun run check 2>&1 | head -30
```

- [ ] **Step 5: Commit**

```bash
rtk git add frontend/src/routes/history/+page.svelte
rtk git commit -m "feat: redesign CL history card with inline status pipeline and match bar"
```

---

## Chunk 3: Preview Pane

### Task 3: Two-row header + tabs + fit analysis

**Files:**
- Modify: `frontend/src/routes/history/+page.svelte`

- [ ] **Step 1: Locate the preview pane block**

Find the `{#if selectedCl}` block inside the cover letter grid. It currently contains:
```svelte
<div class="border rounded-lg overflow-hidden bg-white dark:bg-zinc-950/40 ...">
  <div class="flex items-center justify-between gap-2 p-3 border-b bg-muted/30">
    ...header...
  </div>
  <div class="overflow-auto max-h-[70vh]">
    <CoverLetterPreview text={selectedCl.cover_letter_text} />
  </div>
</div>
```

- [ ] **Step 2: Replace the entire preview pane**

Replace the entire `<div class="border rounded-lg overflow-hidden bg-white dark:bg-zinc-950/40 ...">` block with:

```svelte
<div class="border rounded-lg overflow-hidden bg-white dark:bg-zinc-950/40 print:bg-white shadow-sm transition-colors">
  <!-- Row 1: identity + actions -->
  <div class="flex items-center justify-between gap-2 p-3 border-b bg-muted/30">
    <div class="min-w-0 flex-1">
      <span class="text-sm font-semibold">{displayCompany(selectedCl)}</span>
      {#if displayRole(selectedCl)}
        <span class="text-xs text-muted-foreground ml-2 truncate">{displayRole(selectedCl)}</span>
      {/if}
    </div>
    <div class="flex gap-2 shrink-0">
      <Button variant="outline" size="sm" onclick={handleCopyCl}>Copy</Button>
      <Button variant="outline" size="sm" onclick={handlePrint}>Print</Button>
      <Button variant="destructive" size="sm" onclick={() => selectedCl && handleDeleteCl(selectedCl.id)}>Delete</Button>
    </div>
  </div>

  <!-- Row 2: metadata strip -->
  <div class="flex items-center gap-2 px-3 py-1.5 bg-muted/10 border-b text-xs flex-wrap">
    {#if selectedCl.match_score !== null}
      <span class="px-1.5 py-0.5 rounded font-medium {scoreColor(selectedCl.match_score)}">{selectedCl.match_score}% match</span>
    {/if}
    {#if selectedCl.tone && selectedCl.tone !== 'professional'}
      <span class="bg-muted border border-border rounded px-1.5 py-0.5 capitalize">{selectedCl.tone}</span>
    {/if}
    {#if selectedCl.application_status}
      {@const sp = STATUS_PIPELINE.find(p => p.value === selectedCl.application_status)}
      {#if sp}
        <span class="px-2 py-0.5 rounded-full font-medium {sp.activeClass}">● {sp.label}</span>
      {/if}
    {/if}
    {#if selectedCl.application_id}
      <a href="/tracker" class="text-primary hover:underline">📌 Tracker →</a>
    {/if}
    <span class="text-muted-foreground ml-auto">{formatDate(selectedCl.created_at)}</span>
  </div>

  <!-- Tab bar (only when fit_analysis is available) -->
  {#if selectedCl.fit_analysis}
    <div class="flex border-b">
      <button
        class="px-4 py-2 text-sm font-medium transition-colors
          {previewTab === 'letter' ? 'border-b-2 border-primary text-foreground' : 'text-muted-foreground hover:text-foreground'}"
        onclick={() => (previewTab = 'letter')}
      >📄 Cover Letter</button>
      <button
        class="px-4 py-2 text-sm font-medium transition-colors
          {previewTab === 'analysis' ? 'border-b-2 border-primary text-foreground' : 'text-muted-foreground hover:text-foreground'}"
        onclick={() => (previewTab = 'analysis')}
      >📊 Fit Analysis</button>
    </div>
  {/if}

  <!-- Content -->
  <div class="overflow-auto max-h-[70vh]">
    {#if previewTab === 'letter' || !selectedCl.fit_analysis}
      <CoverLetterPreview text={selectedCl.cover_letter_text} />
    {:else}
      <!-- Fit Analysis -->
      <div class="p-4 space-y-4">

        <!-- Match score bar -->
        <div>
          <div class="flex justify-between text-xs mb-1.5">
            <span class="font-semibold text-muted-foreground uppercase tracking-wide">Match Score</span>
            <span class="font-bold {scoreColor(selectedCl.fit_analysis.match_score)}">{selectedCl.fit_analysis.match_score}%</span>
          </div>
          <div class="bg-muted rounded-full h-2 overflow-hidden">
            <div
              class="h-2 rounded-full {scoreBarColor(selectedCl.fit_analysis.match_score)}"
              style="width:{selectedCl.fit_analysis.match_score}%"
            ></div>
          </div>
        </div>

        <!-- Strengths / Gaps -->
        {#if selectedCl.fit_analysis.pros.length > 0 || selectedCl.fit_analysis.cons.length > 0}
          <div class="grid grid-cols-2 gap-3">
            {#if selectedCl.fit_analysis.pros.length > 0}
              <div class="border border-green-500/20 bg-green-500/5 rounded-lg p-3">
                <p class="text-xs font-semibold text-green-600 uppercase tracking-wide mb-2">✓ Strengths</p>
                <ul class="space-y-1">
                  {#each selectedCl.fit_analysis.pros as pro}
                    <li class="text-xs text-muted-foreground">· {pro}</li>
                  {/each}
                </ul>
              </div>
            {/if}
            {#if selectedCl.fit_analysis.cons.length > 0}
              <div class="border border-red-500/20 bg-red-500/5 rounded-lg p-3">
                <p class="text-xs font-semibold text-red-500 uppercase tracking-wide mb-2">✗ Gaps</p>
                <ul class="space-y-1">
                  {#each selectedCl.fit_analysis.cons as con}
                    <li class="text-xs text-muted-foreground">· {con}</li>
                  {/each}
                </ul>
              </div>
            {/if}
          </div>
        {/if}

        <!-- Missing Keywords -->
        {#if selectedCl.fit_analysis.missing_keywords.length > 0}
          <div>
            <p class="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Missing Keywords</p>
            <div class="flex flex-wrap gap-1.5">
              {#each selectedCl.fit_analysis.missing_keywords as kw}
                <span class="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded">{kw}</span>
              {/each}
            </div>
          </div>
        {/if}

        <!-- Red Flags -->
        {#if selectedCl.fit_analysis.red_flags.length > 0}
          <div class="border border-amber-500/20 bg-amber-500/5 rounded-lg p-3">
            <p class="text-xs font-semibold text-amber-600 uppercase tracking-wide mb-2">⚠ Red Flags</p>
            <ul class="space-y-1">
              {#each selectedCl.fit_analysis.red_flags as flag}
                <li class="text-xs text-muted-foreground">· {flag}</li>
              {/each}
            </ul>
          </div>
        {/if}

        <!-- Suggested Emphasis -->
        {#if selectedCl.fit_analysis.suggested_emphasis}
          <div>
            <p class="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1">Suggested Emphasis</p>
            <p class="text-xs text-muted-foreground">{selectedCl.fit_analysis.suggested_emphasis}</p>
          </div>
        {/if}

        <!-- Interview Questions -->
        {#if selectedCl.fit_analysis.interview_questions.length > 0}
          <div>
            <p class="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Interview Questions</p>
            <ol class="space-y-1.5 list-decimal list-inside">
              {#each selectedCl.fit_analysis.interview_questions as q}
                <li class="text-xs text-muted-foreground">{q}</li>
              {/each}
            </ol>
          </div>
        {/if}

      </div>
    {/if}
  </div>
</div>
```

- [ ] **Step 3: Verify the page renders**

Navigate to `http://localhost:5173/history` → Cover Letters tab → click a cover letter. Expected:
- Two-row header: company + role snippet on left, Copy/Print/Delete on right
- Metadata strip shows match score, tone (if not professional), status pill (if set), tracker link (if tracked), date
- If cover letter has fit analysis: tab bar appears with "📄 Cover Letter" and "📊 Fit Analysis"
- Clicking "📊 Fit Analysis" shows the analysis section
- Switching cards resets to "📄 Cover Letter" tab

- [ ] **Step 4: Verify no TypeScript/Svelte warnings**

```bash
cd frontend && bun run check 2>&1 | head -30
```

Expected: 0 errors.

- [ ] **Step 5: Commit**

```bash
rtk git add frontend/src/routes/history/+page.svelte
rtk git commit -m "feat: add two-row preview header and fit analysis tab to CL history"
```
