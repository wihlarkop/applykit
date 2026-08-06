<script lang="ts">
  import { page } from '$app/state';
  import { activeProfile } from '$lib/activeProfile.svelte';
  import {
    generateCvPdf,
    generateCvStream,
    getCvHistoryEntry,
    getProfile,
  } from '$lib/api';
  import { authState } from '$lib/auth-state.svelte';
  import AiReadinessNotice from '$lib/components/AiReadinessNotice.svelte';
  import CvPreview from '$lib/components/CvPreview.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import PageHeader from '$lib/components/PageHeader.svelte';
  import ReadinessEmptyState from '$lib/components/resume-readiness/ReadinessEmptyState.svelte';
  import ReadinessExtractionPreview from '$lib/components/resume-readiness/ReadinessExtractionPreview.svelte';
  import ReadinessFindingList from '$lib/components/resume-readiness/ReadinessFindingList.svelte';
  import ReadinessSummary from '$lib/components/resume-readiness/ReadinessSummary.svelte';
  import { Button } from '$lib/components/ui/button';
  import { Card, CardContent } from '$lib/components/ui/card';
  import { Label } from '$lib/components/ui/label';
  import { Skeleton } from '$lib/components/ui/skeleton';
  import { Textarea } from '$lib/components/ui/textarea';
  import { consumeDraft, draftKey, saveDraft } from '$lib/draft-recovery';
  import type { ReadinessResponse } from '$lib/readiness-types';
  import {
    createResumeReadinessAnalysis,
    getLatestResumeReadiness,
  } from '$lib/resume-readiness-api';
  import type { ResumeReadinessResponse } from '$lib/resume-readiness-types';
  import { analyzeRoleMatch } from '$lib/role-match-api';
  import { consumeStructuredStream } from '$lib/stream';
  import { toastState } from '$lib/toast.svelte';
  import type { ProfileData } from '$lib/types';
  import { errorMessage } from '$lib/utils';
  import {
    Download,
    FileCheck2,
    FileText,
    History,
    Sparkles,
    UserRoundPen,
  } from '@lucide/svelte';
  import confetti from 'canvas-confetti';

  interface GenerateDraft {
    jobDescription: string;
    profile: ProfileData | null;
    enhanced: boolean;
  }

  interface WorkspaceData {
    readiness?: ReadinessResponse;
    activeProfileId?: number | null;
  }

  let { data }: { data: WorkspaceData } = $props();
  let readinessOverride = $state<ReadinessResponse | null>(null);
  const aiReadiness = $derived(readinessOverride ?? data.readiness);
  const aiReady = $derived(aiReadiness?.ai.ready ?? false);

  let profile: ProfileData | null = $state(null);
  let activeProfileData: ProfileData | null = $state(null);
  let enhanced = $state(false);
  let loading = $state(false);
  let downloading = $state(false);
  let profileLoading = $state(true);
  let jobDescription = $state('');
  let draftProfileId = $state<number | null>(null);
  let loadSequence = 0;

  let generatedCvId = $state<number | null>(null);
  let generatedCvProfileId = $state<number | null>(null);
  let viewingSavedVersion = $state(false);
  let roleMatchAnalysisId = $state<number | null>(null);
  let roleMatchJobDescription = $state('');
  let resumeReadiness = $state<ResumeReadinessResponse | null>(null);
  let readinessLoading = $state(false);
  let readinessError = $state('');

  const previewProfile = $derived(profile ?? activeProfileData);
  const isProfileEmpty = $derived.by(() => {
    if (profileLoading || !activeProfileData) return true;
    return (
      activeProfileData.work_experience.length === 0
      && activeProfileData.skills.length === 0
      && activeProfileData.education.length === 0
    );
  });

  function requestedGeneratedCvId(): number | null {
    const raw = page.url.searchParams.get('generated_cv_id');
    if (!raw) return null;
    const parsed = Number(raw);
    return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
  }

  function parseSnapshot(raw: string): ProfileData {
    const parsed: unknown = JSON.parse(raw);
    if (parsed == null || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error('The saved resume snapshot is not valid.');
    }
    return parsed as ProfileData;
  }

  $effect(() => {
    data.readiness;
    readinessOverride = null;
  });

  $effect(() => {
    const selected = activeProfile.current;
    const requestedId = requestedGeneratedCvId();
    const sequence = ++loadSequence;

    activeProfileData = null;
    profile = null;
    enhanced = false;
    profileLoading = true;
    draftProfileId = null;
    generatedCvId = null;
    generatedCvProfileId = null;
    viewingSavedVersion = requestedId != null;
    roleMatchAnalysisId = null;
    roleMatchJobDescription = '';
    resumeReadiness = null;
    readinessError = '';

    if (requestedId != null) {
      Promise.all([
        getCvHistoryEntry(requestedId),
        getLatestResumeReadiness(requestedId),
      ])
        .then(([entry, latestAnalysis]) => {
          if (sequence !== loadSequence) return;
          const snapshot = parseSnapshot(entry.profile_snapshot);
          profile = snapshot;
          activeProfileData = snapshot;
          enhanced = entry.enhanced;
          generatedCvId = entry.id;
          generatedCvProfileId = entry.profile_id;
          resumeReadiness = latestAnalysis;
        })
        .catch((error: unknown) => {
          if (sequence !== loadSequence) return;
          readinessError = errorMessage(error);
          toastState.error(`Could not open the saved resume: ${readinessError}`);
        })
        .finally(() => {
          if (sequence === loadSequence) profileLoading = false;
        });
      return;
    }

    if (!selected) {
      profileLoading = false;
      return;
    }

    getProfile(selected.id)
      .then((loadedProfile) => {
        if (sequence !== loadSequence) return;
        activeProfileData = loadedProfile;
        const restored = authState.authMode === 'password'
          ? consumeDraft<GenerateDraft>(sessionStorage, draftKey('/generate', selected.id))
          : null;
        if (restored) {
          jobDescription = restored.jobDescription;
          profile = restored.profile;
          enhanced = restored.enhanced;
          toastState.success('Draft restored after sign-in.');
        }
        draftProfileId = selected.id;
      })
      .catch((error: unknown) => {
        if (sequence !== loadSequence) return;
        toastState.error(`Failed to load profile data: ${errorMessage(error)}`);
      })
      .finally(() => {
        if (sequence === loadSequence) profileLoading = false;
      });
  });

  $effect(() => {
    const selected = activeProfile.current;
    if (
      viewingSavedVersion
      || authState.authMode !== 'password'
      || !selected
      || profileLoading
      || draftProfileId !== selected.id
    ) return;

    const generatedProfile = profile
      ? JSON.parse(JSON.stringify(profile)) as ProfileData
      : null;
    saveDraft(sessionStorage, draftKey('/generate', selected.id), {
      jobDescription,
      profile: generatedProfile,
      enhanced,
    } satisfies GenerateDraft);
  });

  async function handleGenerate() {
    const selected = activeProfile.current;
    if (!selected) return;
    if (!aiReady) {
      toastState.error('Verify the active AI connection before generating a resume.');
      return;
    }

    loading = true;
    profile = null;
    enhanced = false;
    generatedCvId = null;
    generatedCvProfileId = selected.id;
    viewingSavedVersion = false;
    roleMatchAnalysisId = null;
    roleMatchJobDescription = '';
    resumeReadiness = null;
    readinessError = '';

    try {
      const response = await generateCvStream({
        profile_id: selected.id,
        enhance: true,
        job_description: jobDescription.trim() || null,
      });
      await consumeStructuredStream(response, {
        onEvent(event, eventData) {
          if (event === 'done') {
            const result = eventData as {
              enhanced: boolean;
              profile: ProfileData;
              id: number;
            };
            profile = result.profile;
            activeProfileData = result.profile;
            enhanced = result.enhanced;
            generatedCvId = result.id;
            generatedCvProfileId = selected.id;
            toastState.success('Resume generated successfully.');
            confetti({ particleCount: 120, spread: 65, origin: { y: 0.6 } });
          } else if (event === 'rate_limit') {
            toastState.error('Rate limit reached. Please wait before generating again.');
          }
        },
        onError(message) {
          toastState.error(`Generation failed: ${message}`);
        },
      });
    } catch (error: unknown) {
      toastState.error(`Generation failed: ${errorMessage(error)}`);
    } finally {
      loading = false;
    }
  }

  async function handleDownloadPdf() {
    if (!profile) return;
    downloading = true;
    try {
      const blob = await generateCvPdf({ profile });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = 'resume.pdf';
      anchor.click();
      URL.revokeObjectURL(url);
      toastState.success('Resume PDF downloaded.');
    } catch (error: unknown) {
      toastState.error(`Download failed: ${errorMessage(error)}`);
    } finally {
      downloading = false;
    }
  }

  async function runResumeReadiness() {
    if (generatedCvId == null) return;

    readinessLoading = true;
    readinessError = '';
    try {
      const targetJob = jobDescription.trim();
      const selected = activeProfile.current;
      let analysisId = (
        roleMatchJobDescription === targetJob ? roleMatchAnalysisId : null
      );

      const profileMatches = (
        selected != null
        && (generatedCvProfileId == null || generatedCvProfileId === selected.id)
      );

      if (targetJob && analysisId == null && profileMatches && selected) {
        try {
          const roleMatch = await analyzeRoleMatch({
            profile_id: selected.id,
            job_description: targetJob,
          });
          analysisId = roleMatch.id;
          roleMatchAnalysisId = roleMatch.id;
          roleMatchJobDescription = targetJob;
        } catch (error: unknown) {
          roleMatchAnalysisId = null;
          roleMatchJobDescription = '';
          toastState.error(
            `Role Evidence Match was unavailable. Parseability and quality will still be checked: ${errorMessage(error)}`,
          );
        }
      }

      resumeReadiness = await createResumeReadinessAnalysis({
        generated_cv_id: generatedCvId,
        job_description: targetJob || null,
        role_match_analysis_id: analysisId,
      });
      toastState.success('Resume Readiness analysis completed.');
    } catch (error: unknown) {
      readinessError = errorMessage(error);
      toastState.error(`Resume analysis failed: ${readinessError}`);
    } finally {
      readinessLoading = false;
    }
  }

  async function refreshLatestReadiness() {
    if (generatedCvId == null) return;
    readinessLoading = true;
    readinessError = '';
    try {
      resumeReadiness = await getLatestResumeReadiness(generatedCvId);
    } catch (error: unknown) {
      readinessError = errorMessage(error);
    } finally {
      readinessLoading = false;
    }
  }
</script>

<div class="pb-10">
  <PageHeader
    title="Resume"
    subtitle="Create a role-specific resume, validate the exported PDF, and review actionable findings."
  />

  {#if aiReadiness && data.activeProfileId != null}
    <div class="mt-6">
      <AiReadinessNotice
        ai={aiReadiness.ai}
        profileId={data.activeProfileId}
        onrefreshed={(next) => (readinessOverride = next)}
      />
    </div>
  {/if}

  {#if viewingSavedVersion && generatedCvId != null}
    <div class="mt-6 flex flex-col justify-between gap-3 rounded-xl border bg-muted/30 p-4 sm:flex-row sm:items-center">
      <div class="flex items-start gap-3">
        <History class="mt-0.5 h-5 w-5 text-primary" />
        <div>
          <p class="font-semibold">Viewing saved resume #{generatedCvId}</p>
          <p class="text-sm text-muted-foreground">
            This immutable historical version can be downloaded and analyzed without regenerating it.
          </p>
        </div>
      </div>
      <Button href="/resume" variant="outline">Return to active profile</Button>
    </div>
  {/if}

  <div class="mt-6 lg:grid lg:grid-cols-2 lg:items-start lg:gap-10">
    <div class="space-y-5 lg:sticky lg:top-6">
      <div class="space-y-2">
        <Label for="jd" class="font-semibold">
          Job Description
          <span class="text-xs font-normal text-muted-foreground">(optional)</span>
        </Label>
        <Textarea
          id="jd"
          bind:value={jobDescription}
          placeholder="Paste a target job to tailor the resume and enable job-specific readiness checks…"
          rows={6}
          class="max-h-[40vh] resize-y bg-background/50"
        />
      </div>

      {#if activeProfile.current}
        <div class="flex items-center gap-2 rounded-lg border bg-muted/50 px-3 py-2 text-sm">
          <span>{activeProfile.current.icon}</span>
          <span class="font-medium">{activeProfile.current.label}</span>
          {#if viewingSavedVersion && generatedCvProfileId !== activeProfile.current.id}
            <span class="ml-auto text-xs text-muted-foreground">Historical profile snapshot</span>
          {/if}
        </div>
      {/if}

      <div class="flex flex-wrap gap-3">
        <Button
          onclick={handleGenerate}
          disabled={
            loading
            || !activeProfile.current
            || !aiReady
            || isProfileEmpty
            || profileLoading
          }
          class="shadow-md"
        >
          <Sparkles class="mr-2 h-4 w-4 {loading ? 'animate-pulse' : ''}" />
          {loading ? 'Generating…' : 'Generate Resume'}
        </Button>

        {#if profile}
          <Button variant="outline" onclick={handleDownloadPdf} disabled={downloading}>
            <Download class="mr-2 h-4 w-4" />
            {downloading ? 'Downloading…' : 'Download PDF'}
          </Button>
        {/if}
      </div>

      {#if loading}
        <div class="flex items-center gap-2 rounded-lg border border-primary/20 bg-primary/5 p-3 text-sm text-primary">
          <Sparkles class="h-4 w-4 animate-pulse" />
          Preparing a role-specific resume…
        </div>
      {:else if profile && generatedCvId != null}
        <div class="rounded-lg border bg-muted/50 p-3 text-sm">
          <span class="font-medium">{enhanced ? 'AI-assisted version' : 'Profile-based version'}</span>
          <span class="text-muted-foreground"> — Saved as resume #{generatedCvId}.</span>
        </div>
      {:else if isProfileEmpty && !profileLoading}
        <Card class="border-2 border-dashed border-yellow-400/60 bg-yellow-50/30 dark:bg-yellow-900/10">
          <CardContent>
            <EmptyState
              icon={UserRoundPen}
              title="Profile is empty"
              description="Add experience, education, or skills before generating a resume."
            >
              <Button href="/profile">Fill in my profile</Button>
            </EmptyState>
          </CardContent>
        </Card>
      {/if}
    </div>

    <div class="mt-8 lg:mt-0">
      {#if profileLoading}
        <div class="rounded-xl border bg-muted/30 p-8">
          <div class="mx-auto min-h-150 max-w-212.5 space-y-6 rounded-lg bg-white p-12 shadow-xl dark:bg-zinc-950/40">
            <Skeleton class="h-10 w-1/3" />
            <Skeleton class="h-4 w-full" />
            <Skeleton class="h-4 w-5/6" />
          </div>
        </div>
      {:else if previewProfile}
        <div class="relative rounded-xl border bg-muted/30 p-4 shadow-inner sm:p-8">
          {#if loading}
            <div class="absolute inset-0 z-10 flex items-center justify-center rounded-xl bg-background/60 backdrop-blur-[2px]">
              <div class="rounded-lg border bg-background px-4 py-2 text-sm font-medium text-primary shadow-lg">
                Enhancing with AI…
              </div>
            </div>
          {/if}
          <div class="mx-auto max-w-212.5 overflow-hidden rounded-lg border bg-white shadow-xl dark:bg-zinc-950/40">
            <CvPreview profile={previewProfile} />
          </div>
        </div>
      {:else}
        <Card class="flex min-h-64 items-center border-2 border-dashed bg-muted/30">
          <CardContent class="w-full">
            <EmptyState
              icon={FileText}
              title="Resume preview will appear here"
              description="Set up your profile and generate a saved resume version."
            />
          </CardContent>
        </Card>
      {/if}
    </div>
  </div>

  <section class="mt-10 space-y-4" aria-labelledby="readiness-section-heading">
    <div class="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
      <div>
        <p class="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Document validation</p>
        <h2 id="readiness-section-heading" class="mt-1 text-2xl font-black">Resume Readiness</h2>
        <p class="mt-1 max-w-2xl text-sm text-muted-foreground">
          This is an explainable document-quality assessment, not a probability of passing an employer's ATS.
        </p>
      </div>
      <div class="flex gap-2">
        {#if generatedCvId != null}
          <Button onclick={runResumeReadiness} disabled={readinessLoading}>
            <FileCheck2 class="mr-2 h-4 w-4" />
            {readinessLoading
              ? 'Analyzing…'
              : resumeReadiness
                ? 'Run again'
                : 'Check Resume Readiness'}
          </Button>
          {#if resumeReadiness}
            <Button variant="outline" onclick={refreshLatestReadiness} disabled={readinessLoading}>
              Refresh
            </Button>
          {/if}
        {/if}
      </div>
    </div>

    {#if readinessError}
      <div class="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
        {readinessError}
      </div>
    {/if}

    {#if resumeReadiness}
      <ReadinessSummary analysis={resumeReadiness} />
      {#if resumeReadiness.findings.length > 0}
        <ReadinessFindingList findings={resumeReadiness.findings} />
      {/if}
      {#if resumeReadiness.extraction}
        <ReadinessExtractionPreview extraction={resumeReadiness.extraction} />
      {/if}
    {:else}
      <ReadinessEmptyState generated={generatedCvId != null} />
    {/if}
  </section>
</div>

<style>
  @media print {
    :global(header), :global(nav) {
      display: none !important;
    }
  }
</style>
