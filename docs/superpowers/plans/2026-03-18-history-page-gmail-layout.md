# History Page Gmail-Style Layout Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current full-width list + fixed right-side drawer with a permanent Gmail-style two-column layout: 320px scrollable sidebar on the left, full-height preview panel on the right.

**Architecture:** All changes are in a single file: `frontend/src/routes/history/+page.svelte`. No new files, no new components. The existing helpers (`STATUS_PIPELINE`, `scoreColor`, `scoreBarColor`, `displayRole`, `formatDateShort`, `displayCompany`, `previewTab`) are already in the file and just need to be wired into the new markup.

**Tech Stack:** SvelteKit Svelte 5 runes, Tailwind CSS 4

---

## Task 1: Replace flat list + drawer with Gmail two-column grid

**Files:**
- Modify: `frontend/src/routes/history/+page.svelte`

The current CL section (inside `{#if tab === 'cover-letter'}`) has:
- A filter bar
- A bulk-delete confirmation bar
- `<div class="space-y-2">` — the flat list
- A `{#if selectedCl}` block — the fixed drawer (with backdrop)

This task replaces both the flat list div and the drawer block with a two-column grid.

- [ ] **Step 1: Read the current file**

Open `frontend/src/routes/history/+page.svelte` and confirm:
- The flat list starts at `<div class="space-y-2">` (inside the cover-letter tab, after the filter bar)
- The drawer block starts at `<!-- Preview drawer: fixed right panel -->` with a `{#if selectedCl}` containing a `<div class="fixed inset-0 bg-black/30 ...">` backdrop

- [ ] **Step 2: Replace flat list + drawer with two-column grid**

Find and replace this exact block. The old block starts at the list comment and ends at the **first** `{/if}` after the drawer (line 620 in the current file). The two `{/if}` lines that follow (lines 621–622, which close the outer `{:else}` and `{#if clItems.length === 0}` blocks) must **not** be removed — they stay in place.

Start of block to replace:
```svelte
        <!-- List (always full width) -->
        <div class="space-y-2">
```

End of block to replace (inclusive — stop right here, do not remove what follows):
```svelte
        {/if}
      {/if}
    {/if}
```

The lines immediately after the replacement (which must remain) are:
```svelte
      {/if}
    {/if}
```

So the exact trailing anchor for the replacement is:

```
        {/if}    ← LAST line of the replaced block (closes drawer's {#if selectedCl})
      {/if}      ← KEEP — closes the {:else} of {#if clItems.length === 0}
    {/if}        ← KEEP — closes {#if tab === 'cover-letter'}
```

Use these three lines together as the find anchor to ensure precision.

Replace the entire section with:

```svelte
        <!-- Gmail two-column layout -->
        <div class="grid md:grid-cols-[320px_1fr] h-[calc(100vh-240px)] overflow-hidden border border-border rounded-lg">

          <!-- LEFT: Sidebar (card list) -->
          <div class="overflow-y-auto border-r border-border {selectedCl ? 'hidden md:block' : ''}">
            <div class="p-2 space-y-1.5">
              {#each clItems as entry}
                <div class="flex items-start gap-1.5">
                  <input
                    type="checkbox"
                    class="mt-3.5 rounded shrink-0"
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
                      {selectedCl?.id === entry.id ? 'border-primary bg-accent shadow-sm' : 'bg-card border-border'}"
                  >
                    <!-- Row 1: company + match score badge -->
                    <div class="flex items-center justify-between gap-2">
                      <span class="text-sm font-bold truncate">{displayCompany(entry)}</span>
                      <div class="flex items-center gap-1.5 shrink-0">
                        {#if entry.match_score !== null}
                          <span class="text-xs px-1.5 py-0.5 rounded font-semibold {scoreColor(entry.match_score)}">{entry.match_score}%</span>
                        {/if}
                        {#if entry.profile_color && entry.profile_icon}
                          <span class="flex items-center gap-1 text-xs text-muted-foreground">
                            <span class="w-2 h-2 rounded-full shrink-0" style="background:{entry.profile_color}"></span>
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
                      <div class="mt-1.5 bg-muted rounded-full h-1 overflow-hidden">
                        <div class="h-1 rounded-full {scoreBarColor(entry.match_score)}" style="width:{entry.match_score}%"></div>
                      </div>
                    {/if}

                    <!-- Row 4: all 4 status pills -->
                    <div
                      class="mt-2 flex items-center gap-1 flex-wrap"
                      role="presentation"
                      onclick={(e) => e.stopPropagation()}
                      onkeydown={(e) => e.stopPropagation()}
                    >
                      {#each STATUS_PIPELINE as s}
                        {#if entry.application_status === s.value}
                          <span class="text-xs px-2 py-0.5 rounded-full font-semibold {s.activeClass}">{s.label}</span>
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
                    </div>

                    <!-- Row 5: tracked badge (span+goto avoids <a> inside <button> HTML violation) -->
                    {#if entry.application_id}
                      <span
                        role="link"
                        tabindex="0"
                        class="mt-1.5 block text-[10px] text-primary hover:underline cursor-pointer"
                        onclick={(e) => { e.stopPropagation(); goto('/tracker'); }}
                        onkeydown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); goto('/tracker'); } }}
                        title="View in Tracker"
                      >📌 Tracked →</span>
                    {/if}
                  </button>
                </div>
              {/each}
            </div>
          </div>

          <!-- RIGHT: Preview panel -->
          <div class="flex flex-col overflow-hidden">
            {#if !selectedCl}
              <!-- Empty state -->
              <div class="flex-1 flex flex-col items-center justify-center gap-2 text-muted-foreground">
                <span class="text-4xl">📄</span>
                <p class="text-sm font-medium">Select a cover letter to preview</p>
                <p class="text-xs text-muted-foreground/70">Click any card on the left</p>
              </div>
            {:else}
              <!-- Gradient header with score ring -->
              <div class="shrink-0 border-b border-border" style="background:linear-gradient(135deg,#eef2ff,#f0fdf4)">
                <!-- Mobile back button row -->
                <div class="md:hidden px-3 pt-2">
                  <Button variant="ghost" size="sm" onclick={() => selectedCl = null}>← Back</Button>
                </div>
                <div class="flex gap-3 items-start p-4">
                  <!-- Score ring (only when match_score exists) -->
                  {#if selectedCl.match_score !== null}
                    {@const pct = selectedCl.match_score}
                    {@const deg = Math.round(pct * 3.6)}
                    {@const ringColor = pct >= 70 ? '#22c55e' : pct >= 40 ? '#f59e0b' : '#ef4444'}
                    <div
                      class="shrink-0 w-14 h-14 rounded-full flex items-center justify-center"
                      style="background:conic-gradient({ringColor} {deg}deg, #e2e8f0 0)"
                    >
                      <div class="w-10 h-10 rounded-full bg-white flex items-center justify-center">
                        <span class="text-xs font-bold" style="color:{ringColor}">{pct}%</span>
                      </div>
                    </div>
                  {/if}

                  <!-- Identity -->
                  <div class="flex-1 min-w-0">
                    <div class="text-base font-bold text-foreground truncate">{displayCompany(selectedCl)}</div>
                    {#if displayRole(selectedCl)}
                      <div class="text-xs text-muted-foreground mt-0.5 truncate">{displayRole(selectedCl)}</div>
                    {/if}
                    <div class="text-xs text-muted-foreground mt-0.5">{formatDate(selectedCl.created_at)}</div>
                    <div class="mt-2 flex items-center gap-2 flex-wrap">
                      {#if selectedCl.application_status}
                        {@const sp = STATUS_PIPELINE.find(p => p.value === selectedCl!.application_status)}
                        {#if sp}
                          <span class="text-xs px-2 py-0.5 rounded-full font-semibold {sp.activeClass}">● {sp.label}</span>
                        {/if}
                      {/if}
                      {#if selectedCl.application_id}
                        <a href="/tracker" class="text-xs text-primary hover:underline">📌 Tracker →</a>
                      {/if}
                    </div>
                  </div>

                  <!-- Action buttons -->
                  <div class="flex gap-1.5 shrink-0">
                    <Button variant="outline" size="sm" onclick={handleCopyCl}>Copy</Button>
                    <Button variant="outline" size="sm" onclick={handlePrint}>Print</Button>
                    <Button variant="destructive" size="sm" onclick={() => selectedCl && handleDeleteCl(selectedCl.id)}>Delete</Button>
                  </div>
                </div>
              </div>

              <!-- Tab bar (only when fit_analysis available) -->
              {#if selectedCl.fit_analysis}
                <div class="flex border-b border-border shrink-0 bg-background">
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

              <!-- Scrollable content -->
              <div class="overflow-y-auto flex-1">
                {#if previewTab === 'letter' || !selectedCl.fit_analysis}
                  <CoverLetterPreview text={selectedCl.cover_letter_text} />
                {:else}
                  <div class="p-4 space-y-4">
                    <!-- Match score bar -->
                    <div>
                      <div class="flex justify-between text-xs mb-1.5">
                        <span class="font-semibold text-muted-foreground uppercase tracking-wide">Match Score</span>
                        <span class="font-bold {scoreColor(selectedCl.fit_analysis.match_score)}">{selectedCl.fit_analysis.match_score}%</span>
                      </div>
                      <div class="bg-muted rounded-full h-2 overflow-hidden">
                        <div class="h-2 rounded-full {scoreBarColor(selectedCl.fit_analysis.match_score)}" style="width:{selectedCl.fit_analysis.match_score}%"></div>
                      </div>
                    </div>
                    <!-- Strengths / Gaps -->
                    {#if selectedCl.fit_analysis.pros.length > 0 || selectedCl.fit_analysis.cons.length > 0}
                      <div class="grid grid-cols-2 gap-3">
                        {#if selectedCl.fit_analysis.pros.length > 0}
                          <div class="border border-green-500/20 bg-green-500/5 rounded-lg p-3">
                            <p class="text-xs font-semibold text-green-600 uppercase tracking-wide mb-2">✓ Strengths</p>
                            <ul class="space-y-1">{#each selectedCl.fit_analysis.pros as pro}<li class="text-xs text-muted-foreground">· {pro}</li>{/each}</ul>
                          </div>
                        {/if}
                        {#if selectedCl.fit_analysis.cons.length > 0}
                          <div class="border border-red-500/20 bg-red-500/5 rounded-lg p-3">
                            <p class="text-xs font-semibold text-red-500 uppercase tracking-wide mb-2">✗ Gaps</p>
                            <ul class="space-y-1">{#each selectedCl.fit_analysis.cons as con}<li class="text-xs text-muted-foreground">· {con}</li>{/each}</ul>
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
                        <ul class="space-y-1">{#each selectedCl.fit_analysis.red_flags as flag}<li class="text-xs text-muted-foreground">· {flag}</li>{/each}</ul>
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
            {/if}
          </div>

        </div>
```

- [ ] **Step 3: Verify no TypeScript errors**

```bash
cd C:/Users/Edo/Project/applykit/frontend && bun run check 2>&1 | head -30
```

Expected: 0 errors in `history/+page.svelte`. The 6 pre-existing errors in `cover-letter` and `generate` pages are unrelated — those are acceptable.

- [ ] **Step 4: Verify in browser**

Navigate to `http://localhost:5173/history` → Cover Letters tab. Verify:
- Two columns always visible side by side
- Left sidebar shows cards with match%, role, date, match bar, 4 status pills, tracked badge
- Right side shows empty state (📄 icon + text) when nothing selected
- Clicking a card updates the right panel instantly with gradient header + score ring + tabs
- Clicking a status pill changes status without triggering card selection
- Scrolling the sidebar does not scroll the preview and vice versa

If the height feels off (too tall / too short), adjust `h-[calc(100vh-240px)]` — try `220px` or `260px` until both columns fit cleanly within the viewport.

- [ ] **Step 5: Commit**

```bash
cd C:/Users/Edo/Project/applykit && rtk git add frontend/src/routes/history/+page.svelte && rtk git commit -m "feat: gmail-style two-column layout for CL history with rich sidebar cards and score ring preview"
```
