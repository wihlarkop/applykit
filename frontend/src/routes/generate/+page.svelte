<script lang="ts">
  import { activeProfile } from '$lib/activeProfile.svelte';
  import { generateCv, generateCvPdf, getProfile } from '$lib/api';
  import CvPreview from '$lib/components/CvPreview.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import PageHeader from '$lib/components/PageHeader.svelte';
  import { Button } from '$lib/components/ui/button';
  import { Card, CardContent } from '$lib/components/ui/card';
  import { Label } from '$lib/components/ui/label';
  import { Skeleton } from '$lib/components/ui/skeleton';
  import { Textarea } from '$lib/components/ui/textarea';
  import { toastState } from '$lib/toast.svelte';
  import type { ProfileData } from '$lib/types';
  import { errorMessage } from '$lib/utils';
  import { Download, FileText, Lock, Printer, Sparkles, UserRoundPen } from '@lucide/svelte';
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
     ((activeProfileData?.work_experience.length ?? 0) === 0 &&
      (activeProfileData?.skills.length ?? 0) === 0 &&
      (activeProfileData?.education.length ?? 0) === 0))
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
      .catch(() => { toastState.error('Failed to load profile data.'); })
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
    } catch (e: unknown) {
      toastState.error(`Generation failed: ${errorMessage(e)}`);
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
    } catch (e: unknown) {
      toastState.error(`Download failed: ${errorMessage(e)}`);
    } finally {
      downloading = false;
    }
  }

  function handlePrintCv() {
    if (!profile) return;
    const printWindow = window.open('', '_blank');
    if (!printWindow) {
      toastState.error('Please allow popups to print');
      return;
    }
    
    const p = profile;
    const contactParts = [p.email, p.phone, p.location, p.linkedin, p.github, p.portfolio].filter(Boolean);
    const contactsHtml = contactParts.map(c => `<span>${c}</span>`).join('<span style="margin:0 8px;color:#6b7280">|</span>');
    
    let html = `<div style="font-family:ui-sans-serif,system-ui,sans-serif;font-size:13px;line-height:1.5;color:#000;width:210mm;margin:0 auto;padding:20mm;background:#fff">
      <div style="text-align:center;margin-bottom:16px">
        <h1 style="font-size:24px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;margin:0 0 4px">${p.name}</h1>
        <div style="font-size:12px;color:#6b7280;display:flex;justify-content:center;flex-wrap:wrap;gap:4px 12px;margin-top:4px">${contactsHtml}</div>
      </div>`;
    
    if (p.summary) {
      html += `<section style="margin-bottom:16px">
        <h2 style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;border-bottom:1px solid #d1d5db;padding-bottom:2px;margin-bottom:8px">Summary</h2>
        <p style="color:#4b5563;margin:0">${p.summary}</p></section>`;
    }
    
    if (p.work_experience.length) {
      html += `<section style="margin-bottom:16px">
        <h2 style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;border-bottom:1px solid #d1d5db;padding-bottom:2px;margin-bottom:8px">Experience</h2>`;
      p.work_experience.forEach(w => {
        html += `<div style="margin-bottom:12px">
          <div style="display:flex;justify-content:space-between;align-items:baseline"><span style="font-weight:600">${w.role}</span><span style="font-size:12px;color:#6b7280">${w.start_date} – ${w.end_date ?? 'Present'}</span></div>
          <div style="font-size:12px;color:#6b7280;margin-bottom:4px">${w.company}</div>
          <ul style="margin:0;padding-left:16px">${w.bullets.map(b => `<li style="margin-bottom:2px">${b}</li>`).join('')}</ul></div>`;
      });
      html += `</section>`;
    }
    
    if (p.education.length) {
      html += `<section style="margin-bottom:16px">
        <h2 style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;border-bottom:1px solid #d1d5db;padding-bottom:2px;margin-bottom:8px">Education</h2>`;
      p.education.forEach(e => {
        html += `<div style="margin-bottom:8px">
          <div style="display:flex;justify-content:space-between;align-items:baseline"><span style="font-weight:600">${e.degree} in ${e.field}</span><span style="font-size:12px;color:#6b7280">${e.start_date} – ${e.end_date ?? 'Present'}</span></div>
          <div style="font-size:12px;color:#6b7280">${e.institution}</div></div>`;
      });
      html += `</section>`;
    }
    
    if (p.skills.length) {
      html += `<section style="margin-bottom:16px">
        <h2 style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;border-bottom:1px solid #d1d5db;padding-bottom:2px;margin-bottom:8px">Skills</h2>
        <p style="color:#4b5563;margin:0">${p.skills.join(' · ')}</p></section>`;
    }
    
    if (p.projects.length) {
      html += `<section style="margin-bottom:16px">
        <h2 style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;border-bottom:1px solid #d1d5db;padding-bottom:2px;margin-bottom:8px">Projects</h2>`;
      p.projects.forEach(proj => {
        html += `<div style="margin-bottom:8px">
          <div style="display:flex;justify-content:space-between;align-items:baseline"><span style="font-weight:600">${proj.name}</span>${proj.link ? `<a href="${proj.link}" style="font-size:12px;color:#2563eb;text-decoration:none">${proj.link}</a>` : ''}</div>
          <p style="color:#4b5563;margin:4px 0 0">${proj.description}</p>
          ${proj.tech_stack.length ? `<p style="font-size:12px;color:#6b7280;margin:2px 0 0">${proj.tech_stack.join(', ')}</p>` : ''}</div>`;
      });
      html += `</section>`;
    }
    
    if (p.certifications && p.certifications.length) {
      html += `<section style="margin-bottom:16px">
        <h2 style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;border-bottom:1px solid #d1d5db;padding-bottom:2px;margin-bottom:8px">Certifications</h2>`;
      p.certifications.forEach(c => {
        html += `<div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px">
          <span>${c.name} — <span style="color:#6b7280">${c.issuer}</span></span>
          <span style="font-size:12px;color:#6b7280">${c.date}</span></div>`;
      });
      html += `</section>`;
    }
    
    html += `</div>`;
    
    printWindow.document.write(`<!DOCTYPE html><html><head><title>Print CV</title><meta charset="utf-8"><style>
      @page { size: A4; margin: 0; }
      @page { @top-left { content: ""; } @top-right { content: ""; } @bottom-left { content: ""; } @bottom-right { content: ""; } }
      body { margin: 0; padding: 0; background: #fff; }
      @media print { body { print-color-adjust: exact; -webkit-print-color-adjust: exact; } }
    </style></head><body>${html}</body></html>`);
    printWindow.document.close();
    printWindow.onload = () => {
      setTimeout(() => { printWindow.focus(); printWindow.print(); printWindow.close(); }, 500);
    };
    printWindow.onerror = () => {
      setTimeout(() => { printWindow.focus(); printWindow.print(); printWindow.close(); }, 500);
    };
  }
</script>


<div class="space-y-8 max-w-4xl pb-10 relative">
  <PageHeader
    title="Generate CV"
    subtitle="Create an ATS-optimized CV tailored from your profile."
  >
    {#snippet actions()}
      {#if profile}
        <Button variant="outline" size="sm" onclick={handlePrintCv} class="shadow-sm hidden sm:flex">
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
    {/snippet}
  </PageHeader>

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
    {:else}
      <Card class="border-dashed border-2 bg-muted/30">
        <CardContent>
          <EmptyState
            icon={FileText}
            title="Ready to generate your CV?"
            description='Click the "Generate ATS CV" button above to dynamically create a beautifully formatted resume. If your API key is configured, AI will enhance your bullet points for ATS systems.'
          />
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
          class="border rounded-lg overflow-hidden bg-white dark:bg-zinc-950/40 print:bg-white print:border-0 print:shadow-none shadow-xl mx-auto max-w-212.5 transition-colors"
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
