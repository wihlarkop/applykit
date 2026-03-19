# Smart Apply Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a `/smart-apply` page that chains job scraping → fit analysis → CV generation → cover letter generation → application tracker record into a single hybrid workflow.

**Architecture:** Frontend-only orchestration — no new backend endpoints. Two backend schemas get new optional fields (`application_id`, `extra_context` on `GenerateCvRequest`; `application_id` on `CoverLetterRequest`) so generated documents link to the application. The Application record is created first; its ID threads through subsequent generation calls. The tracker reads `?new=<id>` on load to highlight the new entry.

**Tech Stack:** SvelteKit 5 (runes), FastAPI, SQLAlchemy, Pydantic v2, Tailwind CSS, shadcn/ui components, LiteLLM streaming (SSE)

---

## File Map

| Action | File | What changes |
|--------|------|-------------|
| Modify | `backend/app/schemas.py` | Add `application_id` + `extra_context` to `GenerateCvRequest`; add `application_id` to `CoverLetterRequest` |
| Modify | `backend/app/routes/generate.py` | Pass `application_id` to `GeneratedCV` + `GeneratedCoverLetter` DB writes; append `extra_context` to ATS prompt |
| Modify | `frontend/src/lib/types.ts` | Mirror backend schema additions |
| Modify | `frontend/src/routes/+layout.svelte` | Add Smart Apply nav item with Zap icon |
| Create | `frontend/src/routes/smart-apply/+page.svelte` | Full Smart Apply page |
| Modify | `frontend/src/routes/tracker/+page.svelte` | Read `?new=<id>` param; open detail panel for that application after load |

---

## Task 1: Backend schema additions

**Files:**
- Modify: `backend/app/schemas.py`

- [ ] Open `backend/app/schemas.py`. Find `GenerateCvRequest` (currently at ~line 85):

```python
class GenerateCvRequest(BaseModel):
    profile_id: int
    enhance: bool = True
    job_description: str | None = None
```

Replace with:

```python
class GenerateCvRequest(BaseModel):
    profile_id: int
    enhance: bool = True
    job_description: str | None = None
    application_id: int | None = None
    extra_context: str | None = None
```

- [ ] Find `CoverLetterRequest` (currently at ~line 105). It already has `match_score`, `fit_analysis_json`, etc. Add one field at the end:

```python
class CoverLetterRequest(BaseModel):
    profile_id: int
    job_description: str
    company_name: str | None = None
    extra_context: str = ""
    tone: Literal["professional", "enthusiastic", "concise", "creative"] = "professional"
    job_url: str | None = None
    fit_context: str | None = None
    match_score: int | None = None
    fit_analysis_json: str | None = None
    application_id: int | None = None   # ← new field
```

- [ ] Commit:

```bash
git add backend/app/schemas.py
git commit -m "feat: add application_id + extra_context to generation request schemas"
```

---

## Task 2: Wire new fields into backend routes

**Files:**
- Modify: `backend/app/routes/generate.py`

### 2a — `generate_cv`: wire `application_id` + `extra_context`

- [ ] Find the `generate_cv` function. Inside the `if req.enhance and provider and api_key:` block, find where the ATS user prompt is built:

```python
user_prompt = _format_profile_for_llm(profile_data)
if req.job_description:
    user_prompt += (
        f"\n\n---\nTARGET JOB DESCRIPTION:\n{req.job_description}"
    )
user_prompt += f"\n\n---\nORIGINAL DATA (use this schema for your JSON output):\n{profile_data.model_dump_json()}"
```

Add `extra_context` injection after the job description line and before the original data line:

```python
user_prompt = _format_profile_for_llm(profile_data)
if req.job_description:
    user_prompt += (
        f"\n\n---\nTARGET JOB DESCRIPTION:\n{req.job_description}"
    )
if req.extra_context and req.extra_context.strip():
    user_prompt += f"\n\nADDITIONAL CONTEXT FROM CANDIDATE: {req.extra_context.strip()}"
user_prompt += f"\n\n---\nORIGINAL DATA (use this schema for your JSON output):\n{profile_data.model_dump_json()}"
```

- [ ] Find where `GeneratedCV` is created (a few lines after the try/except block):

```python
entry = GeneratedCV(
    enhanced=int(enhanced),
    profile_snapshot=result_profile.model_dump_json(),
    profile_id=req.profile_id,
)
```

Add `application_id`:

```python
entry = GeneratedCV(
    enhanced=int(enhanced),
    profile_snapshot=result_profile.model_dump_json(),
    profile_id=req.profile_id,
    application_id=req.application_id,
)
```

### 2b — `generate_cover_letter`: wire `application_id`

- [ ] Find the `event_stream` inner function inside `generate_cover_letter`. Find where `GeneratedCoverLetter` is constructed (after `yield "data: [DONE]\n\n"`):

```python
entry = GeneratedCoverLetter(
    company_name=req.company_name,
    job_description=req.job_description,
    extra_context=req.extra_context or None,
    cover_letter_text=full_text,
    profile_id=req.profile_id,
    job_url=req.job_url,
    tone=req.tone or "professional",
    match_score=req.match_score,
    fit_analysis=req.fit_analysis_json,
)
```

Add `application_id`:

```python
entry = GeneratedCoverLetter(
    company_name=req.company_name,
    job_description=req.job_description,
    extra_context=req.extra_context or None,
    cover_letter_text=full_text,
    profile_id=req.profile_id,
    job_url=req.job_url,
    tone=req.tone or "professional",
    match_score=req.match_score,
    fit_analysis=req.fit_analysis_json,
    application_id=req.application_id,
)
```

- [ ] Commit:

```bash
git add backend/app/routes/generate.py
git commit -m "feat: wire application_id and extra_context through generation routes"
```

---

## Task 3: Frontend type additions

**Files:**
- Modify: `frontend/src/lib/types.ts`

- [ ] Find `GenerateCvRequest` interface and add the two new optional fields:

```typescript
export interface GenerateCvRequest {
  profile_id: number;
  enhance?: boolean;
  job_description?: string | null;
  application_id?: number | null;   // ← new
  extra_context?: string | null;    // ← new
}
```

- [ ] Find `CoverLetterRequest` interface and add `application_id`:

```typescript
export interface CoverLetterRequest {
  profile_id: number;
  job_description: string;
  company_name?: string | null;
  extra_context?: string;
  tone?: Tone;
  job_url?: string | null;
  fit_context?: string | null;
  match_score?: number | null;
  fit_analysis_json?: string | null;
  application_id?: number | null;   // ← new
}
```

- [ ] Commit:

```bash
git add frontend/src/lib/types.ts
git commit -m "feat: add application_id + extra_context to frontend generation types"
```

---

## Task 4: Add Smart Apply nav item

**Files:**
- Modify: `frontend/src/routes/+layout.svelte`

- [ ] In the `<script>` block, the layout currently has no imports from lucide. Add the import at the top of the script section (or if there are already lucide imports, add to that line). The layout script block starts at line 1. Add:

```svelte
<script lang="ts">
  import { Zap } from '@lucide/svelte';
  import { page } from '$app/state';
  ...rest of existing imports...
```

- [ ] In the `<nav>` block, find the line with the second `<span>` separator (before History and Tracker) and add Smart Apply after the first separator group:

Current nav structure:
```svelte
<a href="/" class={navClass('/')}>Dashboard</a>
<span class="w-px h-4 bg-border mx-2 shrink-0"></span>
<a href="/cover-letter" class={navClass('/cover-letter')}>Cover Letter</a>
<a href="/generate" class={navClass('/generate')}>Generate CV</a>
<span class="w-px h-4 bg-border mx-2 shrink-0"></span>
<a href="/history" class={navClass('/history')}>History</a>
<a href="/tracker" class={navClass('/tracker')}>Tracker</a>
```

Update to:
```svelte
<a href="/" class={navClass('/')}>Dashboard</a>
<span class="w-px h-4 bg-border mx-2 shrink-0"></span>
<a href="/cover-letter" class={navClass('/cover-letter')}>Cover Letter</a>
<a href="/generate" class={navClass('/generate')}>Generate CV</a>
<a href="/smart-apply" class="{navClass('/smart-apply')} flex items-center gap-1.5">
  <Zap class="w-3.5 h-3.5" />
  Smart Apply
</a>
<span class="w-px h-4 bg-border mx-2 shrink-0"></span>
<a href="/history" class={navClass('/history')}>History</a>
<a href="/tracker" class={navClass('/tracker')}>Tracker</a>
```

- [ ] Commit:

```bash
git add frontend/src/routes/+layout.svelte
git commit -m "feat: add Smart Apply nav item"
```

---

## Task 5: Smart Apply page

**Files:**
- Create: `frontend/src/routes/smart-apply/+page.svelte`

- [ ] Create the file with the full implementation below. Read it carefully — the sections unlock progressively as steps complete.

```svelte
<script lang="ts">
  import { goto } from '$app/navigation';
  import { activeProfile } from '$lib/activeProfile.svelte';
  import {
    analyzeFit,
    createApplication,
    generateCoverLetterStream,
    generateCv,
    scrapeJob,
  } from '$lib/api';
  import { Button } from '$lib/components/ui/button';
  import { Card, CardContent } from '$lib/components/ui/card';
  import { Input } from '$lib/components/ui/input';
  import { Label } from '$lib/components/ui/label';
  import { toastState } from '$lib/toast.svelte';
  import type { FitAnalysisResponse } from '$lib/types';
  import {
    AlertTriangle,
    CheckCircle,
    ChevronDown,
    Loader2,
    Zap,
  } from '@lucide/svelte';

  // ---------------------------------------------------------------------------
  // Section 1 — Job input
  // ---------------------------------------------------------------------------
  let inputMode = $state<'url' | 'paste'>('url');
  let jobUrl = $state('');
  let jobText = $state('');
  let analysisLoading = $state(false);

  // ---------------------------------------------------------------------------
  // Section 2 — Analysis results
  // ---------------------------------------------------------------------------
  let scrapeResult = $state<{ job_description: string; company_name: string | null } | null>(null);
  let fitResult = $state<FitAnalysisResponse | null>(null);
  let analysisError = $state('');

  // ---------------------------------------------------------------------------
  // Section 3 — Job details (editable)
  // ---------------------------------------------------------------------------
  let companyName = $state('');
  let roleTitle = $state('');

  // ---------------------------------------------------------------------------
  // Section 4 — Generate options
  // ---------------------------------------------------------------------------
  let generateCvEnabled = $state(true);
  let cvEnhance = $state(true);
  let cvContext = $state('');
  let cvOptionsOpen = $state(false);

  let generateClEnabled = $state(true);
  let clTone = $state<'professional' | 'enthusiastic' | 'concise' | 'creative'>('professional');
  let clContext = $state('');
  let clOptionsOpen = $state(false);

  const TONES = [
    { value: 'professional' as const, label: 'Professional', desc: 'Formal & polished' },
    { value: 'enthusiastic' as const, label: 'Enthusiastic', desc: 'Energetic & passionate' },
    { value: 'concise' as const, label: 'Concise', desc: 'Short & direct' },
    { value: 'creative' as const, label: 'Creative', desc: 'Distinctive & memorable' },
  ];

  // ---------------------------------------------------------------------------
  // Action
  // ---------------------------------------------------------------------------
  let generating = $state(false);
  let generationStep = $state('');

  // Derived visibility
  const analysisReady = $derived(!!scrapeResult && !!fitResult);
  const canGenerate = $derived(analysisReady && (generateCvEnabled || generateClEnabled));

  // ---------------------------------------------------------------------------
  // Helpers from cover-letter page
  // ---------------------------------------------------------------------------
  function extractFromTitleLine(raw: string): { company: string; role: string } {
    const titleLine = raw.match(/^Title:\s*(.+)$/m);
    if (!titleLine) return { company: '', role: '' };
    const full = titleLine[1].trim();
    const atMatch = full.match(/^(.+?)\s+at\s+([^|]+)/i);
    if (atMatch) return { role: atMatch[1].trim(), company: atMatch[2].trim() };
    const dashMatch = full.match(/^(.+?)\s*[-–]\s*(.+?)(?:\s*\|.*)?$/);
    if (dashMatch) return { role: dashMatch[1].trim(), company: dashMatch[2].trim() };
    return { company: '', role: full.replace(/\|.*$/, '').trim() };
  }

  // ---------------------------------------------------------------------------
  // Step 1: Analyze
  // ---------------------------------------------------------------------------
  async function analyze() {
    const ap = activeProfile.current;
    if (!ap) { toastState.error('Select a profile first.'); return; }

    const rawText = inputMode === 'url' ? '' : jobText.trim();
    const url = inputMode === 'url' ? jobUrl.trim() : '';
    if (!url && !rawText) { toastState.error('Enter a job URL or paste a job description.'); return; }

    analysisLoading = true;
    analysisError = '';
    scrapeResult = null;
    fitResult = null;

    try {
      let jobDescription = rawText;
      let company: string | null = null;

      if (url) {
        const scraped = await scrapeJob(url);
        jobDescription = scraped.job_description;
        company = scraped.company_name;
      }

      // Extract role/company from text heuristic
      const extracted = extractFromTitleLine(jobDescription);
      companyName = company || extracted.company || '';
      roleTitle = extracted.role || '';

      scrapeResult = { job_description: jobDescription, company_name: company };

      // Run fit analysis
      const fit = await analyzeFit(ap.id, jobDescription);
      fitResult = fit;
    } catch (e: any) {
      analysisError = e.message ?? 'Analysis failed.';
      if (!scrapeResult) {
        toastState.error(`Scrape failed: ${e.message}. Try pasting the job description instead.`);
      } else {
        toastState.error(`Fit analysis failed: ${e.message}`);
        // Allow continuing without fit score
        fitResult = null;
      }
    } finally {
      analysisLoading = false;
    }
  }

  // ---------------------------------------------------------------------------
  // Step 2: Generate & Track
  // ---------------------------------------------------------------------------
  async function generateAndTrack() {
    const ap = activeProfile.current;
    if (!ap || !scrapeResult) return;
    generating = true;

    try {
      // 1. Create application record first
      generationStep = 'Creating application…';
      const app = await createApplication({
        company_name: companyName || 'Unknown',
        role_title: roleTitle,
        job_url: inputMode === 'url' ? jobUrl.trim() || null : null,
        profile_id: ap.id,
        status: 'applied',
      });

      // 2. Generate CV (if enabled)
      if (generateCvEnabled) {
        generationStep = 'Generating CV…';
        try {
          await generateCv({
            profile_id: ap.id,
            enhance: cvEnhance,
            job_description: scrapeResult.job_description,
            application_id: app.id,
            extra_context: cvContext || undefined,
          });
        } catch (e: any) {
          toastState.error(`CV generation failed: ${e.message}`);
        }
      }

      // 3. Generate cover letter (if enabled) — consume SSE stream silently
      if (generateClEnabled) {
        generationStep = 'Generating cover letter…';
        try {
          const res = await generateCoverLetterStream({
            profile_id: ap.id,
            job_description: scrapeResult.job_description,
            company_name: companyName || null,
            tone: clTone,
            extra_context: clContext || '',
            job_url: inputMode === 'url' ? jobUrl.trim() || null : null,
            match_score: fitResult?.match_score ?? null,
            fit_analysis_json: fitResult ? JSON.stringify(fitResult) : null,
            application_id: app.id,
          });
          // Consume stream to completion (backend writes DB row after [DONE])
          if (res.body) {
            const reader = res.body.getReader();
            while (true) {
              const { done } = await reader.read();
              if (done) break;
            }
          }
        } catch (e: any) {
          toastState.error(`Cover letter generation failed: ${e.message}`);
        }
      }

      generationStep = 'Done!';
      await goto(`/tracker?new=${app.id}`);
    } catch (e: any) {
      toastState.error(`Failed: ${e.message}`);
    } finally {
      generating = false;
      generationStep = '';
    }
  }

  // Score ring helper (same as cover-letter page)
  function ringOffset(score: number) {
    const circumference = 2 * Math.PI * 20;
    return circumference - (score / 100) * circumference;
  }

  function scoreColor(score: number) {
    if (score >= 70) return 'text-green-500';
    if (score >= 40) return 'text-amber-500';
    return 'text-red-500';
  }

  function ringStroke(score: number) {
    if (score >= 70) return 'stroke-green-500';
    if (score >= 40) return 'stroke-amber-500';
    return 'stroke-red-500';
  }
</script>

<div class="max-w-2xl mx-auto space-y-6 pb-20">
  <!-- Header -->
  <div class="space-y-1">
    <h1 class="text-2xl font-bold flex items-center gap-2">
      <Zap class="w-6 h-6 text-primary" />
      Smart Apply
    </h1>
    <p class="text-sm text-muted-foreground">Paste a job URL, tailor your documents, and track your application — in one flow.</p>
  </div>

  <!-- Section 1: Job Input -->
  <Card class="shadow-sm">
    <CardContent class="p-6 space-y-4">
      <!-- Mode toggle -->
      <div class="flex gap-1 p-1 rounded-lg bg-muted w-fit">
        <button
          onclick={() => inputMode = 'url'}
          class="px-4 py-1.5 rounded-md text-sm font-medium transition-all {inputMode === 'url' ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground'}"
        >
          Job URL
        </button>
        <button
          onclick={() => inputMode = 'paste'}
          class="px-4 py-1.5 rounded-md text-sm font-medium transition-all {inputMode === 'paste' ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground'}"
        >
          Paste Text
        </button>
      </div>

      {#if inputMode === 'url'}
        <div class="space-y-2">
          <Label for="job-url">Job posting URL</Label>
          <Input
            id="job-url"
            bind:value={jobUrl}
            placeholder="https://boards.greenhouse.io/company/jobs/123"
            class="h-11"
            onkeydown={(e) => { if (e.key === 'Enter') analyze(); }}
          />
        </div>
      {:else}
        <div class="space-y-2">
          <Label for="job-text">Job description</Label>
          <textarea
            id="job-text"
            bind:value={jobText}
            placeholder="Paste the full job description here…"
            rows={6}
            class="w-full rounded-xl border border-border bg-background px-4 py-3 text-sm placeholder:text-muted-foreground/50 resize-y focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          ></textarea>
        </div>
      {/if}

      <Button onclick={analyze} disabled={analysisLoading} class="w-full">
        {#if analysisLoading}
          <Loader2 class="w-4 h-4 mr-2 animate-spin" />
          Analyzing…
        {:else}
          <Zap class="w-4 h-4 mr-2" />
          Analyze Job
        {/if}
      </Button>
    </CardContent>
  </Card>

  <!-- Section 2 + 3: Results (visible after analysis) -->
  {#if scrapeResult}
    <!-- Fit analysis -->
    {#if fitResult}
      <Card class="shadow-sm border-border/50 animate-in fade-in slide-in-from-top-2 duration-300">
        <CardContent class="p-6 space-y-4">
          <div class="flex items-center gap-4">
            <!-- Score ring -->
            <div class="relative shrink-0 w-16 h-16">
              <svg class="w-16 h-16 -rotate-90" viewBox="0 0 48 48">
                <circle cx="24" cy="24" r="20" fill="none" stroke="currentColor" stroke-width="4" class="text-muted/30" />
                <circle
                  cx="24" cy="24" r="20" fill="none" stroke-width="4"
                  stroke-linecap="round"
                  class="{ringStroke(fitResult.match_score)} transition-all duration-700"
                  stroke-dasharray="{2 * Math.PI * 20}"
                  stroke-dashoffset="{ringOffset(fitResult.match_score)}"
                />
              </svg>
              <span class="absolute inset-0 flex items-center justify-center text-sm font-bold {scoreColor(fitResult.match_score)}">
                {fitResult.match_score}%
              </span>
            </div>
            <div>
              <p class="font-semibold text-sm">Profile Match</p>
              <p class="text-xs text-muted-foreground">
                {fitResult.match_score >= 70 ? 'Strong fit — good to apply.' : fitResult.match_score >= 40 ? 'Decent fit — tailor your documents.' : 'Weak fit — consider the gaps below.'}
              </p>
            </div>
          </div>

          <!-- Pros / Cons -->
          {#if fitResult.pros.length || fitResult.cons.length}
            <div class="grid grid-cols-2 gap-3">
              <div class="space-y-1.5">
                {#each fitResult.pros.slice(0, 3) as pro}
                  <div class="flex items-start gap-1.5 text-xs text-green-700 dark:text-green-400 bg-green-50 dark:bg-green-900/20 rounded-lg px-2.5 py-1.5">
                    <CheckCircle class="w-3.5 h-3.5 mt-0.5 shrink-0" />
                    {pro}
                  </div>
                {/each}
              </div>
              <div class="space-y-1.5">
                {#each fitResult.cons.slice(0, 3) as con}
                  <div class="flex items-start gap-1.5 text-xs text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 rounded-lg px-2.5 py-1.5">
                    <AlertTriangle class="w-3.5 h-3.5 mt-0.5 shrink-0" />
                    {con}
                  </div>
                {/each}
              </div>
            </div>
          {/if}

          <!-- Missing keywords -->
          {#if fitResult.missing_keywords.length}
            <div class="flex flex-wrap gap-1.5">
              {#each fitResult.missing_keywords.slice(0, 8) as kw}
                <span class="text-[11px] px-2 py-0.5 rounded-full bg-muted border border-border/60 text-muted-foreground">{kw}</span>
              {/each}
            </div>
          {/if}
        </CardContent>
      </Card>
    {:else if analysisError}
      <div class="flex items-center gap-2 text-sm text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 rounded-xl px-4 py-3 border border-amber-200 dark:border-amber-800">
        <AlertTriangle class="w-4 h-4 shrink-0" />
        Fit analysis unavailable — you can still generate documents.
      </div>
    {/if}

    <!-- Job details: editable -->
    <Card class="shadow-sm animate-in fade-in slide-in-from-top-2 duration-300">
      <CardContent class="p-6 space-y-4">
        <h2 class="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Job Details</h2>
        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-2">
            <Label for="company-name">Company</Label>
            <Input id="company-name" bind:value={companyName} placeholder="Company name" class="h-10" />
          </div>
          <div class="space-y-2">
            <Label for="role-title">Role</Label>
            <Input id="role-title" bind:value={roleTitle} placeholder="Job title" class="h-10" />
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- Section 4: Generate options -->
    <div class="space-y-3 animate-in fade-in slide-in-from-top-2 duration-300">
      <h2 class="text-sm font-semibold uppercase tracking-wider text-muted-foreground px-1">What to generate</h2>

      <!-- CV card -->
      <Card class="shadow-sm transition-all {generateCvEnabled ? 'border-primary/30 bg-primary/5' : 'opacity-60'}">
        <CardContent class="p-4 space-y-3">
          <div class="flex items-center justify-between">
            <label class="flex items-center gap-3 cursor-pointer">
              <input type="checkbox" bind:checked={generateCvEnabled} class="w-4 h-4 accent-primary rounded" />
              <span class="font-semibold text-sm">Generate CV</span>
            </label>
            {#if generateCvEnabled}
              <button
                onclick={() => cvOptionsOpen = !cvOptionsOpen}
                class="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors"
              >
                Options <ChevronDown class="w-3 h-3 transition-transform {cvOptionsOpen ? 'rotate-180' : ''}" />
              </button>
            {/if}
          </div>

          {#if generateCvEnabled && cvOptionsOpen}
            <div class="space-y-3 pt-1 border-t border-border/50 animate-in fade-in duration-150">
              <label class="flex items-center gap-2 cursor-pointer text-sm">
                <input type="checkbox" bind:checked={cvEnhance} class="w-4 h-4 accent-primary rounded" />
                ATS-enhance bullets and summary
              </label>
              <div class="space-y-1.5">
                <label class="text-xs font-medium text-muted-foreground">Extra context (optional)</label>
                <textarea
                  bind:value={cvContext}
                  placeholder="e.g. Highlight my leadership experience, focus on backend skills…"
                  rows={2}
                  class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground/50 resize-none focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                ></textarea>
              </div>
            </div>
          {/if}
        </CardContent>
      </Card>

      <!-- Cover letter card -->
      <Card class="shadow-sm transition-all {generateClEnabled ? 'border-primary/30 bg-primary/5' : 'opacity-60'}">
        <CardContent class="p-4 space-y-3">
          <div class="flex items-center justify-between">
            <label class="flex items-center gap-3 cursor-pointer">
              <input type="checkbox" bind:checked={generateClEnabled} class="w-4 h-4 accent-primary rounded" />
              <span class="font-semibold text-sm">Generate Cover Letter</span>
            </label>
            {#if generateClEnabled}
              <button
                onclick={() => clOptionsOpen = !clOptionsOpen}
                class="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors"
              >
                Options <ChevronDown class="w-3 h-3 transition-transform {clOptionsOpen ? 'rotate-180' : ''}" />
              </button>
            {/if}
          </div>

          {#if generateClEnabled && clOptionsOpen}
            <div class="space-y-3 pt-1 border-t border-border/50 animate-in fade-in duration-150">
              <!-- Tone -->
              <div class="space-y-1.5">
                <label class="text-xs font-medium text-muted-foreground">Tone</label>
                <div class="grid grid-cols-2 gap-2">
                  {#each TONES as t}
                    <button
                      onclick={() => clTone = t.value}
                      class="flex flex-col items-start px-3 py-2 rounded-lg border text-left transition-all text-sm
                             {clTone === t.value
                               ? 'bg-primary text-primary-foreground border-primary'
                               : 'bg-background border-border hover:border-primary/40'}"
                    >
                      <span class="font-semibold text-xs">{t.label}</span>
                      <span class="text-[10px] {clTone === t.value ? 'text-primary-foreground/70' : 'text-muted-foreground'}">{t.desc}</span>
                    </button>
                  {/each}
                </div>
              </div>
              <!-- Extra context -->
              <div class="space-y-1.5">
                <label class="text-xs font-medium text-muted-foreground">Extra context (optional)</label>
                <textarea
                  bind:value={clContext}
                  placeholder="e.g. Mention my open source contributions, I'm excited about their mission…"
                  rows={2}
                  class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground/50 resize-none focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                ></textarea>
              </div>
            </div>
          {/if}
        </CardContent>
      </Card>
    </div>

    <!-- Action button -->
    <Button
      onclick={generateAndTrack}
      disabled={generating || !canGenerate}
      size="lg"
      class="w-full h-12 text-base font-semibold"
    >
      {#if generating}
        <Loader2 class="w-5 h-5 mr-2 animate-spin" />
        {generationStep || 'Working…'}
      {:else}
        <Zap class="w-5 h-5 mr-2" />
        Generate & Track
      {/if}
    </Button>
  {/if}
</div>
```

- [ ] Commit:

```bash
git add frontend/src/routes/smart-apply/+page.svelte
git commit -m "feat: add Smart Apply page"
```

---

## Task 6: Tracker page — highlight new application

The tracker uses `selectedApp` to open the detail panel. After load, if `?new=<id>` is in the URL, find that application and select it.

**Files:**
- Modify: `frontend/src/routes/tracker/+page.svelte`

- [ ] In the tracker's `<script>` block, add the `page` import at the top (alongside existing imports):

```typescript
import { page } from '$app/state';
```

- [ ] Find the `load()` function. After `apps = res.items;` and before the `catch`, add the highlight logic:

```typescript
const res = await listApplications(filters);
apps = res.items;

// Highlight newly created application if redirected from Smart Apply
const newId = page.url.searchParams.get('new');
if (newId) {
  const target = apps.find(a => a.id === Number(newId));
  if (target) selectedApp = target;
}
```

- [ ] Commit:

```bash
git add frontend/src/routes/tracker/+page.svelte
git commit -m "feat: open detail panel for new application after Smart Apply redirect"
```

---

## Task 7: Final push

- [ ] Verify the app runs end-to-end:
  1. Navigate to `/smart-apply`
  2. Paste a job URL or text
  3. Click "Analyze Job" — fit analysis card should appear
  4. Toggle CV and/or Cover Letter, open Options to verify config panels work
  5. Click "Generate & Track" — watch progress steps, confirm redirect to `/tracker?new=<id>`
  6. Confirm the detail panel opens for the new application
  7. Confirm generated CV and cover letter appear in the detail panel's linked docs section

- [ ] Push:

```bash
git push
```
