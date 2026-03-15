<script lang="ts">
  import { generateCoverLetter, generateCoverLetterPdf, getProfile } from '$lib/api';
  import { activeProfile } from '$lib/activeProfile.svelte';
  import { Button } from '$lib/components/ui/button';
  import { Textarea } from '$lib/components/ui/textarea';
  import { Label } from '$lib/components/ui/label';
  import { Input } from '$lib/components/ui/input';
  import { Card, CardContent } from '$lib/components/ui/card';
  import { Mail, Sparkles, Copy, Check, Download, Printer, Lock, UserRoundPen } from '@lucide/svelte';
  import { toastState } from '$lib/toast.svelte';
  import { Skeleton } from '$lib/components/ui/skeleton';
  import CoverLetterPreview from '$lib/components/CoverLetterPreview.svelte';
  import type { ProfileData } from '$lib/types';

  let { data } = $props();
  const isOnboarded = $derived(data.isOnboarded);

  let companyName = $state('');
  let jobDescription = $state('');
  let extraContext = $state('');
  let coverLetterText = $state('');
  let loading = $state(false);
  let downloading = $state(false);
  let copied = $state(false);
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
    coverLetterText = '';
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
    if (!jobDescription.trim()) {
      toastState.error('Please enter a job description.');
      return;
    }
    loading = true;
    coverLetterText = '';
    try {
      const res = await generateCoverLetter({
        profile_id: ap.id,
        job_description: jobDescription,
        extra_context: extraContext,
        company_name: companyName.trim() || null,
      });
      coverLetterText = res.cover_letter_text;
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
      const html = `<div style="font-family:sans-serif;font-size:13px;line-height:1.6;padding:40px;white-space:pre-wrap">${coverLetterText}</div>`;
      const blob = await generateCoverLetterPdf({ html });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'cover-letter.pdf';
      a.click();
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
        <p class="text-xs text-muted-foreground mt-0.5">Write a perfectly tailored cover letter instantly based on a job description.</p>
      </div>
    </div>
  </div>

  <div class="grid lg:grid-cols-[1fr_1.5fr] gap-8 items-start">
    <div class="sticky top-6 z-10 pt-2 pb-6 max-h-[calc(100vh-3rem)] overflow-y-auto">
      <Card class="shadow-sm">
        <CardContent class="p-6 space-y-6">
          <div class="space-y-3">
            <Label for="company">Company Name <span class="text-muted-foreground text-xs">(optional)</span></Label>
            <Input
              id="company"
              bind:value={companyName}
              placeholder="e.g. Acme Corp"
            />
          </div>

          <div class="space-y-2">
            <Label for="jd" class="font-semibold text-base">Job Description *</Label>
            <p class="text-xs text-muted-foreground mb-2">Paste the full job posting requirements here.</p>
            <Textarea
              id="jd"
              bind:value={jobDescription}
              placeholder="We are looking for a Senior Software Engineer with 5+ years of experience in React and Node.js..."
              rows={12}
              class="bg-background/50 resize-y max-h-[40vh]"
            />
          </div>

          <div class="space-y-2">
            <Label for="extra" class="font-semibold text-base">What to emphasize <span class="text-muted-foreground text-xs font-normal">(optional)</span></Label>
            <p class="text-xs text-muted-foreground mb-2">Any specific things to highlight or tone preferences?</p>
            <Textarea
              id="extra"
              bind:value={extraContext}
              placeholder="Focus heavily on my open source contributions. Make the tone enthusiastic."
              rows={4}
              class="bg-background/50 resize-y max-h-[20vh]"
            />
          </div>

          {#if activeProfile.current}
            <div class="flex items-center gap-2 px-3 py-2 rounded-lg bg-muted/50 border text-sm">
              <span class="text-base leading-none">{activeProfile.current.icon}</span>
              <span class="font-medium">{activeProfile.current.label}</span>
              <span class="text-muted-foreground text-xs">— writing as this profile</span>
            </div>
          {/if}

          <Button onclick={handleGenerate} disabled={loading || !jobDescription.trim() || !isOnboarded || isProfileEmpty || profileLoading} class="w-full shadow-md" size="lg">
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

    <div class="space-y-4">
      {#if !coverLetterText && !loading}
        {#if isProfileEmpty}
          <Card class="border-dashed border-2 border-yellow-400/60 bg-yellow-50/30 dark:bg-yellow-900/10 h-full min-h-[500px] flex items-center justify-center">
            <CardContent class="flex flex-col items-center justify-center p-8 text-center">
              <div class="w-16 h-16 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400 rounded-full flex items-center justify-center mb-4">
                <UserRoundPen class="w-8 h-8" />
              </div>
              <h3 class="text-lg font-bold mb-2">Profile is empty</h3>
              <p class="text-muted-foreground text-sm max-w-[260px] mb-5">
                Add your work experience, education, or skills to <strong>{activeProfile.current?.label ?? 'this profile'}</strong> before writing a cover letter.
              </p>
              <Button href="/profile" variant="default" size="sm">Fill in my profile</Button>
            </CardContent>
          </Card>
        {:else}
          <Card class="border-dashed border-2 bg-muted/30 h-full min-h-[500px] flex items-center justify-center">
            <CardContent class="flex flex-col items-center justify-center p-8 text-center">
              <div class="w-16 h-16 bg-primary/10 text-primary rounded-full flex items-center justify-center mb-4">
                <Mail class="w-8 h-8 opacity-50" />
              </div>
              <h3 class="text-lg font-bold mb-2">No letter generated yet</h3>
              <p class="text-muted-foreground text-sm max-w-[250px]">
                Fill out the job description on the left and click generate to create your tailored cover letter.
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
          <Card class="shadow-lg border-primary/10 overflow-hidden">
            <CardContent class="p-8 space-y-6 bg-white dark:bg-zinc-950/40 transition-colors min-h-[500px]">
              <div class="space-y-3">
                <Skeleton class="h-4 w-1/4" />
                <Skeleton class="h-4 w-1/3" />
              </div>
              <div class="pt-4 space-y-4">
                <Skeleton class="h-6 w-1/4 mb-4" />
                {#each Array(4) as _}
                  <div class="space-y-2">
                    <Skeleton class="h-4 w-full" />
                    <Skeleton class="h-4 w-full" />
                    <Skeleton class="h-4 w-5/6" />
                  </div>
                {/each}
              </div>
            </CardContent>
          </Card>
        </div>
      {/if}

      {#if coverLetterText}
        <div class="animate-in fade-in slide-in-from-right-4 duration-500 space-y-3">
          <div class="flex items-center justify-between px-1">
            <h2 class="font-semibold text-lg flex items-center gap-2">
              <Sparkles class="w-5 h-5 text-amber-500" />
              Generated Letter
            </h2>
            <div class="flex gap-2">
              <Button variant="outline" size="sm" onclick={handleCopy} class="shadow-sm">
                {#if copied}
                  <Check class="w-4 h-4 mr-1 text-green-500" /> Copied
                {:else}
                  <Copy class="w-4 h-4 mr-1" /> Copy
                {/if}
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
    :global(header), :global(nav) {
      display: none !important;
    }
  }
</style>
