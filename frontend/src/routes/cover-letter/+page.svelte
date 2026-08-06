<script lang="ts">
  import { activeProfile } from '$lib/activeProfile.svelte';
  import {
    analyzeFit,
    generateCoverLetterPdf,
    generateCoverLetterStream,
    getProfile,
    scrapeAnalyze,
  } from '$lib/api';
  import { authState } from '$lib/auth-state.svelte';
  import AiReadinessNotice from '$lib/components/AiReadinessNotice.svelte';
  import CoverLetterPreview from '$lib/components/CoverLetterPreview.svelte';
  import FitAnalysisDisplay from '$lib/components/RoleMatchFitAnalysisDisplay.svelte';
  import { Button } from '$lib/components/ui/button';
  import { Card, CardContent } from '$lib/components/ui/card';
  import { Input } from '$lib/components/ui/input';
  import { Label } from '$lib/components/ui/label';
  import { Skeleton } from '$lib/components/ui/skeleton';
  import { Textarea } from '$lib/components/ui/textarea';
  import { consumeDraft, draftKey, saveDraft } from '$lib/draft-recovery';
  import type { ReadinessResponse } from '$lib/readiness-types';
  import { consumeStream } from '$lib/stream';
  import { toastState } from '$lib/toast.svelte';
  import type { FitAnalysisResponse, ProfileData, Tone } from '$lib/types';
  import { errorMessage } from '$lib/utils';
  import {
    ArrowRight,
    Building2,
    Check,
    ChevronDown,
    Copy,
    Download,
    FileText,
    Globe2,
    Link,
    Loader2,
    Mail,
    MapPin,
    Pencil,
    Sparkles,
    TrendingUp,
    UserRoundPen,
  } from '@lucide/svelte';

  interface CoverLetterDraft {
    inputTab: 'paste' | 'url';
    jobUrl: string;
    isImported: boolean;
    importedDomain: string;
    companyName: string;
    roleTitle: string;
    location: string;
    salary: string;
    jobDescription: string;
    jobDescriptionExpanded: boolean;
    extraContext: string;
    tone: Tone;
    fitResult: FitAnalysisResponse | null;
    showInterviewPrep: boolean;
    coverLetterText: string;
    writingPreferencesOpen?: boolean;
    resultView?: 'fit' | 'letter';
  }

  let { data } = $props();
  let readinessOverride = $state<ReadinessResponse | null>(null);
  const readiness = $derived(readinessOverride ?? data.readiness);
  const aiReady = $derived(readiness?.ai.ready ?? false);

  $effect(() => {
    data.readiness;
    readinessOverride = null;
  });

  let inputTab = $state<'paste' | 'url'>('url');
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
  let writingPreferencesOpen = $state(false);
  let resultView = $state<'fit' | 'letter'>('fit');

  function cleanScrapedText(raw: string): string {
    return raw
      .replace(/^Title:.*\n?/m, '')
      .replace(/^URL Source:.*\n?/m, '')
      .replace(/^Published Time:.*\n?/m, '')
      .replace(/^Markdown Content:\s*\n?/m, '')
      .replace(/\[!\[.*?\]\(.*?\)\]\(.*?\)/g, '')
      .replace(/!\[.*?\]\(.*?\)/g, '')
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      .replace(/^#{1,6}\s+/gm, '')
      .replace(/\*\*\*(.+?)\*\*\*/g, '$1')
      .replace(/\*\*(.+?)\*\*/g, '$1')
      .replace(/__(.+?)__/g, '$1')
      .replace(/\*(.+?)\*/g, '$1')
      .replace(/_(.+?)_/g, '$1')
      .replace(/`([^`]+)`/g, '$1')
      .replace(/^[-*_]{3,}\s*$/gm, '')
      .replace(/^>\s*/gm, '')
      .replace(/\n{3,}/g, '\n\n')
      .trim();
  }

  function extractHttpJobUrl(raw: string): string | null {
    const candidate = raw.trim();
    if (!candidate || /\s/.test(candidate)) return null;
    try {
      const parsed = new URL(candidate);
      return parsed.protocol === 'http:' || parsed.protocol === 'https:' ? candidate : null;
    } catch {
      return null;
    }
  }

  function domainFor(raw: string): string {
    try {
      return new URL(raw).hostname.replace(/^www\./, '');
    } catch {
      return raw;
    }
  }

  let analyzing = $state(false);
  let fitResult = $state<FitAnalysisResponse | null>(null);
  let showInterviewPrep = $state(false);

  let coverLetterText = $state('');
  let loading = $state(false);
  let downloading = $state(false);
  let copied = $state(false);

  let activeProfileData: ProfileData | null = $state(null);
  let profileLoading = $state(true);
  let lastProfileId = $state<number | null>(null);
  let draftProfileId = $state<number | null>(null);

  const TONES: { value: Tone; label: string; description: string }[] = [
    { value: 'professional', label: 'Professional', description: 'Formal and polished' },
    { value: 'enthusiastic', label: 'Enthusiastic', description: 'Warm and energetic' },
    { value: 'concise', label: 'Concise', description: 'Short and direct' },
    { value: 'creative', label: 'Creative', description: 'Distinctive and memorable' },
  ];

  const jobReady = $derived(isImported && !!jobDescription.trim());
  const step1Done = $derived(jobReady);
  const step2Done = $derived(!!fitResult);
  const step3Done = $derived(!!coverLetterText);
  const currentStep = $derived(
    loading || coverLetterText ? 3 : jobReady || analyzing || fitResult ? 2 : 1,
  );

  const isProfileEmpty = $derived.by(() => {
    if (profileLoading || !activeProfileData) return true;
    return (
      activeProfileData.work_experience.length === 0 &&
      activeProfileData.skills.length === 0 &&
      activeProfileData.education.length === 0
    );
  });

  $effect(() => {
    const ap = activeProfile.current;
    const newId = ap?.id ?? null;
    activeProfileData = null;
    profileLoading = true;

    if (newId !== lastProfileId) {
      if (coverLetterText) {
        toastState.error('Profile switched — your in-progress letter was cleared.');
      }
      coverLetterText = '';
      resultView = 'fit';
      lastProfileId = newId;
    }

    if (!ap) {
      profileLoading = false;
      return;
    }

    getProfile(ap.id)
      .then((profile) => {
        activeProfileData = profile;
        const restored =
          authState.authMode === 'password'
            ? consumeDraft<CoverLetterDraft>(
                sessionStorage,
                draftKey('/cover-letter', ap.id),
              )
            : null;

        if (restored) {
          inputTab = restored.inputTab;
          jobUrl = restored.jobUrl;
          isImported = restored.isImported;
          importedDomain = restored.importedDomain;
          companyName = restored.companyName;
          roleTitle = restored.roleTitle;
          location = restored.location;
          salary = restored.salary;
          jobDescription = restored.jobDescription;
          jobDescriptionExpanded = restored.jobDescriptionExpanded;
          extraContext = restored.extraContext;
          tone = restored.tone;
          fitResult = restored.fitResult;
          showInterviewPrep = restored.showInterviewPrep;
          coverLetterText = restored.coverLetterText;
          writingPreferencesOpen =
            restored.writingPreferencesOpen ?? !!restored.fitResult;
          resultView =
            restored.resultView ?? (restored.coverLetterText ? 'letter' : 'fit');
          toastState.success('Draft restored after sign-in.');
        }

        draftProfileId = ap.id;
      })
      .catch((error: unknown) => {
        toastState.error(`Failed to load profile: ${errorMessage(error)}`);
      })
      .finally(() => {
        profileLoading = false;
      });
  });

  $effect(() => {
    const ap = activeProfile.current;
    if (
      authState.authMode !== 'password' ||
      !ap ||
      profileLoading ||
      draftProfileId !== ap.id
    ) {
      return;
    }

    const fitSnapshot = fitResult
      ? (JSON.parse(JSON.stringify(fitResult)) as FitAnalysisResponse)
      : null;

    saveDraft(sessionStorage, draftKey('/cover-letter', ap.id), {
      inputTab,
      jobUrl,
      isImported,
      importedDomain,
      companyName,
      roleTitle,
      location,
      salary,
      jobDescription,
      jobDescriptionExpanded,
      extraContext,
      tone,
      fitResult: fitSnapshot,
      showInterviewPrep,
      coverLetterText,
      writingPreferencesOpen,
      resultView,
    } satisfies CoverLetterDraft);
  });

  function resetGeneratedWork() {
    fitResult = null;
    coverLetterText = '';
    resultView = 'fit';
    writingPreferencesOpen = false;
    showInterviewPrep = false;
  }

  function changeJob() {
    inputTab = 'url';
    jobUrl = '';
    isImported = false;
    importedDomain = '';
    companyName = '';
    roleTitle = '';
    location = '';
    salary = '';
    jobDescription = '';
    jobDescriptionExpanded = false;
    extraContext = '';
    resetGeneratedWork();
  }

  async function handleImport() {
    const url = jobUrl.trim();
    if (!url) return;

    scraping = true;
    try {
      const analyzed = await scrapeAnalyze({ url });
      jobDescription = cleanScrapedText(analyzed.job_description);
      companyName = analyzed.company_name || '';
      roleTitle = analyzed.role_title || '';
      location = analyzed.location || '';
      salary = analyzed.salary || '';
      isImported = true;
      importedDomain = domainFor(url);
      resetGeneratedWork();
      toastState.success('Job posting imported.');
    } catch (error: unknown) {
      toastState.error(errorMessage(error));
    } finally {
      scraping = false;
    }
  }

  async function handleParsePasted() {
    const raw = jobDescription.trim();
    if (!raw) return;
    if (!aiReady) {
      toastState.error('Verify the active AI connection before extracting job details.');
      return;
    }

    scraping = true;
    try {
      const pastedUrl = extractHttpJobUrl(raw);
      const analyzed = await scrapeAnalyze({ text: raw });
      jobDescription = cleanScrapedText(analyzed.job_description || raw);
      companyName = analyzed.company_name || '';
      roleTitle = analyzed.role_title || '';
      location = analyzed.location || '';
      salary = analyzed.salary || '';
      jobUrl = pastedUrl || '';
      importedDomain = pastedUrl ? domainFor(pastedUrl) : 'Pasted description';
      isImported = true;
      resetGeneratedWork();
      toastState.success(
        pastedUrl ? 'Job URL imported.' : 'Job details extracted.',
      );
    } catch (error: unknown) {
      toastState.error(`Failed to extract details: ${errorMessage(error)}`);
    } finally {
      scraping = false;
    }
  }

  async function handleAnalyzeFit() {
    const ap = activeProfile.current;
    if (!ap || !jobReady) return;
    if (!aiReady) {
      toastState.error('Verify the active AI connection before analyzing fit.');
      return;
    }

    analyzing = true;
    fitResult = null;
    coverLetterText = '';
    resultView = 'fit';

    try {
      fitResult = await analyzeFit(ap.id, jobDescription);
      writingPreferencesOpen = true;
    } catch (error: unknown) {
      toastState.error(errorMessage(error));
    } finally {
      analyzing = false;
    }
  }

  function acceptSuggestedEmphasis() {
    if (fitResult) extraContext = fitResult.suggested_emphasis;
  }

  function openWritingPreferences() {
    writingPreferencesOpen = true;
  }

  async function handleGenerate() {
    const ap = activeProfile.current;
    if (!ap || !jobReady) return;
    if (!aiReady) {
      toastState.error('Verify the active AI connection before generating a cover letter.');
      return;
    }

    loading = true;
    coverLetterText = '';
    resultView = 'letter';

    try {
      const response = await generateCoverLetterStream({
        profile_id: ap.id,
        job_description: jobDescription,
        extra_context:
          [roleTitle ? `Target role: ${roleTitle}` : '', extraContext]
            .filter(Boolean)
            .join('\n') || undefined,
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

      if (!response.ok) {
        const error = await response
          .json()
          .catch(() => ({ detail: 'Generation failed' }));
        throw new Error(error.detail ?? 'Generation failed');
      }

      await consumeStream(response, {
        onChunk: (text) => {
          coverLetterText += text;
        },
        onDone: () => {
          loading = false;
          toastState.success('Cover letter generated.');
        },
        onError: (message) => {
          toastState.error(message);
          loading = false;
        },
      });
    } catch (error: unknown) {
      toastState.error(`Generation failed: ${errorMessage(error)}`);
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
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = 'cover-letter.pdf';
      anchor.click();
      URL.revokeObjectURL(url);
      toastState.success('PDF downloaded.');
    } catch (error: unknown) {
      toastState.error(`Download failed: ${errorMessage(error)}`);
    } finally {
      downloading = false;
    }
  }
</script>

<div class="w-full space-y-6 pb-12">
  {#if readiness && data.activeProfileId != null}
    <AiReadinessNotice
      ai={readiness.ai}
      profileId={data.activeProfileId}
      onrefreshed={(next) => (readinessOverride = next)}
    />
  {/if}

  <header class="space-y-5">
    <div class="space-y-1.5">
      <div class="flex items-center gap-2 text-primary">
        <Mail class="h-5 w-5" aria-hidden="true" />
        <span class="text-xs font-semibold uppercase tracking-[0.18em]">Application writing</span>
      </div>
      <h1 class="text-2xl font-bold tracking-tight sm:text-3xl">Cover Letter</h1>
      <p class="max-w-2xl text-sm leading-6 text-muted-foreground sm:text-base">
        Import a role, review the evidence behind your fit, and write a tailored letter without losing your place.
      </p>
    </div>

    <nav aria-label="Cover letter progress" class="rounded-xl border bg-card px-4 py-3 shadow-sm sm:px-5">
      <ol class="grid grid-cols-3 gap-2">
        <li class="flex min-w-0 items-center gap-2">
          <span
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-xs font-semibold
              {step1Done
                ? 'border-primary bg-primary text-primary-foreground'
                : currentStep === 1
                  ? 'border-primary text-primary ring-4 ring-primary/10'
                  : 'border-border text-muted-foreground'}"
          >
            {#if step1Done}<Check class="h-3.5 w-3.5" aria-hidden="true" />{:else}1{/if}
          </span>
          <span class="min-w-0">
            <span class="block truncate text-xs font-semibold sm:text-sm">Job details</span>
            <span class="hidden truncate text-[11px] text-muted-foreground sm:block">Import or paste</span>
          </span>
        </li>

        <li class="flex min-w-0 items-center gap-2 border-l pl-3 sm:pl-5">
          <span
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-xs font-semibold
              {step2Done
                ? 'border-primary bg-primary text-primary-foreground'
                : currentStep === 2
                  ? 'border-primary text-primary ring-4 ring-primary/10'
                  : 'border-border text-muted-foreground'}"
          >
            {#if step2Done}<Check class="h-3.5 w-3.5" aria-hidden="true" />{:else}2{/if}
          </span>
          <span class="min-w-0">
            <span class="block truncate text-xs font-semibold sm:text-sm">Fit Review</span>
            <span class="hidden truncate text-[11px] text-muted-foreground sm:block">Match evidence</span>
          </span>
        </li>

        <li class="flex min-w-0 items-center gap-2 border-l pl-3 sm:pl-5">
          <span
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-xs font-semibold
              {step3Done
                ? 'border-primary bg-primary text-primary-foreground'
                : currentStep === 3
                  ? 'border-primary text-primary ring-4 ring-primary/10'
                  : 'border-border text-muted-foreground'}"
          >
            {#if step3Done}<Check class="h-3.5 w-3.5" aria-hidden="true" />{:else}3{/if}
          </span>
          <span class="min-w-0">
            <span class="block truncate text-xs font-semibold sm:text-sm">Cover Letter</span>
            <span class="hidden truncate text-[11px] text-muted-foreground sm:block">Write and export</span>
          </span>
        </li>
      </ol>
    </nav>
  </header>

  <div
    data-cover-letter-layout="hybrid"
    class="grid items-start gap-6 xl:grid-cols-[minmax(22rem,0.72fr)_minmax(0,1.28fr)]"
  >
    <div class="space-y-5 xl:sticky xl:top-6">
      <Card class="overflow-hidden shadow-sm">
        <CardContent class="space-y-5 p-5 sm:p-6">
          <div class="flex items-start justify-between gap-4">
            <div class="space-y-1">
              <p class="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                Step 1
              </p>
              <h2 class="text-lg font-semibold">Add the job</h2>
              <p class="text-sm leading-5 text-muted-foreground">
                Start with the source. You can still edit every extracted field.
              </p>
            </div>

            {#if jobReady}
              <Button type="button" variant="outline" size="sm" onclick={changeJob}>
                <Pencil class="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
                Change job
              </Button>
            {/if}
          </div>

          {#if !jobReady}
            <div
              class="grid grid-cols-2 rounded-lg bg-muted p-1"
              aria-label="Job input method"
            >
              <button
                type="button"
                aria-pressed={inputTab === 'url'}
                class="inline-flex min-h-10 items-center justify-center gap-2 rounded-md px-3 text-sm font-medium transition-colors
                  {inputTab === 'url'
                    ? 'bg-background text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'}"
                onclick={() => (inputTab = 'url')}
              >
                <Link class="h-4 w-4" aria-hidden="true" />
                Import URL
              </button>
              <button
                type="button"
                aria-pressed={inputTab === 'paste'}
                class="inline-flex min-h-10 items-center justify-center gap-2 rounded-md px-3 text-sm font-medium transition-colors
                  {inputTab === 'paste'
                    ? 'bg-background text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'}"
                onclick={() => (inputTab = 'paste')}
              >
                <FileText class="h-4 w-4" aria-hidden="true" />
                Paste text
              </button>
            </div>

            {#if inputTab === 'url'}
              <div class="space-y-3">
                <div class="space-y-1.5">
                  <Label for="job-url">Job posting URL</Label>
                  <Input
                    id="job-url"
                    bind:value={jobUrl}
                    placeholder="https://job-boards.greenhouse.io/..."
                    autocomplete="url"
                    class="h-11"
                  />
                  <p class="text-xs leading-5 text-muted-foreground">
                    Best for Greenhouse, Lever, Ashby, and most public job boards.
                  </p>
                </div>
                <Button
                  type="button"
                  onclick={handleImport}
                  disabled={scraping || !jobUrl.trim()}
                  class="w-full"
                  size="lg"
                >
                  {#if scraping}
                    <Loader2 class="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                    Importing job…
                  {:else}
                    Import job
                    <ArrowRight class="ml-2 h-4 w-4" aria-hidden="true" />
                  {/if}
                </Button>
              </div>
            {:else}
              <div class="space-y-3">
                <div class="space-y-1.5">
                  <Label for="job-description">Job description</Label>
                  <Textarea
                    id="job-description"
                    bind:value={jobDescription}
                    placeholder="Paste the complete job description here..."
                    rows={9}
                    class="max-h-[44vh] resize-y bg-background text-sm leading-6"
                  />
                  <p class="text-xs leading-5 text-muted-foreground">
                    A standalone URL pasted here is safely routed through the URL importer.
                  </p>
                </div>
                <Button
                  type="button"
                  onclick={handleParsePasted}
                  disabled={scraping || !jobDescription.trim() || !aiReady}
                  class="w-full"
                  size="lg"
                >
                  {#if scraping}
                    <Loader2 class="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                    Extracting details…
                  {:else}
                    Extract details
                    <Sparkles class="ml-2 h-4 w-4" aria-hidden="true" />
                  {/if}
                </Button>
              </div>
            {/if}
          {:else}
            <div class="overflow-hidden rounded-xl border bg-muted/20">
              <div class="space-y-4 p-4 sm:p-5">
                <div class="flex items-start gap-3">
                  <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Building2 class="h-5 w-5" aria-hidden="true" />
                  </div>
                  <div class="min-w-0 flex-1">
                    <p class="truncate text-base font-semibold">
                      {roleTitle || 'Untitled role'}
                    </p>
                    <p class="truncate text-sm text-muted-foreground">
                      {companyName || 'Company not detected'}
                    </p>
                  </div>
                  <span class="rounded-full bg-emerald-500/10 px-2.5 py-1 text-[11px] font-semibold text-emerald-700 dark:text-emerald-300">
                    {jobUrl ? 'Imported' : 'Extracted'}
                  </span>
                </div>

                <div class="flex flex-wrap gap-x-4 gap-y-2 text-xs text-muted-foreground">
                  {#if location}
                    <span class="inline-flex items-center gap-1.5">
                      <MapPin class="h-3.5 w-3.5" aria-hidden="true" />
                      {location}
                    </span>
                  {/if}
                  <span class="inline-flex items-center gap-1.5">
                    <Globe2 class="h-3.5 w-3.5" aria-hidden="true" />
                    {importedDomain || 'Pasted description'}
                  </span>
                </div>
              </div>

              <button
                type="button"
                aria-expanded={jobDescriptionExpanded}
                class="flex min-h-11 w-full items-center justify-between border-t px-4 text-left text-sm font-medium hover:bg-muted/50 sm:px-5"
                onclick={() => (jobDescriptionExpanded = !jobDescriptionExpanded)}
              >
                <span>{jobDescriptionExpanded ? 'Hide' : 'View'} job description</span>
                <ChevronDown
                  class="h-4 w-4 transition-transform {jobDescriptionExpanded ? 'rotate-180' : ''}"
                  aria-hidden="true"
                />
              </button>

              {#if jobDescriptionExpanded}
                <div class="max-h-72 overflow-y-auto border-t bg-background px-4 py-4 sm:px-5">
                  <p class="whitespace-pre-wrap text-sm leading-6 text-muted-foreground">
                    {jobDescription}
                  </p>
                </div>
              {/if}
            </div>

            <section class="space-y-3" aria-labelledby="job-details-heading">
              <div>
                <h3 id="job-details-heading" class="text-sm font-semibold">Job details</h3>
                <p class="text-xs leading-5 text-muted-foreground">
                  Correct anything the source did not provide clearly.
                </p>
              </div>

              <div class="grid gap-3 sm:grid-cols-2">
                <div class="space-y-1.5">
                  <Label for="company">Company</Label>
                  <Input id="company" bind:value={companyName} placeholder="Company name" />
                </div>
                <div class="space-y-1.5">
                  <Label for="salary">Salary</Label>
                  <Input id="salary" bind:value={salary} placeholder="Optional" />
                </div>
                <div class="space-y-1.5 sm:col-span-2">
                  <Label for="role">Role</Label>
                  <Input id="role" bind:value={roleTitle} placeholder="Target role" />
                </div>
                <div class="space-y-1.5 sm:col-span-2">
                  <Label for="location">Location</Label>
                  <Input id="location" bind:value={location} placeholder="Tokyo, Japan" />
                </div>
              </div>
            </section>

            {#if !fitResult}
              <div class="space-y-2 border-t pt-5">
                <Button
                  type="button"
                  onclick={handleAnalyzeFit}
                  disabled={analyzing || loading || !aiReady}
                  class="w-full"
                  size="lg"
                >
                  {#if analyzing}
                    <Loader2 class="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                    Analyzing fit…
                  {:else}
                    <TrendingUp class="mr-2 h-4 w-4" aria-hidden="true" />
                    Analyze fit
                  {/if}
                </Button>
                <button
                  type="button"
                  class="min-h-10 w-full rounded-md px-3 text-sm font-medium text-muted-foreground hover:bg-muted hover:text-foreground"
                  onclick={openWritingPreferences}
                >
                  Generate without fit review
                </button>
              </div>
            {:else}
              <div class="flex items-center gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-3.5 py-3 text-sm">
                <span class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-500/15 text-emerald-700 dark:text-emerald-300">
                  <Check class="h-3.5 w-3.5" aria-hidden="true" />
                </span>
                <span class="font-medium">Fit review complete. Use the evidence to guide your letter.</span>
              </div>
            {/if}
          {/if}
        </CardContent>
      </Card>

      {#if jobReady && (writingPreferencesOpen || fitResult || coverLetterText)}
        <Card class="shadow-sm">
          <CardContent class="space-y-5 p-5 sm:p-6">
            <div class="space-y-1">
              <p class="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                Step 3
              </p>
              <h2 class="text-lg font-semibold">Writing preferences</h2>
              <p class="text-sm leading-5 text-muted-foreground">
                Choose the voice and tell ApplyKit what deserves extra attention.
              </p>
            </div>

            <div class="grid gap-2 sm:grid-cols-2" aria-label="Cover letter tone">
              {#each TONES as option}
                <button
                  type="button"
                  aria-pressed={tone === option.value}
                  onclick={() => (tone = option.value)}
                  class="rounded-lg border p-3 text-left transition-colors
                    {tone === option.value
                      ? 'border-primary bg-primary/5 ring-2 ring-primary/10'
                      : 'border-border hover:border-foreground/20 hover:bg-muted/40'}"
                >
                  <span class="block text-sm font-semibold">{option.label}</span>
                  <span class="mt-0.5 block text-xs text-muted-foreground">
                    {option.description}
                  </span>
                </button>
              {/each}
            </div>

            <div class="space-y-1.5">
              <Label for="extra-context">
                What should the letter emphasize?
                <span class="font-normal text-muted-foreground">(optional)</span>
              </Label>
              <Textarea
                id="extra-context"
                bind:value={extraContext}
                placeholder="Highlight my backend, AI, and production experience..."
                rows={3}
                class="resize-y bg-background text-sm"
              />
            </div>

            {#if activeProfile.current}
              <div class="flex items-center gap-3 rounded-lg bg-muted/50 px-3.5 py-3">
                <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-background text-sm shadow-sm">
                  {activeProfile.current.icon}
                </div>
                <div class="min-w-0 flex-1">
                  <p class="truncate text-sm font-semibold">{activeProfile.current.label}</p>
                  <p class="text-xs text-muted-foreground">Active writing profile</p>
                </div>
              </div>
            {/if}

            {#if isProfileEmpty && !profileLoading}
              <div class="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4">
                <p class="text-sm font-semibold">Your active profile is empty</p>
                <p class="mt-1 text-xs leading-5 text-muted-foreground">
                  Add experience, skills, or education before generating a useful letter.
                </p>
                <Button href="/profile" variant="outline" size="sm" class="mt-3">
                  <UserRoundPen class="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
                  Complete profile
                </Button>
              </div>
            {/if}

            <Button
              type="button"
              onclick={handleGenerate}
              disabled={loading || !aiReady || isProfileEmpty || profileLoading}
              class="w-full"
              size="lg"
            >
              {#if loading}
                <Loader2 class="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                Writing cover letter…
              {:else}
                <Sparkles class="mr-2 h-4 w-4" aria-hidden="true" />
                Generate cover letter
              {/if}
            </Button>
          </CardContent>
        </Card>
      {/if}
    </div>

    <Card class="min-h-[34rem] overflow-hidden shadow-sm">
      <CardContent class="p-0">
        {#if !jobReady}
          <div class="p-6 sm:p-8">
            <div class="max-w-xl space-y-6">
              <div class="space-y-2">
                <p class="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                  Guided workflow
                </p>
                <h2 class="text-xl font-semibold">What happens next?</h2>
                <p class="text-sm leading-6 text-muted-foreground">
                  ApplyKit keeps the source, your evidence review, and the final letter in one continuous workspace.
                </p>
              </div>

              <div class="grid gap-3">
                <div class="flex gap-3 rounded-xl border bg-muted/20 p-4">
                  <span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Link class="h-4 w-4" aria-hidden="true" />
                  </span>
                  <div>
                    <p class="text-sm font-semibold">Import reliable job details</p>
                    <p class="mt-1 text-xs leading-5 text-muted-foreground">
                      Extract the company, role, location, and full description from the source.
                    </p>
                  </div>
                </div>

                <div class="flex gap-3 rounded-xl border bg-muted/20 p-4">
                  <span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <TrendingUp class="h-4 w-4" aria-hidden="true" />
                  </span>
                  <div>
                    <p class="text-sm font-semibold">Review matching evidence</p>
                    <p class="mt-1 text-xs leading-5 text-muted-foreground">
                      See which requirements your profile supports and where the evidence is weaker.
                    </p>
                  </div>
                </div>

                <div class="flex gap-3 rounded-xl border bg-muted/20 p-4">
                  <span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Mail class="h-4 w-4" aria-hidden="true" />
                  </span>
                  <div>
                    <p class="text-sm font-semibold">Write from verified context</p>
                    <p class="mt-1 text-xs leading-5 text-muted-foreground">
                      Generate, copy, and export a letter tailored to the role and your active profile.
                    </p>
                  </div>
                </div>
              </div>

              {#if activeProfile.current}
                <div class="flex items-center gap-3 border-t pt-5">
                  <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted text-sm">
                    {activeProfile.current.icon}
                  </div>
                  <div class="min-w-0">
                    <p class="truncate text-sm font-semibold">{activeProfile.current.label}</p>
                    <p class="text-xs text-muted-foreground">This profile will be used for analysis and writing.</p>
                  </div>
                </div>
              {/if}
            </div>
          </div>
        {:else if analyzing}
          <div class="space-y-6 p-6 sm:p-8">
            <div class="space-y-2">
              <p class="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                Fit Review
              </p>
              <h2 class="text-xl font-semibold">Analyzing your evidence</h2>
              <p class="text-sm leading-6 text-muted-foreground">
                Reviewing role requirements against experience, skills, projects, and eligibility signals.
              </p>
            </div>
            <div class="space-y-4">
              <Skeleton class="h-28 w-full rounded-xl" />
              <Skeleton class="h-20 w-full rounded-xl" />
              <Skeleton class="h-20 w-full rounded-xl" />
            </div>
          </div>
        {:else if loading}
          <div class="space-y-7 p-6 sm:p-8">
            <div class="space-y-2">
              <p class="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                Cover Letter
              </p>
              <h2 class="text-xl font-semibold">Writing your cover letter</h2>
              <p class="text-sm leading-6 text-muted-foreground">
                Combining the imported role, your profile, and {fitResult ? 'verified fit evidence' : 'your writing preferences'}.
              </p>
            </div>
            <div class="rounded-xl border bg-muted/20 p-5">
              <div class="space-y-3">
                <div class="flex items-center gap-2 text-sm font-medium">
                  <Loader2 class="h-4 w-4 animate-spin text-primary" aria-hidden="true" />
                  Drafting and streaming the result…
                </div>
                <Skeleton class="h-3 w-full" />
                <Skeleton class="h-3 w-[92%]" />
                <Skeleton class="h-3 w-[84%]" />
                <Skeleton class="mt-5 h-3 w-full" />
                <Skeleton class="h-3 w-[88%]" />
              </div>
            </div>
          </div>
        {:else if coverLetterText}
          <div class="border-b px-5 py-4 sm:px-6">
            <div class="flex flex-wrap items-center justify-between gap-3">
              <div class="flex rounded-lg bg-muted p-1" aria-label="Result view">
                <button
                  type="button"
                  aria-pressed={resultView === 'letter'}
                  class="rounded-md px-3 py-1.5 text-sm font-medium transition-colors
                    {resultView === 'letter'
                      ? 'bg-background text-foreground shadow-sm'
                      : 'text-muted-foreground hover:text-foreground'}"
                  onclick={() => (resultView = 'letter')}
                >
                  Cover Letter
                </button>
                {#if fitResult}
                  <button
                    type="button"
                    aria-pressed={resultView === 'fit'}
                    class="rounded-md px-3 py-1.5 text-sm font-medium transition-colors
                      {resultView === 'fit'
                        ? 'bg-background text-foreground shadow-sm'
                        : 'text-muted-foreground hover:text-foreground'}"
                    onclick={() => (resultView = 'fit')}
                  >
                    Fit Review
                  </button>
                {/if}
              </div>

              {#if resultView === 'letter'}
                <div class="flex items-center gap-2">
                  <Button type="button" variant="outline" size="sm" onclick={handleCopy}>
                    {#if copied}
                      <Check class="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
                      Copied
                    {:else}
                      <Copy class="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
                      Copy
                    {/if}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onclick={handleDownloadPdf}
                    disabled={downloading}
                  >
                    {#if downloading}
                      <Loader2 class="mr-1.5 h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                    {:else}
                      <Download class="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
                    {/if}
                    PDF
                  </Button>
                </div>
              {/if}
            </div>
          </div>

          {#if resultView === 'letter'}
            <div class="bg-muted/20 p-4 sm:p-5 lg:p-6">
              <div class="mx-auto min-h-[42rem] max-w-[44rem] rounded-xl border bg-background shadow-sm">
                <CoverLetterPreview text={coverLetterText} />
              </div>
            </div>
          {:else if fitResult}
            <div class="p-5 sm:p-6 lg:p-8">
              <FitAnalysisDisplay
                {fitResult}
                {companyName}
                onReanalyze={handleAnalyzeFit}
                {analyzing}
                onAcceptEmphasis={acceptSuggestedEmphasis}
                bind:showInterviewPrep
                embedded={true}
              />
            </div>
          {/if}
        {:else if fitResult}
          <div class="space-y-5 p-5 sm:p-6 lg:p-8">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                Step 2
              </p>
              <h2 class="mt-1 text-xl font-semibold">Fit Review</h2>
            </div>
            <FitAnalysisDisplay
              {fitResult}
              {companyName}
              onReanalyze={handleAnalyzeFit}
              {analyzing}
              onAcceptEmphasis={acceptSuggestedEmphasis}
              bind:showInterviewPrep
              embedded={true}
            />
          </div>
        {:else}
          <div class="p-6 sm:p-8">
            <div class="max-w-xl space-y-6">
              <div class="space-y-2">
                <p class="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                  Step 2
                </p>
                <h2 class="text-xl font-semibold">See how your experience matches</h2>
                <p class="text-sm leading-6 text-muted-foreground">
                  Fit Review turns the job description into traceable requirements and connects them to evidence in your active profile.
                </p>
              </div>

              <div class="grid gap-3 sm:grid-cols-2">
                <div class="rounded-xl border bg-muted/20 p-4">
                  <p class="text-sm font-semibold">What it reviews</p>
                  <ul class="mt-3 space-y-2 text-xs leading-5 text-muted-foreground">
                    <li class="flex gap-2"><Check class="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />Required skills</li>
                    <li class="flex gap-2"><Check class="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />Supporting experience</li>
                    <li class="flex gap-2"><Check class="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />Eligibility signals</li>
                  </ul>
                </div>
                <div class="rounded-xl border bg-muted/20 p-4">
                  <p class="text-sm font-semibold">What you get</p>
                  <ul class="mt-3 space-y-2 text-xs leading-5 text-muted-foreground">
                    <li class="flex gap-2"><Check class="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />Evidence-backed score</li>
                    <li class="flex gap-2"><Check class="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />Strengths and gaps</li>
                    <li class="flex gap-2"><Check class="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />Writing guidance</li>
                  </ul>
                </div>
              </div>

              <div class="flex items-center gap-3 rounded-xl border border-primary/20 bg-primary/5 p-4">
                <TrendingUp class="h-5 w-5 shrink-0 text-primary" aria-hidden="true" />
                <p class="text-sm leading-5">
                  Run <span class="font-semibold">Analyze fit</span> from the job panel, or continue without it when you are in a hurry.
                </p>
              </div>
            </div>
          </div>
        {/if}
      </CardContent>
    </Card>
  </div>
</div>
