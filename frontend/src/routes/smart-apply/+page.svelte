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
  import FitAnalysisDisplay from '$lib/components/FitAnalysisDisplay.svelte';
  import { Input } from '$lib/components/ui/input';
  import { Label } from '$lib/components/ui/label';
  import { toastState } from '$lib/toast.svelte';
  import { consumeStream } from '$lib/stream';
  import { errorMessage } from '$lib/utils';
  import type { FitAnalysisResponse } from '$lib/types';
  import {
    AlertTriangle,
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
  const analysisReady = $derived(!!scrapeResult);
  const canGenerate = $derived(analysisReady && (generateCvEnabled || generateClEnabled));

  // ---------------------------------------------------------------------------
  // Helpers — extract role/company from job description text
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
  // Step 1: Analyze job
  // ---------------------------------------------------------------------------
  async function analyze() {
    const ap = activeProfile.current;
    if (!ap) { toastState.error('Select a profile first.'); return; }

    const rawText = inputMode === 'paste' ? jobText.trim() : '';
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

      const extracted = extractFromTitleLine(jobDescription);
      companyName = company || extracted.company || '';
      roleTitle = extracted.role || '';

      scrapeResult = { job_description: jobDescription, company_name: company };

      // Run fit analysis — non-fatal if it fails
      try {
        fitResult = await analyzeFit(ap.id, jobDescription);
      } catch (e: unknown) {
        analysisError = errorMessage(e) ?? 'Fit analysis failed.';
        toastState.error(`Fit analysis failed: ${errorMessage(e)}`);
      }
    } catch (e: unknown) {
      analysisError = errorMessage(e) ?? 'Analysis failed.';
      toastState.error(`Scrape failed: ${errorMessage(e)}. Try pasting the job description instead.`);
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
        } catch (e: unknown) {
          toastState.error(`CV generation failed: ${errorMessage(e)}`);
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
          await consumeStream(res);
        } catch (e: unknown) {
          toastState.error(`Cover letter generation failed: ${errorMessage(e)}`);
        }
      }

      generationStep = 'Done!';
      await goto(`/tracker?new=${app.id}`);
    } catch (e: unknown) {
      toastState.error(`Failed: ${errorMessage(e)}`);
    } finally {
      generating = false;
      generationStep = '';
    }
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

  <!-- Sections 2–5: shown after analysis -->
  {#if scrapeResult}
    <!-- Fit analysis card -->
    {#if fitResult}
      <FitAnalysisDisplay {fitResult} compact />
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
                <label for="cv-context" class="text-xs font-medium text-muted-foreground">Extra context (optional)</label>
                <textarea
                  id="cv-context"
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
                <span class="text-xs font-medium text-muted-foreground">Tone</span>
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
                <label for="cl-context" class="text-xs font-medium text-muted-foreground">Extra context (optional)</label>
                <textarea
                  id="cl-context"
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
