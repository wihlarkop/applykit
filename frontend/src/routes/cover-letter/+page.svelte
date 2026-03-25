<script lang="ts">
  import { activeProfile } from '$lib/activeProfile.svelte';
  import {
      analyzeFit,
      generateCoverLetterPdf,
      generateCoverLetterStream,
      getProfile,
      scrapeAnalyze,
  } from '$lib/api';
  import CoverLetterPreview from '$lib/components/CoverLetterPreview.svelte';
  import FitAnalysisDisplay from '$lib/components/FitAnalysisDisplay.svelte';
  import { Button } from '$lib/components/ui/button';
  import { Card, CardContent } from '$lib/components/ui/card';
  import { Input } from '$lib/components/ui/input';
  import { Label } from '$lib/components/ui/label';
  import { Skeleton } from '$lib/components/ui/skeleton';
  import { Textarea } from '$lib/components/ui/textarea';
  import { consumeStream } from '$lib/stream';
  import { toastState } from '$lib/toast.svelte';
  import type { FitAnalysisResponse, ProfileData, Tone } from '$lib/types';
  import { errorMessage } from '$lib/utils';
  import {
      ArrowRight, Check, ChevronDown, Copy, Download, Link, Loader2, Lock, Mail,
      MapPin, Pencil, Sparkles, TrendingUp, UserRoundPen,
  } from '@lucide/svelte';

  let { data } = $props();
  const isOnboarded = $derived(data.isOnboarded);

  // --- Form state ---
  let inputTab = $state<'paste' | 'url'>('paste');
  let jobUrl = $state('');
  let scraping = $state(false);
  let isImported = $state(false);
  let importedDomain = $state('');
  let companyName = $state('');
  let roleTitle = $state('');
  let location = $state('');
  let salary = $state('');
  let jobDescription = $state('');
  let jobDescriptionExpanded = $state(false);
  let extraContext = $state('');
  let tone = $state<Tone>('professional');

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

  function cleanScrapedText(raw: string): string {
    return raw
      // Strip metadata lines from scrapers
      .replace(/^Title:.*\n?/m, '')
      .replace(/^URL Source:.*\n?/m, '')
      .replace(/^Published Time:.*\n?/m, '')
      .replace(/^Markdown Content:\s*\n?/m, '')
      // Remove nested image links and plain image tags
      .replace(/\[!\[.*?\]\(.*?\)\]\(.*?\)/g, '')
      .replace(/!\[.*?\]\(.*?\)/g, '')
      // [text](url) → text only
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      // Strip markdown headings (## Heading → Heading)
      .replace(/^#{1,6}\s+/gm, '')
      // Strip bold/italic (**text** → text, *text* → text, __text__ → text)
      .replace(/\*\*\*(.+?)\*\*\*/g, '$1')
      .replace(/\*\*(.+?)\*\*/g, '$1')
      .replace(/__(.+?)__/g, '$1')
      .replace(/\*(.+?)\*/g, '$1')
      .replace(/_(.+?)_/g, '$1')
      // Strip inline code `code` → code
      .replace(/`([^`]+)`/g, '$1')
      // Strip horizontal rules
      .replace(/^[-*_]{3,}\s*$/gm, '')
      // Strip blockquote markers
      .replace(/^>\s*/gm, '')
      // Collapse excessive blank lines
      .replace(/\n{3,}/g, '\n\n')
      .trim();
  }

  // --- Fit analysis state ---
  let analyzing = $state(false);
  let fitResult = $state<FitAnalysisResponse | null>(null);
  let showInterviewPrep = $state(false);

  // --- Generate state ---
  let coverLetterText = $state('');
  let loading = $state(false);
  let downloading = $state(false);
  let copied = $state(false);

  let activeProfileData: ProfileData | null = $state(null);
  let profileLoading = $state(true);
  let lastProfileId = $state<number | null>(null);

  const TONES: { value: Tone; label: string }[] = [
    { value: 'professional', label: 'Professional' },
    { value: 'enthusiastic', label: 'Enthusiastic' },
    { value: 'concise', label: 'Concise' },
    { value: 'creative', label: 'Creative' },
  ];

  // Workflow steps: 1 = Import Job, 2 = Analyze Fit, 3 = Generate
  const step1Done = $derived(!!jobDescription.trim());
  const step2Done = $derived(!!fitResult);

  const isProfileEmpty = $derived.by(() => {
    if (profileLoading || !activeProfileData) return true;
    return (
      activeProfileData.work_experience.length === 0 &&
      activeProfileData.skills.length === 0 &&
      activeProfileData.education.length === 0
    );
  });

  // Right panel state machine
  const rightPanel = $derived(
    loading ? 'generating' :
    coverLetterText ? 'letter' :
    analyzing ? 'analyzing' :
    fitResult ? 'fit' :
    isProfileEmpty ? 'empty-profile' :
    jobDescription.trim() ? 'ready' :
    'empty'
  );

  const step3Active = $derived(rightPanel === 'generating' || rightPanel === 'letter');

  $effect(() => {
    const ap = activeProfile.current;
    const newId = ap?.id ?? null;
    activeProfileData = null;
    profileLoading = true;
    // Only clear the generated letter when the user switches to a different profile
    if (newId !== lastProfileId) {
      if (coverLetterText) {
        toastState.error('Profile switched — your in-progress letter was cleared.');
      }
      coverLetterText = '';
      lastProfileId = newId;
    }
    if (!ap) { profileLoading = false; return; }
    getProfile(ap.id)
      .then((p) => { activeProfileData = p; })
      .catch((e: unknown) => { toastState.error(`Failed to load profile: ${errorMessage(e)}`); })
      .finally(() => { profileLoading = false; });
  });

  async function handleImport() {
    if (!jobUrl.trim()) return;
    scraping = true;
    try {
      const analyzed = await scrapeAnalyze({ url: jobUrl.trim() });
      jobDescription = cleanScrapedText(analyzed.job_description);
      companyName = analyzed.company_name || '';
      roleTitle = analyzed.role_title || '';
      location = analyzed.location || '';
      salary = analyzed.salary || '';
      isImported = true;
      try { importedDomain = new URL(jobUrl.trim()).hostname.replace('www.', ''); } catch { importedDomain = jobUrl; }
      toastState.success('Job posting imported!');
    } catch (e: unknown) {
      toastState.error(errorMessage(e));
    } finally {
      scraping = false;
    }
  }

  async function handleParsePasted() {
    if (!jobDescription.trim()) return;
    scraping = true;
    try {
      const analyzed = await scrapeAnalyze({ text: jobDescription });
      if (analyzed.company_name) companyName = analyzed.company_name;
      if (analyzed.role_title) roleTitle = analyzed.role_title;
      if (analyzed.location) location = analyzed.location;
      if (analyzed.salary) salary = analyzed.salary;
      toastState.success('Fields extracted from job description!');
    } catch (e: unknown) {
      toastState.error(`Failed to parse: ${errorMessage(e)}`);
    } finally {
      scraping = false;
    }
  }

  async function handleAnalyzeFit() {
    const ap = activeProfile.current;
    if (!ap || !jobDescription.trim()) return;
    analyzing = true;
    fitResult = null;
    try {
      fitResult = await analyzeFit(ap.id, jobDescription);
    } catch (e: unknown) {
      toastState.error(errorMessage(e));
    } finally {
      analyzing = false;
    }
  }

  function acceptSuggestedEmphasis() {
    if (fitResult) extraContext = fitResult.suggested_emphasis;
  }

  async function handleGenerate() {
    const ap = activeProfile.current;
    if (!ap || !jobDescription.trim()) return;
    loading = true;
    coverLetterText = '';
    try {
      const resp = await generateCoverLetterStream({
        profile_id: ap.id,
        job_description: jobDescription,
        extra_context: [roleTitle ? `Target role: ${roleTitle}` : '', extraContext].filter(Boolean).join('\n') || undefined,
        company_name: companyName.trim() || null,
        role_title: roleTitle.trim() || null,
        location: location.trim() || null,
        salary: salary.trim() || null,
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
      await consumeStream(resp, {
        onChunk: (text) => { coverLetterText += text; },
        onDone: () => { loading = false; toastState.success('Cover letter generated!'); },
        onError: (msg) => { toastState.error(msg); loading = false; },
      });
    } catch (e: unknown) {
      toastState.error(`Generation failed: ${errorMessage(e)}`);
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
      const blob = await generateCoverLetterPdf({ text: coverLetterText });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'cover-letter.pdf'; a.click();
      URL.revokeObjectURL(url);
      toastState.success('PDF downloaded!');
    } catch (e: unknown) {
      toastState.error(`Download failed: ${errorMessage(e)}`);
    } finally {
      downloading = false;
    }
  }
</script>

<div class="max-w-5xl pb-10">

  <!-- Workflow steps header -->
  <div class="flex items-center justify-between mb-6">
    <h1 class="text-xl font-bold flex items-center gap-2">
      <Mail class="w-5 h-5 text-primary" />
      Cover Letter
    </h1>
    <div class="flex items-center gap-1 text-xs">
      <!-- Step 1 -->
      <div class="flex items-center gap-1.5 px-2.5 py-1 rounded-full {step1Done ? 'text-green-600 dark:text-green-400' : 'text-muted-foreground'}">
        <span class="w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold shrink-0
          {step1Done ? 'bg-green-500/15 text-green-600 dark:text-green-400' : 'bg-muted text-muted-foreground'}">
          {#if step1Done}<Check class="w-2.5 h-2.5" />{:else}1{/if}
        </span>
        Import Job
      </div>
      <span class="text-muted-foreground/40">›</span>
      <!-- Step 2 -->
      <div class="flex items-center gap-1.5 px-2.5 py-1 rounded-full {step2Done ? 'text-green-600 dark:text-green-400' : step1Done ? 'text-foreground font-medium bg-accent' : 'text-muted-foreground'}">
        <span class="w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold shrink-0
          {step2Done ? 'bg-green-500/15 text-green-600 dark:text-green-400' : step1Done ? 'bg-primary/15 text-primary' : 'bg-muted text-muted-foreground'}">
          {#if step2Done}<Check class="w-2.5 h-2.5" />{:else}2{/if}
        </span>
        Analyze Fit
      </div>
      <span class="text-muted-foreground/40">›</span>
      <!-- Step 3 -->
      <div class="flex items-center gap-1.5 px-2.5 py-1 rounded-full {step3Active ? 'text-foreground font-medium bg-accent' : 'text-muted-foreground'}">
        <span class="w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold shrink-0
          {step3Active ? 'bg-primary/15 text-primary' : 'bg-muted text-muted-foreground'}">3</span>
        Generate
      </div>
    </div>
  </div>

  <div class="grid lg:grid-cols-[340px_1fr] gap-5 items-start">

    <!-- ── Left panel: form ── -->
    <div class="sticky top-6 space-y-4">

      <!-- Job details card -->
      <Card class="shadow-sm">
        <CardContent class="p-5 space-y-4">

          <!-- Job description input (URL or Paste) - FIRST -->
          <div class="space-y-1.5">
            <div class="flex items-center justify-between">
              <Label class="text-xs font-medium text-muted-foreground uppercase tracking-wide">Job Description *</Label>
              {#if isImported}
                <button
                  onclick={() => { isImported = false; inputTab = 'paste'; }}
                  class="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                >
                  <Pencil class="w-3 h-3" /> Edit
                </button>
              {/if}
            </div>

            {#if isImported}
              <!-- Collapsible job description -->
              <div class="rounded-lg border border-border bg-muted/20 overflow-hidden">
                <div class="flex items-center gap-2 px-3 py-2 border-b border-border bg-muted/40">
                  <Link class="w-3 h-3 text-muted-foreground shrink-0" />
                  <span class="text-xs text-muted-foreground truncate flex-1">{importedDomain}</span>
                  <span class="text-[10px] bg-green-500/10 text-green-600 dark:text-green-400 px-1.5 py-0.5 rounded font-semibold uppercase tracking-wide">Imported</span>
                </div>
                <button
                  onclick={() => jobDescriptionExpanded = !jobDescriptionExpanded}
                  class="flex items-center justify-between w-full px-3 py-2 text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  <span>{jobDescriptionExpanded ? 'Hide' : 'Show'} description</span>
                  <ChevronDown class="w-3.5 h-3.5 transition-transform {jobDescriptionExpanded ? 'rotate-180' : ''}" />
                </button>
                {#if jobDescriptionExpanded}
                  <div class="px-3 pb-3 max-h-[30vh] overflow-y-auto">
                    <p class="text-xs text-foreground/80 leading-relaxed whitespace-pre-wrap">{jobDescription}</p>
                  </div>
                {:else}
                  <div class="px-3 pb-3">
                    <p class="text-xs text-muted-foreground truncate">{jobDescription.slice(0, 150)}...</p>
                  </div>
                {/if}
              </div>
            {:else}
              <div class="flex gap-1 border-b border-border mb-2">
                <button
                  class="px-3 py-1.5 text-sm font-medium transition-colors cursor-pointer {inputTab === 'paste' ? 'border-b-2 border-primary text-foreground' : 'text-muted-foreground hover:text-foreground'}"
                  onclick={() => (inputTab = 'paste')}
                >Paste Text</button>
                <button
                  class="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium transition-colors cursor-pointer {inputTab === 'url' ? 'border-b-2 border-primary text-foreground' : 'text-muted-foreground hover:text-foreground'}"
                  onclick={() => (inputTab = 'url')}
                ><Link class="w-3.5 h-3.5" /> Import URL</button>
              </div>
              {#if inputTab === 'url'}
                <div class="flex gap-2">
                  <Input bind:value={jobUrl} placeholder="https://boards.greenhouse.io/..." class="flex-1 h-9" />
                  <Button onclick={handleImport} disabled={scraping || !jobUrl.trim()} size="sm" class="h-9">
                    {#if scraping}<Loader2 class="w-3.5 h-3.5 animate-spin mr-1" />{/if}
                    {scraping ? 'Fetching…' : 'Import'}
                  </Button>
                </div>
                <p class="text-xs text-muted-foreground">Supports Greenhouse, Lever, Ashby, and most job boards.</p>
              {:else}
                <Textarea
                  id="jd"
                  bind:value={jobDescription}
                  placeholder="Paste the full job posting here..."
                  rows={6}
                  class="bg-background/50 resize-y max-h-[35vh] text-sm"
                />
                <Button onclick={handleParsePasted} disabled={scraping || !jobDescription.trim()} size="sm" variant="outline" class="mt-2">
                  {#if scraping}<Loader2 class="w-3.5 h-3.5 animate-spin mr-1" />{/if}
                  Parse with AI
                </Button>
              {/if}
            {/if}
          </div>

          <!-- Company, Role, Location, Salary - SECOND -->
          <div class="grid grid-cols-2 gap-3">
            <!-- Company name -->
            <div class="space-y-1.5">
              <Label for="company" class="text-xs font-medium text-muted-foreground uppercase tracking-wide">Company</Label>
              <Input id="company" bind:value={companyName} placeholder="Acme Corp" class="h-9" />
            </div>
            <!-- Role / position -->
            <div class="space-y-1.5">
              <Label for="role" class="text-xs font-medium text-muted-foreground uppercase tracking-wide">Role</Label>
              <Input id="role" bind:value={roleTitle} placeholder="e.g. Backend Engineer" class="h-9" />
            </div>
            <!-- Location -->
            <div class="space-y-1.5">
              <Label for="location" class="text-xs font-medium text-muted-foreground uppercase tracking-wide">Location</Label>
              <div class="relative">
                <MapPin class="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
                <Input id="location" bind:value={location} placeholder="e.g. San Francisco, CA or Remote" class="h-9 pl-8" />
              </div>
            </div>
            <!-- Salary -->
            <div class="space-y-1.5">
              <Label for="salary" class="text-xs font-medium text-muted-foreground uppercase tracking-wide">Salary</Label>
              <Input id="salary" bind:value={salary} placeholder="e.g. $120,000 - $150,000" class="h-9" />
            </div>
          </div>

        </CardContent>
      </Card>

      <!-- Options card -->
      <Card class="shadow-sm">
        <CardContent class="p-5 space-y-4">

          <!-- Tone -->
          <div class="space-y-1.5">
            <Label class="text-xs font-medium text-muted-foreground uppercase tracking-wide">Tone</Label>
            <div class="grid grid-cols-2 gap-1.5">
              {#each TONES as t}
                <button
                  onclick={() => (tone = t.value)}
                  class="px-3 py-2 text-xs rounded-md border transition-colors cursor-pointer text-left font-medium
                    {tone === t.value
                      ? 'bg-primary/10 text-primary border-primary/30 dark:bg-primary/15'
                      : 'border-border text-muted-foreground hover:text-foreground hover:bg-accent'}"
                >{t.label}</button>
              {/each}
            </div>
          </div>

          <!-- Emphasis -->
          <div class="space-y-1.5">
            <Label for="extra" class="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              What to Emphasize <span class="text-muted-foreground/60 normal-case">(optional)</span>
            </Label>
            <Textarea
              id="extra"
              bind:value={extraContext}
              placeholder="Focus on my open source contributions..."
              rows={2}
              class="bg-background/50 resize-none text-sm"
            />
          </div>

          <!-- Active profile -->
          {#if activeProfile.current}
            <div class="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-muted/50 border">
              <div class="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center text-sm shrink-0 font-semibold">
                {activeProfile.current.icon}
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-xs font-semibold truncate">{activeProfile.current.label}</p>
                <p class="text-[10px] text-muted-foreground">writing as this profile</p>
              </div>
              <div class="w-2 h-2 rounded-full bg-green-500 shrink-0 ring-2 ring-green-500/20"></div>
            </div>
          {/if}

          <!-- Buttons -->
          <div class="space-y-2 pt-1">
            {#if jobDescription.trim()}
              <Button
                variant="outline"
                size="sm"
                class="w-full"
                onclick={handleAnalyzeFit}
                disabled={analyzing || loading}
              >
                {#if analyzing}
                  <Loader2 class="w-3.5 h-3.5 mr-2 animate-spin" /> Analyzing…
                {:else}
                  <TrendingUp class="w-3.5 h-3.5 mr-2" /> Analyze Fit
                {/if}
              </Button>
            {/if}
            <Button
              onclick={handleGenerate}
              disabled={loading || !jobDescription.trim() || !isOnboarded || isProfileEmpty || profileLoading}
              class="w-full"
              size="lg"
            >
              {#if !isOnboarded}
                <Lock class="w-4 h-4 mr-2" /> Locked
              {:else if loading}
                <Loader2 class="w-4 h-4 mr-2 animate-spin" /> Generating…
              {:else}
                <Sparkles class="w-4 h-4 mr-2" /> Generate Cover Letter
              {/if}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- ── Right panel: dynamic content ── -->
    <div class="min-h-[60vh]">

      <!-- Empty: no profile -->
      {#if rightPanel === 'empty-profile'}
        <Card class="border-dashed border-2 border-yellow-400/60 bg-yellow-50/30 dark:bg-yellow-900/10 h-full min-h-[60vh] flex items-center justify-center">
          <CardContent class="flex flex-col items-center justify-center p-10 text-center">
            <div class="w-14 h-14 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400 rounded-full flex items-center justify-center mb-4">
              <UserRoundPen class="w-7 h-7" />
            </div>
            <h3 class="text-base font-semibold mb-2">Profile is empty</h3>
            <p class="text-muted-foreground text-sm max-w-xs mb-5">
              Add work experience, education, or skills to <strong>{activeProfile.current?.label ?? 'this profile'}</strong> before generating.
            </p>
            <Button href="/profile" size="sm">Fill in my profile</Button>
          </CardContent>
        </Card>

      <!-- Empty: no job description yet -->
      {:else if rightPanel === 'empty'}
        <Card class="border-dashed border-2 bg-muted/20 h-full min-h-[60vh] flex items-center justify-center">
          <CardContent class="flex flex-col items-center justify-center p-10 text-center">
            <div class="w-14 h-14 bg-primary/10 text-primary rounded-full flex items-center justify-center mb-4">
              <Mail class="w-7 h-7 opacity-40" />
            </div>
            <h3 class="text-base font-semibold mb-1">No job added yet</h3>
            <p class="text-sm text-muted-foreground max-w-xs">
              Paste a job description or import from a URL to get started.
            </p>
          </CardContent>
        </Card>

      <!-- Ready: has job, no analysis -->
      {:else if rightPanel === 'ready'}
        <Card class="shadow-sm border-primary/20 min-h-[60vh] flex items-center justify-center">
          <CardContent class="flex flex-col items-center justify-center p-12 text-center">
            <div class="w-16 h-16 bg-primary/10 text-primary rounded-2xl flex items-center justify-center mb-5">
              <TrendingUp class="w-8 h-8" />
            </div>
            <h3 class="text-base font-bold mb-2">Job imported — ready to go</h3>
            <p class="text-sm text-muted-foreground max-w-xs mb-6 leading-relaxed">
              Run <strong class="font-semibold text-foreground">Analyze Fit</strong> first to see your match score and get a more personalized letter, or generate directly.
            </p>
            <div class="flex gap-2">
              <Button variant="outline" size="sm" onclick={handleAnalyzeFit} disabled={analyzing}>
                {#if analyzing}<Loader2 class="w-3.5 h-3.5 animate-spin" />{:else}<TrendingUp class="w-3.5 h-3.5" />{/if}
                Analyze Fit
              </Button>
              <Button size="sm" onclick={handleGenerate} disabled={loading || !isOnboarded}>
                <Sparkles class="w-3.5 h-3.5" /> Generate Now
              </Button>
            </div>
          </CardContent>
        </Card>

      <!-- Analyzing skeleton -->
      {:else if rightPanel === 'analyzing'}
        <Card class="shadow-sm">
          <CardContent class="p-6 space-y-5">
            <div class="flex items-center gap-2 text-sm text-primary animate-pulse">
              <Loader2 class="w-4 h-4 animate-spin" />
              <span class="font-medium">Analyzing your fit…</span>
            </div>
            <div class="flex items-center gap-4">
              <Skeleton class="w-20 h-20 rounded-full shrink-0" />
              <div class="flex-1 space-y-2">
                <Skeleton class="h-4 w-32" />
                <Skeleton class="h-2 w-full rounded-full" />
              </div>
            </div>
            {#each Array(3) as _}
              <div class="space-y-2">
                <Skeleton class="h-3 w-24" />
                <Skeleton class="h-3 w-full" />
                <Skeleton class="h-3 w-5/6" />
              </div>
            {/each}
          </CardContent>
        </Card>

      <!-- Fit analysis results -->
      {:else if rightPanel === 'fit' && fitResult}
        <div class="animate-in fade-in duration-300 space-y-4">
          <FitAnalysisDisplay
            {fitResult}
            {companyName}
            onReanalyze={handleAnalyzeFit}
            {analyzing}
            onAcceptEmphasis={acceptSuggestedEmphasis}
            bind:showInterviewPrep
          />

          <!-- Generate CTA banner -->
          <div class="flex items-center gap-3 p-4 rounded-xl bg-primary/8 dark:bg-primary/12 border border-primary/20">
            <div class="w-9 h-9 rounded-lg bg-primary flex items-center justify-center shrink-0 shadow-sm">
              <Sparkles class="w-4 h-4 text-white" />
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-semibold text-foreground">Ready to generate</p>
              <p class="text-xs text-muted-foreground">{fitResult.match_score}% match · {tone} tone{activeProfile.current ? ` · ${activeProfile.current.label}` : ''}</p>
            </div>
            <Button onclick={handleGenerate} disabled={loading || !isOnboarded} size="sm" class="shrink-0">
              Generate <ArrowRight class="w-3.5 h-3.5 ml-1" />
            </Button>
          </div>
        </div>

      <!-- Generating -->
      {:else if rightPanel === 'generating'}
        <div class="space-y-4">
          <div class="flex items-center gap-2 text-sm bg-primary/5 px-4 py-3 rounded-lg border border-primary/20 animate-pulse">
            <Loader2 class="w-4 h-4 text-primary animate-spin" />
            <span class="text-primary font-medium">AI is crafting your letter…</span>
          </div>
          {#if coverLetterText}
            <Card class="shadow-lg border-primary/10">
              <CardContent class="p-0">
                <div class="overflow-hidden bg-white dark:bg-zinc-950/40 rounded-xl">
                  <CoverLetterPreview text={coverLetterText} />
                </div>
              </CardContent>
            </Card>
          {:else}
            <Card class="shadow-sm overflow-hidden">
              <CardContent class="p-8 space-y-6 bg-white dark:bg-zinc-950/40 min-h-[50vh]">
                {#each Array(5) as _}
                  <div class="space-y-2">
                    <Skeleton class="h-4 w-full" />
                    <Skeleton class="h-4 w-5/6" />
                    <Skeleton class="h-4 w-4/6" />
                  </div>
                {/each}
              </CardContent>
            </Card>
          {/if}
        </div>

      <!-- Generated letter -->
      {:else if rightPanel === 'letter'}
        <div class="space-y-3 animate-in fade-in slide-in-from-bottom-2 duration-400">
          <div class="flex items-center justify-between px-1">
            <h2 class="font-semibold flex items-center gap-2">
              <Sparkles class="w-4 h-4 text-amber-500" />
              Generated Letter
            </h2>
            <div class="flex gap-2">
              <Button variant="outline" size="sm" onclick={handleCopy}>
                {#if copied}
                  <Check class="w-3.5 h-3.5 mr-1 text-green-500" /> Copied
                {:else}
                  <Copy class="w-3.5 h-3.5 mr-1" /> Copy
                {/if}
              </Button>
              <Button variant="outline" size="sm" onclick={handleDownloadPdf} disabled={downloading}>
                {#if downloading}
                  <Loader2 class="w-3.5 h-3.5 mr-1 animate-spin" />
                {:else}
                  <Download class="w-3.5 h-3.5 mr-1" />
                {/if}
                PDF
              </Button>
            </div>
          </div>
          <Card class="shadow-lg border-primary/10">
            <CardContent class="p-0">
              <div class="overflow-hidden bg-white dark:bg-zinc-950/40 rounded-xl">
                <CoverLetterPreview text={coverLetterText} />
              </div>
            </CardContent>
          </Card>
        </div>
      {/if}

    </div>
  </div>
</div>
