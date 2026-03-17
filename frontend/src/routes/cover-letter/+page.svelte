<script lang="ts">
  import { activeProfile } from '$lib/activeProfile.svelte';
  import {
    analyzeFit,
    generateCoverLetterPdf,
    generateCoverLetterStream,
    getProfile,
    scrapeJob,
  } from '$lib/api';
  import CoverLetterPreview from '$lib/components/CoverLetterPreview.svelte';
  import { Button } from '$lib/components/ui/button';
  import { Card, CardContent } from '$lib/components/ui/card';
  import { Input } from '$lib/components/ui/input';
  import { Label } from '$lib/components/ui/label';
  import { Skeleton } from '$lib/components/ui/skeleton';
  import { Textarea } from '$lib/components/ui/textarea';
  import { toastState } from '$lib/toast.svelte';
  import type { FitAnalysisResponse, ProfileData, Tone } from '$lib/types';
  import { Check, Copy, Download, Link, Lock, Mail, Printer, Sparkles, UserRoundPen } from '@lucide/svelte';

  let { data } = $props();
  const isOnboarded = $derived(data.isOnboarded);

  // --- Form state ---
  let inputTab = $state<'paste' | 'url'>('paste');
  let jobUrl = $state('');
  let scraping = $state(false);
  let companyName = $state('');
  let jobDescription = $state('');
  let extraContext = $state('');
  let tone = $state<Tone>('professional');

  // --- Fit analysis state ---
  let analyzing = $state(false);
  let fitResult = $state<FitAnalysisResponse | null>(null);
  let showInterviewPrep = $state(false);
  let fitCollapsed = $state(false);

  // --- Generate state ---
  let coverLetterText = $state('');
  let loading = $state(false);
  let downloading = $state(false);
  let copied = $state(false);

  let activeProfileData: ProfileData | null = $state(null);
  let profileLoading = $state(true);

  const TONES: { value: Tone; label: string }[] = [
    { value: 'professional', label: 'Professional' },
    { value: 'enthusiastic', label: 'Enthusiastic' },
    { value: 'concise', label: 'Concise' },
    { value: 'creative', label: 'Creative' },
  ];

  const matchColor = $derived(
    fitResult === null
      ? ''
      : fitResult.match_score >= 70
        ? 'text-green-600 bg-green-500'
        : fitResult.match_score >= 40
          ? 'text-yellow-600 bg-yellow-500'
          : 'text-red-600 bg-red-500'
  );

  const isProfileEmpty = $derived(
    !profileLoading &&
    (!activeProfileData ||
      (activeProfileData.work_experience.length === 0 &&
        activeProfileData.skills.length === 0 &&
        activeProfileData.education.length === 0))
  );

  $effect(() => {
    const ap = activeProfile.current;
    activeProfileData = null;
    coverLetterText = '';
    profileLoading = true;
    if (!ap) { profileLoading = false; return; }
    getProfile(ap.id)
      .then((p) => { activeProfileData = p; })
      .catch(() => {})
      .finally(() => { profileLoading = false; });
  });

  // --- URL import ---
  async function handleImport() {
    if (!jobUrl.trim()) return;
    scraping = true;
    try {
      const res = await scrapeJob(jobUrl.trim());
      jobDescription = res.job_description;
      if (res.company_name) companyName = res.company_name;
      inputTab = 'paste';
      toastState.success('Job posting imported!');
    } catch (e: any) {
      toastState.error(e.message);
    } finally {
      scraping = false;
    }
  }

  // --- Fit analysis ---
  async function handleAnalyzeFit() {
    const ap = activeProfile.current;
    if (!ap || !jobDescription.trim()) return;
    analyzing = true;
    fitResult = null;
    try {
      fitResult = await analyzeFit(ap.id, jobDescription);
      fitCollapsed = false;
    } catch (e: any) {
      toastState.error(e.message);
    } finally {
      analyzing = false;
    }
  }

  function acceptSuggestedEmphasis() {
    if (fitResult) extraContext = fitResult.suggested_emphasis;
  }

  // --- Streaming generation ---
  async function handleGenerate() {
    const ap = activeProfile.current;
    if (!ap || !jobDescription.trim()) return;
    loading = true;
    coverLetterText = '';
    fitCollapsed = true;
    try {
      const resp = await generateCoverLetterStream({
        profile_id: ap.id,
        job_description: jobDescription,
        extra_context: extraContext,
        company_name: companyName.trim() || null,
        tone,
        job_url: jobUrl.trim() || null,
        fit_context: fitResult?.suggested_emphasis || null,
        match_score: fitResult?.match_score ?? null,
        fit_analysis_json: fitResult ? JSON.stringify(fitResult) : null,
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: 'Generation failed' }));
        throw new Error(err.detail ?? 'Generation failed');
      }
      const reader = resp.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const payload = line.slice(6);
          if (payload === '[DONE]') { loading = false; break; }
          if (payload.startsWith('[ERROR]')) {
            toastState.error(payload.slice(8));
            loading = false;
            return;
          }
          coverLetterText += payload;
        }
      }
      toastState.success('Cover Letter Generated!');
    } catch (e: any) {
      toastState.error(`Generation failed: ${e.message}`);
    } finally {
      loading = false;
    }
  }

  async function handleCopy() {
    await navigator.clipboard.writeText(coverLetterText);
    copied = true;
    toastState.info('Copied to clipboard');
    setTimeout(() => (copied = false), 2000);
  }

  async function handleDownloadPdf() {
    if (!coverLetterText) return;
    downloading = true;
    try {
      const escaped = coverLetterText
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      const html = `<div style="font-family:sans-serif;font-size:13px;line-height:1.6;padding:40px;white-space:pre-wrap">${escaped}</div>`;
      const blob = await generateCoverLetterPdf({ html });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'cover-letter.pdf'; a.click();
      URL.revokeObjectURL(url);
      toastState.success('PDF Downloaded!');
    } catch (e: any) {
      toastState.error(`Download failed: ${e.message}`);
    } finally {
      downloading = false;
    }
  }
</script>

<div class="space-y-8 max-w-4xl pb-10 relative">
  <!-- Sticky Header -->
  <div class="sticky top-0 z-50 bg-background/80 backdrop-blur-md border-b border-border -mx-4 px-4 py-4 mb-8">
    <div class="flex items-start sm:items-center justify-between flex-col sm:flex-row gap-4 max-w-4xl mx-auto">
      <div>
        <h1 class="text-2xl font-bold flex items-center gap-2">
          <Mail class="w-6 h-6 text-primary" />
          Cover Letter Generator
        </h1>
        <p class="text-xs text-muted-foreground mt-0.5">Import a job URL or paste the description, analyze your fit, and generate a tailored letter.</p>
      </div>
    </div>
  </div>

  <div class="grid lg:grid-cols-[1fr_1.5fr] gap-8 items-start">
    <div class="sticky top-6 z-10 pt-2 pb-6 max-h-[calc(100vh-3rem)] overflow-y-auto">
      <Card class="shadow-sm">
        <CardContent class="p-6 space-y-5">

          <!-- Company name -->
          <div class="space-y-2">
            <Label for="company">Company Name <span class="text-muted-foreground text-xs">(optional)</span></Label>
            <Input id="company" bind:value={companyName} placeholder="e.g. Acme Corp" />
          </div>

          <!-- Job description tab switcher -->
          <div class="space-y-2">
            <Label class="font-semibold text-base">Job Description *</Label>
            <div class="flex gap-1 border-b border-border mb-2">
              <button
                class="px-3 py-1.5 text-sm font-medium transition-colors {inputTab === 'paste' ? 'border-b-2 border-primary text-foreground' : 'text-muted-foreground hover:text-foreground'}"
                onclick={() => (inputTab = 'paste')}
              >Paste Text</button>
              <button
                class="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium transition-colors {inputTab === 'url' ? 'border-b-2 border-primary text-foreground' : 'text-muted-foreground hover:text-foreground'}"
                onclick={() => (inputTab = 'url')}
              ><Link class="w-3.5 h-3.5" /> Import URL</button>
            </div>

            {#if inputTab === 'url'}
              <div class="flex gap-2">
                <Input bind:value={jobUrl} placeholder="https://boards.greenhouse.io/..." class="flex-1" />
                <Button onclick={handleImport} disabled={scraping || !jobUrl.trim()} size="sm">
                  {scraping ? 'Fetching…' : 'Import'}
                </Button>
              </div>
              <p class="text-xs text-muted-foreground">Supports Greenhouse, Lever, and most job boards. LinkedIn URLs may not work.</p>
            {:else}
              <Textarea
                id="jd"
                bind:value={jobDescription}
                placeholder="Paste the full job posting here..."
                rows={10}
                class="bg-background/50 resize-y max-h-[40vh]"
              />
            {/if}
          </div>

          <!-- Analyze Fit button -->
          {#if jobDescription.length > 0}
            <Button
              variant="outline"
              size="sm"
              class="w-full"
              onclick={handleAnalyzeFit}
              disabled={analyzing}
            >
              {#if analyzing}
                <Sparkles class="w-4 h-4 mr-2 animate-pulse" /> Analyzing…
              {:else}
                <Sparkles class="w-4 h-4 mr-2" /> Analyze Fit
              {/if}
            </Button>
          {/if}

          <!-- Fit analysis card -->
          {#if fitResult && !fitCollapsed}
            <div class="border border-border rounded-lg p-4 space-y-3 bg-muted/30 animate-in fade-in duration-300">
              <!-- Match score -->
              <div class="flex items-center gap-3">
                <span class="text-sm font-semibold">Match Score:</span>
                <div class="flex-1 bg-muted rounded-full h-2">
                  <div
                    class="h-2 rounded-full {matchColor.split(' ')[1]}"
                    style="width: {fitResult.match_score}%"
                  ></div>
                </div>
                <span class="text-sm font-bold {matchColor.split(' ')[0]}">{fitResult.match_score}%</span>
              </div>

              <!-- Pros / Cons -->
              <div class="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <p class="font-medium text-green-600 mb-1">✅ Strengths</p>
                  <ul class="space-y-0.5 text-muted-foreground">
                    {#each fitResult.pros as pro}<li>• {pro}</li>{/each}
                  </ul>
                </div>
                <div>
                  <p class="font-medium text-yellow-600 mb-1">⚠️ Gaps</p>
                  <ul class="space-y-0.5 text-muted-foreground">
                    {#each fitResult.cons as con}<li>• {con}</li>{/each}
                  </ul>
                </div>
              </div>

              <!-- Missing keywords -->
              {#if fitResult.missing_keywords.length > 0}
                <div class="text-xs">
                  <span class="font-medium text-muted-foreground">Missing keywords: </span>
                  {#each fitResult.missing_keywords as kw}
                    <span class="inline-block bg-muted border border-border rounded px-1.5 py-0.5 mr-1 mb-1">{kw}</span>
                  {/each}
                </div>
              {/if}

              <!-- Red flags -->
              {#each fitResult.red_flags as flag}
                <p class="text-xs text-red-600">🚨 {flag}</p>
              {/each}

              <!-- Suggested emphasis -->
              <div class="text-xs border-t border-border pt-3">
                <p class="font-medium mb-1">💡 Suggested emphasis:</p>
                <p class="text-muted-foreground italic">{fitResult.suggested_emphasis}</p>
                <button
                  onclick={acceptSuggestedEmphasis}
                  class="mt-2 text-primary underline text-xs hover:no-underline"
                >Accept suggestion →</button>
              </div>

              <!-- Interview prep (collapsible) -->
              <div class="border-t border-border pt-2">
                <button
                  class="flex items-center gap-2 text-xs font-medium w-full"
                  onclick={() => (showInterviewPrep = !showInterviewPrep)}
                >
                  🎤 Interview prep questions {showInterviewPrep ? '▲' : '▼'}
                </button>
                {#if showInterviewPrep}
                  <ul class="mt-2 space-y-1 text-xs text-muted-foreground">
                    {#each fitResult.interview_questions as q}<li>• {q}</li>{/each}
                  </ul>
                {/if}
              </div>

              <!-- Re-analyze -->
              <button
                onclick={handleAnalyzeFit}
                disabled={analyzing}
                class="text-xs text-muted-foreground underline hover:no-underline"
              >Re-analyze</button>
            </div>
          {/if}

          <!-- Extra context / emphasis -->
          <div class="space-y-2">
            <Label for="extra" class="font-semibold text-base">
              What to emphasize <span class="text-muted-foreground text-xs font-normal">(optional)</span>
            </Label>
            <Textarea
              id="extra"
              bind:value={extraContext}
              placeholder="Focus on my open source contributions..."
              rows={3}
              class="bg-background/50 resize-y max-h-[20vh]"
            />
          </div>

          <!-- Tone selector -->
          <div class="space-y-2">
            <Label class="font-semibold text-sm">Tone</Label>
            <div class="flex gap-1 flex-wrap">
              {#each TONES as t}
                <button
                  onclick={() => (tone = t.value)}
                  class="px-3 py-1.5 text-xs rounded-md border transition-colors
                    {tone === t.value
                      ? 'bg-primary text-primary-foreground border-primary'
                      : 'border-border text-muted-foreground hover:text-foreground hover:bg-accent'}"
                >{t.label}</button>
              {/each}
            </div>
          </div>

          {#if activeProfile.current}
            <div class="flex items-center gap-2 px-3 py-2 rounded-lg bg-muted/50 border text-sm">
              <span class="text-base leading-none">{activeProfile.current.icon}</span>
              <span class="font-medium">{activeProfile.current.label}</span>
              <span class="text-muted-foreground text-xs">— writing as this profile</span>
            </div>
          {/if}

          <Button
            onclick={handleGenerate}
            disabled={loading || !jobDescription.trim() || !isOnboarded || isProfileEmpty || profileLoading}
            class="w-full shadow-md"
            size="lg"
          >
            {#if !isOnboarded}
              <Lock class="w-4 h-4 mr-2" /> Locked
            {:else if loading}
              <Sparkles class="w-4 h-4 mr-2 animate-pulse" /> Generating Letter…
            {:else}
              <Sparkles class="w-4 h-4 mr-2" /> Write Cover Letter
            {/if}
          </Button>
        </CardContent>
      </Card>
    </div>

    <!-- Right panel: preview -->
    <div class="space-y-4">
      {#if !coverLetterText && !loading}
        {#if isProfileEmpty}
          <Card class="border-dashed border-2 border-yellow-400/60 bg-yellow-50/30 dark:bg-yellow-900/10 h-full min-h-125 flex items-center justify-center">
            <CardContent class="flex flex-col items-center justify-center p-8 text-center">
              <div class="w-16 h-16 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400 rounded-full flex items-center justify-center mb-4">
                <UserRoundPen class="w-8 h-8" />
              </div>
              <h3 class="text-lg font-bold mb-2">Profile is empty</h3>
              <p class="text-muted-foreground text-sm max-w-65 mb-5">
                Add your work experience, education, or skills to <strong>{activeProfile.current?.label ?? 'this profile'}</strong> before writing a cover letter.
              </p>
              <Button href="/profile" variant="default" size="sm">Fill in my profile</Button>
            </CardContent>
          </Card>
        {:else}
          <Card class="border-dashed border-2 bg-muted/30 h-full min-h-125 flex items-center justify-center">
            <CardContent class="flex flex-col items-center justify-center p-8 text-center">
              <div class="w-16 h-16 bg-primary/10 text-primary rounded-full flex items-center justify-center mb-4">
                <Mail class="w-8 h-8 opacity-50" />
              </div>
              <h3 class="text-lg font-bold mb-2">No letter generated yet</h3>
              <p class="text-muted-foreground text-sm max-w-62.5">
                Fill out the job description and click generate.
              </p>
            </CardContent>
          </Card>
        {/if}
      {/if}

      {#if loading}
        <div class="space-y-4">
          <div class="flex items-center gap-2 text-sm bg-primary/5 p-3 rounded-lg border border-primary/20 animate-pulse">
            <Sparkles class="w-4 h-4 text-primary" />
            <span class="text-primary font-medium">AI is crafting your letter...</span>
          </div>
          {#if coverLetterText}
            <Card class="shadow-lg border-primary/10">
              <CardContent class="p-0">
                <div class="overflow-hidden bg-white dark:bg-zinc-950/40 rounded-xl transition-colors">
                  <CoverLetterPreview text={coverLetterText} />
                </div>
              </CardContent>
            </Card>
          {:else}
            <Card class="shadow-lg border-primary/10 overflow-hidden">
              <CardContent class="p-8 space-y-6 bg-white dark:bg-zinc-950/40 min-h-125">
                {#each Array(4) as _}
                  <div class="space-y-2">
                    <Skeleton class="h-4 w-full" />
                    <Skeleton class="h-4 w-5/6" />
                  </div>
                {/each}
              </CardContent>
            </Card>
          {/if}
        </div>
      {/if}

      {#if coverLetterText && !loading}
        <div class="animate-in fade-in slide-in-from-right-4 duration-500 space-y-3">
          <div class="flex items-center justify-between px-1">
            <h2 class="font-semibold text-lg flex items-center gap-2">
              <Sparkles class="w-5 h-5 text-amber-500" />
              Generated Letter
            </h2>
            <div class="flex gap-2">
              <Button variant="outline" size="sm" onclick={handleCopy} class="shadow-sm">
                {#if copied}<Check class="w-4 h-4 mr-1 text-green-500" /> Copied
                {:else}<Copy class="w-4 h-4 mr-1" /> Copy{/if}
              </Button>
              <Button variant="outline" size="sm" onclick={handleDownloadPdf} disabled={downloading} class="shadow-sm">
                <Download class="w-4 h-4 mr-1" /> PDF
              </Button>
              <Button variant="outline" size="sm" onclick={() => window.print()} class="shadow-sm hidden xl:flex">
                <Printer class="w-4 h-4 mr-1" /> Print
              </Button>
            </div>
          </div>
          <Card class="shadow-lg border-primary/10">
            <CardContent class="p-0">
              <div class="overflow-hidden bg-white dark:bg-zinc-950/40 print:bg-white rounded-xl print:border-0 transition-colors">
                <CoverLetterPreview text={coverLetterText} />
              </div>
            </CardContent>
          </Card>
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
  @media print {
    :global(header), :global(nav) { display: none !important; }
  }
</style>
