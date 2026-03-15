<script lang="ts">
  import { generateCv, generateCvPdf, getProfile } from '$lib/api';
  import { activeProfile } from '$lib/activeProfile.svelte';
  import CvPreview from '$lib/components/CvPreview.svelte';
  import { Button } from '$lib/components/ui/button';
  import { Card, CardContent } from '$lib/components/ui/card';
  import { Textarea } from '$lib/components/ui/textarea';
  import { Label } from '$lib/components/ui/label';
  import { Sparkles, Download, Printer, FileText, Lock, UserRoundPen } from '@lucide/svelte';
  import { toastState } from '$lib/toast.svelte';
  import { Skeleton } from '$lib/components/ui/skeleton';
  import type { ProfileData } from '$lib/types';
  import confetti from 'canvas-confetti';

  let { data } = $props();
  const isOnboarded = $derived(data.isOnboarded);

  let profile: ProfileData | null = $state(null);
  let enhanced = $state(false);
  let loading = $state(false);
  let downloading = $state(false);
  let previewEl: HTMLDivElement | undefined = $state(undefined);
  let jobDescription = $state('');
  let activeProfileData: ProfileData | null = $state(null);
  let profileLoading = $state(true);

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
    profile = null;
    enhanced = false;
    profileLoading = true;
    if (!ap) { profileLoading = false; return; }
    getProfile(ap.id)
      .then(p => { activeProfileData = p; })
      .catch(() => {})
      .finally(() => { profileLoading = false; });
  });

  async function handleGenerate() {
    const ap = activeProfile.current;
    if (!ap) return;
    loading = true;
    profile = null;
    try {
      const res = await generateCv({ profile_id: ap.id, enhance: true, job_description: jobDescription.trim() || null });
      profile = res.profile;
      enhanced = res.enhanced;
      toastState.success('CV Generated Successfully!');
      confetti({
        particleCount: 150,
        spread: 70,
        origin: { y: 0.6 },
        colors: ['#3b82f6', '#8b5cf6', '#10b981']
      });
    } catch (e: any) {
      toastState.error(`Generation failed: ${e.message}`);
    } finally {
      loading = false;
    }
  }

  async function handleDownloadPdf() {
    if (!previewEl) return;
    downloading = true;
    try {
      const html = previewEl.innerHTML;
      const blob = await generateCvPdf({ html });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'cv.pdf';
      a.click();
      URL.revokeObjectURL(url);
      toastState.success('PDF Downloaded!');
    } catch (e: any) {
      toastState.error(`Download failed: ${e.message}`);
    } finally {
      downloading = false;
    }
  }

  function handlePrint() {
    window.print();
  }
</script>

<div class="space-y-8 max-w-4xl pb-10 relative">
  <!-- Sticky Header -->
  <div class="sticky top-0 z-50 bg-background/80 backdrop-blur-md border-b border-border -mx-4 px-4 py-4 mb-8">
    <div class="flex items-start sm:items-center justify-between flex-col sm:flex-row gap-4 max-w-4xl mx-auto">
      <div>
        <h1 class="text-2xl font-bold flex items-center gap-2">
          <Sparkles class="w-6 h-6 text-primary" />
          Generate CV
        </h1>
        <p class="text-xs text-muted-foreground mt-0.5">Create an ATS-optimized CV tailored from your profile.</p>
      </div>
      <div class="flex items-center gap-3 self-end sm:self-auto">
        {#if profile}
          <Button variant="outline" size="sm" onclick={handlePrint} class="shadow-sm hidden sm:flex">
            <Printer class="w-4 h-4 mr-2" /> Print
          </Button>
          <Button variant="outline" size="sm" onclick={handleDownloadPdf} disabled={downloading} class="shadow-sm">
            <Download class="w-4 h-4 mr-2" />
            {downloading ? 'Downloading…' : 'Download PDF'}
          </Button>
        {/if}
        <Button onclick={handleGenerate} disabled={loading || !isOnboarded || isProfileEmpty || profileLoading} size="sm" class="shadow-md h-9">
          {#if !isOnboarded}
            <Lock class="w-4 h-4 mr-2" /> Locked
          {:else}
            <Sparkles class="w-4 h-4 mr-2 {loading ? 'animate-pulse' : ''}" />
            {loading ? 'Generating…' : 'Generate ATS CV'}
          {/if}
        </Button>
      </div>
    </div>
  </div>


  <!-- Job Description + Profile Context -->
  <div class="grid sm:grid-cols-[1fr_auto] gap-4 items-start">
    <div class="space-y-2">
      <Label for="jd" class="font-semibold">Job Description <span class="text-muted-foreground text-xs font-normal">(optional — helps AI tailor your CV)</span></Label>
      <Textarea
        id="jd"
        bind:value={jobDescription}
        placeholder="Paste the job posting here to get a CV tailored to this specific role…"
        rows={4}
        class="bg-background/50 resize-y max-h-[30vh]"
      />
    </div>
    {#if activeProfile.current}
      <div class="flex items-center gap-2 sm:mt-7 px-3 py-2 rounded-lg bg-muted/50 border text-sm shrink-0">
        <span class="text-base leading-none">{activeProfile.current.icon}</span>
        <span class="font-medium">{activeProfile.current.label}</span>
      </div>
    {/if}
  </div>

  {#if !profile && !loading}
    {#if isProfileEmpty}
      <Card class="border-dashed border-2 border-yellow-400/60 bg-yellow-50/30 dark:bg-yellow-900/10">
        <CardContent class="flex flex-col items-center justify-center py-16 text-center">
          <div class="w-16 h-16 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400 rounded-full flex items-center justify-center mb-4">
            <UserRoundPen class="w-8 h-8" />
          </div>
          <h3 class="text-xl font-bold mb-2">Profile is empty</h3>
          <p class="text-muted-foreground max-w-sm mx-auto mb-5">
            Add your work experience, education, or skills to <strong>{activeProfile.current?.label ?? 'this profile'}</strong> before generating a CV.
          </p>
          <Button href="/profile" variant="default">Fill in my profile</Button>
        </CardContent>
      </Card>
    {:else}
      <Card class="border-dashed border-2 bg-muted/30">
        <CardContent class="flex flex-col items-center justify-center py-16 text-center">
          <div class="w-16 h-16 bg-primary/10 text-primary rounded-full flex items-center justify-center mb-4">
            <FileText class="w-8 h-8" />
          </div>
          <h3 class="text-xl font-bold mb-2">Ready to generate your CV?</h3>
          <p class="text-muted-foreground max-w-md mx-auto">
            Click the "Generate ATS CV" button above to dynamically create a beautifully formatted resume. If your API key is configured, AI will enhance your bullet points for ATS systems.
          </p>
        </CardContent>
      </Card>
    {/if}
  {/if}

  {#if loading}
    <div class="space-y-4">
      <div class="flex items-center gap-2 text-sm bg-primary/5 p-3 rounded-lg border border-primary/20 animate-pulse">
        <Sparkles class="w-4 h-4 text-primary" />
        <span class="text-primary font-medium">AI is crafting your tailored CV...</span>
      </div>
      <div class="bg-muted/30 p-4 sm:p-8 rounded-xl border shadow-inner">
        <div class="bg-white dark:bg-zinc-950/40 p-12 space-y-8 rounded-lg shadow-xl mx-auto max-w-[850px] min-h-[600px] transition-colors">
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
    </div>
  {/if}

  {#if profile}
    <div class="animate-in fade-in slide-in-from-bottom-4 duration-500 space-y-4">
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

      <div class="bg-muted/30 p-4 sm:p-8 rounded-xl border shadow-inner">
        <div
          class="border rounded-lg overflow-hidden bg-white dark:bg-zinc-950/40 print:bg-white print:border-0 print:shadow-none shadow-xl mx-auto max-w-[850px] transition-colors"
          bind:this={previewEl}
        >
          <CvPreview {profile} />
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  @media print {
    :global(header), :global(nav) {
      display: none !important;
    }
  }
</style>
