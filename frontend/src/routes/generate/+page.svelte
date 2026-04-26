<script lang="ts">
  import { activeProfile } from '$lib/activeProfile.svelte';
  import { generateCvPdf, generateCvStream, getProfile } from '$lib/api';
  import CvPreview from '$lib/components/CvPreview.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import PageHeader from '$lib/components/PageHeader.svelte';
  import { Button } from '$lib/components/ui/button';
  import { Card, CardContent } from '$lib/components/ui/card';
  import { Label } from '$lib/components/ui/label';
  import { Skeleton } from '$lib/components/ui/skeleton';
  import { Textarea } from '$lib/components/ui/textarea';
  import { consumeStructuredStream } from '$lib/stream';
  import { toastState } from '$lib/toast.svelte';
  import type { ProfileData } from '$lib/types';
  import { errorMessage } from '$lib/utils';
  import { Download, FileText, Lock, Sparkles, UserRoundPen } from '@lucide/svelte';
  import confetti from 'canvas-confetti';

  let { data } = $props();
  const isOnboarded = $derived(data.isOnboarded);

  let profile: ProfileData | null = $state(null);
  let enhanced = $state(false);
  let loading = $state(false);
  let downloading = $state(false);
  let jobDescription = $state('');
  let activeProfileData: ProfileData | null = $state(null);
  let profileLoading = $state(true);

  // Always show something in the preview: the generated CV if available, else the raw profile
  const previewProfile = $derived(profile ?? activeProfileData);

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
    activeProfileData = null;
    profile = null;
    enhanced = false;
    profileLoading = true;
    if (!ap) { profileLoading = false; return; }
    getProfile(ap.id)
      .then(p => { activeProfileData = p; })
      .catch((e) => { toastState.error(`Failed to load profile data: ${errorMessage(e)}`); })
      .finally(() => { profileLoading = false; });
  });

  async function handleGenerate() {
    const ap = activeProfile.current;
    if (!ap) return;
    loading = true;
    profile = null;
    enhanced = false;
    try {
      const response = await generateCvStream({
        profile_id: ap.id,
        enhance: true,
        job_description: jobDescription.trim() || null,
      });
      await consumeStructuredStream(response, {
        onEvent(event, eventData) {
          if (event === 'done') {
            const d = eventData as { enhanced: boolean; profile: ProfileData; id: number };
            profile = d.profile;
            enhanced = d.enhanced;
            toastState.success('CV Generated Successfully!');
            confetti({
              particleCount: 150,
              spread: 70,
              origin: { y: 0.6 },
              colors: ['#3b82f6', '#8b5cf6', '#10b981'],
            });
          } else if (event === 'rate_limit') {
            toastState.error(`Rate limit reached. Please wait before generating again.`);
          }
        },
        onError(msg) {
          toastState.error(`Generation failed: ${msg}`);
        },
      });
    } catch (e: unknown) {
      toastState.error(`Generation failed: ${errorMessage(e)}`);
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
      const a = document.createElement('a');
      a.href = url;
      a.download = 'cv.pdf';
      a.click();
      URL.revokeObjectURL(url);
      toastState.success('PDF Downloaded!');
    } catch (e: unknown) {
      toastState.error(`Download failed: ${errorMessage(e)}`);
    } finally {
      downloading = false;
    }
  }
</script>

<div class="pb-10">
  <PageHeader
    title="Generate CV"
    subtitle="Create an ATS-optimized CV tailored from your profile."
  />

  <div class="mt-6 lg:grid lg:grid-cols-2 lg:gap-10 lg:items-start">

    <!-- Left panel: controls (sticky on desktop) -->
    <div class="lg:sticky lg:top-6 space-y-5">

      <div class="space-y-2">
        <Label for="jd" class="font-semibold">
          Job Description
          <span class="text-muted-foreground text-xs font-normal">(optional — helps AI tailor your CV)</span>
        </Label>
        <Textarea
          id="jd"
          bind:value={jobDescription}
          placeholder="Paste the job posting here to get a CV tailored to this specific role…"
          rows={6}
          class="bg-background/50 resize-y max-h-[40vh]"
        />
      </div>

      {#if activeProfile.current}
        <div class="flex items-center gap-2 px-3 py-2 rounded-lg bg-muted/50 border text-sm">
          <span class="text-base leading-none">{activeProfile.current.icon}</span>
          <span class="font-medium">{activeProfile.current.label}</span>
        </div>
      {/if}

      <div class="flex flex-wrap gap-3">
        <Button
          onclick={handleGenerate}
          disabled={loading || !isOnboarded || isProfileEmpty || profileLoading}
          class="shadow-md"
        >
          {#if !isOnboarded}
            <Lock class="w-4 h-4 mr-2" /> Locked
          {:else}
            <Sparkles class="w-4 h-4 mr-2 {loading ? 'animate-pulse' : ''}" />
            {loading ? 'Generating…' : 'Generate ATS CV'}
          {/if}
        </Button>

        {#if profile}
          <Button variant="outline" onclick={handleDownloadPdf} disabled={downloading} class="shadow-sm">
            <Download class="w-4 h-4 mr-2" />
            {downloading ? 'Downloading…' : 'Download PDF'}
          </Button>
        {/if}
      </div>

      <!-- Status messages -->
      {#if loading}
        <div class="flex items-center gap-2 text-sm bg-primary/5 p-3 rounded-lg border border-primary/20 animate-pulse">
          <Sparkles class="w-4 h-4 text-primary" />
          <span class="text-primary font-medium">AI is crafting your tailored CV…</span>
        </div>
      {:else if profile}
        <div class="flex items-center gap-2 text-sm bg-muted/50 p-3 rounded-lg border">
          {#if enhanced}
            <div class="flex items-center gap-1.5 font-medium text-amber-600 dark:text-amber-400">
              <Sparkles class="w-4 h-4" /> AI Enhanced
            </div>
            <span class="text-muted-foreground flex-1">— Your CV was optimized with AI assistance.</span>
          {:else}
            <div class="font-medium text-muted-foreground">No Enhancement</div>
            <span class="text-muted-foreground flex-1">— Generated from profile without AI (API key not set).</span>
          {/if}
        </div>
      {:else if isProfileEmpty && !profileLoading}
        <Card class="border-dashed border-2 border-yellow-400/60 bg-yellow-50/30 dark:bg-yellow-900/10">
          <CardContent>
            <EmptyState
              icon={UserRoundPen}
              iconClass="text-yellow-600 dark:text-yellow-400"
              iconBg="bg-yellow-100 dark:bg-yellow-900/30"
              title="Profile is empty"
              description="Add your work experience, education, or skills to {activeProfile.current?.label ?? 'this profile'} before generating a CV."
            >
              <Button href="/profile" variant="default">Fill in my profile</Button>
            </EmptyState>
          </CardContent>
        </Card>
      {/if}
    </div>

    <!-- Right panel: live CV preview -->
    <div class="mt-8 lg:mt-0">
      {#if profileLoading}
        <div class="bg-muted/30 p-4 sm:p-8 rounded-xl border shadow-inner">
          <div class="bg-white dark:bg-zinc-950/40 p-12 space-y-8 rounded-lg shadow-xl mx-auto max-w-212.5 min-h-150 transition-colors">
            <div class="space-y-4">
              <Skeleton class="h-10 w-1/3" />
              <Skeleton class="h-4 w-1/4" />
            </div>
            <div class="space-y-2">
              <Skeleton class="h-4 w-full" />
              <Skeleton class="h-4 w-full" />
              <Skeleton class="h-4 w-2/3" />
            </div>
            <div class="space-y-6 pt-8">
              {#each Array(3) as _}
                <div class="space-y-3">
                  <Skeleton class="h-6 w-1/4" />
                  <Skeleton class="h-4 w-full" />
                  <Skeleton class="h-4 w-5/6" />
                </div>
              {/each}
            </div>
          </div>
        </div>

      {:else if previewProfile}
        <div class="relative">
          {#if loading}
            <div class="absolute inset-0 bg-background/60 backdrop-blur-[2px] rounded-xl z-10 flex items-center justify-center pointer-events-none">
              <div class="flex items-center gap-2 text-sm font-medium text-primary bg-background border rounded-lg px-4 py-2 shadow-lg">
                <Sparkles class="w-4 h-4 animate-pulse" />
                Enhancing with AI…
              </div>
            </div>
          {/if}
          <div class="bg-muted/30 p-4 sm:p-8 rounded-xl border shadow-inner transition-opacity duration-300 {loading ? 'opacity-60' : 'opacity-100'}">
            <div class="border rounded-lg overflow-hidden bg-white dark:bg-zinc-950/40 print:bg-white print:border-0 print:shadow-none shadow-xl mx-auto max-w-212.5 transition-colors">
              <CvPreview profile={previewProfile} />
            </div>
          </div>
        </div>

      {:else}
        <Card class="border-dashed border-2 bg-muted/30 min-h-64 flex items-center">
          <CardContent class="w-full">
            <EmptyState
              icon={FileText}
              title="CV preview will appear here"
              description="Set up your profile and click Generate to see your CV."
            />
          </CardContent>
        </Card>
      {/if}
    </div>

  </div>
</div>

<style>
  @media print {
    :global(header), :global(nav) {
      display: none !important;
    }
  }
</style>
