<script lang="ts">
  import { User, SparklesIcon, ChevronDown, Check, Loader2, RefreshCw } from '@lucide/svelte';
  import { Label } from '$lib/components/ui/label';
  import { Input } from '$lib/components/ui/input';
  import { Textarea } from '$lib/components/ui/textarea';
  import { Button } from '$lib/components/ui/button';
  import type { ProfileData } from '$lib/types';
  import { activeProfile } from '$lib/activeProfile.svelte';
  import { generateSummaryStream } from '$lib/api';
  import { consumeStream } from '$lib/stream';
  import { toastState } from '$lib/toast.svelte';
  import { errorMessage } from '$lib/utils';

  interface Props {
    profile: ProfileData;
  }
  let { profile = $bindable() }: Props = $props();

  // Generate Summary
  let showSummaryGen = $state(false);
  let summaryTone = $state<'professional' | 'enthusiastic' | 'concise' | 'creative'>('professional');
  let summaryGenerating = $state(false);
  let summaryPreview = $state('');
  let summaryContext = $state('');

  const SUMMARY_TONES = [
    { id: 'professional' as const, label: 'Professional', desc: 'Formal & polished' },
    { id: 'enthusiastic' as const, label: 'Enthusiastic', desc: 'Energetic & passionate' },
    { id: 'concise' as const, label: 'Concise', desc: 'Short & direct' },
    { id: 'creative' as const, label: 'Creative', desc: 'Distinctive & memorable' },
  ];

  async function generateSummary() {
    const ap = activeProfile.current;
    if (!ap) return;
    summaryGenerating = true;
    summaryPreview = '';
    try {
      const res = await generateSummaryStream(ap.id, summaryTone, summaryContext || undefined);
      if (!res.ok) throw new Error('Generation failed');
      await consumeStream(res, {
        onChunk: (text) => { summaryPreview += text; },
        onDone: () => {},
        onError: (msg) => { toastState.error(msg); },
      });
    } catch (e: unknown) {
      toastState.error(`Generation failed: ${errorMessage(e)}`);
    } finally {
      summaryGenerating = false;
    }
  }

  function applySummary() {
    profile.summary = summaryPreview;
    summaryPreview = '';
    showSummaryGen = false;
    toastState.success('Summary applied! Remember to save.');
  }
</script>

<style>
  @keyframes shimmer-border {
    0% { border-color: hsl(var(--primary) / 0.2); box-shadow: 0 0 0px hsl(var(--primary) / 0); }
    50% { border-color: hsl(var(--primary) / 0.6); box-shadow: 0 0 15px hsl(var(--primary) / 0.2); }
    100% { border-color: hsl(var(--primary) / 0.2); box-shadow: 0 0 0px hsl(var(--primary) / 0); }
  }
  :global(.ai-shimmer) {
    animation: shimmer-border 2s infinite ease-in-out;
  }
</style>

<div class="grid lg:grid-cols-4 gap-12 text-left">
  <div class="space-y-2">
    <h2 class="text-xl font-bold tracking-tight flex items-center gap-3 text-foreground">
      <div class="p-2 bg-primary/10 rounded-lg">
        <User class="w-5 h-5 text-primary" />
      </div>
      Personal Info
    </h2>
    <p class="text-sm text-muted-foreground leading-relaxed">Your professional identity and contact details.</p>
  </div>
  <div class="lg:col-span-3 space-y-8">
    <div class="grid gap-6 sm:grid-cols-2 p-6 rounded-2xl border border-border/50 bg-muted/5 shadow-sm">
      <div class="space-y-2">
        <Label for="name" class="text-xs font-bold uppercase tracking-wider text-muted-foreground">Full Name *</Label>
        <Input id="name" bind:value={profile.name} placeholder="Jane Doe" class="bg-background h-11 text-base border-muted-foreground/20 focus:border-primary transition-all" />
      </div>
      <div class="space-y-2">
        <Label for="email" class="text-xs font-bold uppercase tracking-wider text-muted-foreground">Email *</Label>
        <Input id="email" type="email" bind:value={profile.email} placeholder="jane@example.com" class="bg-background h-11 text-base border-muted-foreground/20 focus:border-primary transition-all" />
      </div>
      <div class="space-y-2">
        <Label for="phone" class="text-xs font-bold uppercase tracking-wider text-muted-foreground">Phone</Label>
        <Input id="phone" bind:value={profile.phone} placeholder="+1 234 567 8900" class="bg-background h-11 text-base border-muted-foreground/20 focus:border-primary transition-all" />
      </div>
      <div class="space-y-2">
        <Label for="location" class="text-xs font-bold uppercase tracking-wider text-muted-foreground">Location</Label>
        <Input id="location" bind:value={profile.location} placeholder="City, Country" class="bg-background h-11 text-base border-muted-foreground/20 focus:border-primary transition-all" />
      </div>
      <div class="space-y-2">
        <Label for="linkedin" class="text-xs font-bold uppercase tracking-wider text-muted-foreground">LinkedIn</Label>
        <Input id="linkedin" bind:value={profile.linkedin} placeholder="linkedin.com/in/username" class="bg-background h-11 text-base border-muted-foreground/20 focus:border-primary transition-all" />
      </div>
      <div class="space-y-2">
        <Label for="github" class="text-xs font-bold uppercase tracking-wider text-muted-foreground">GitHub</Label>
        <Input id="github" bind:value={profile.github} placeholder="github.com/username" class="bg-background h-11 text-base border-muted-foreground/20 focus:border-primary transition-all" />
      </div>
      <div class="space-y-2 sm:col-span-2">
        <Label for="portfolio" class="text-xs font-bold uppercase tracking-wider text-muted-foreground">Portfolio / Personal Website</Label>
        <Input id="portfolio" bind:value={profile.portfolio} placeholder="yoursite.com" class="bg-background h-11 text-base border-muted-foreground/20 focus:border-primary transition-all" />
      </div>
    </div>
    <div class="space-y-2 sm:col-span-2">
      <div class="flex items-center justify-between">
        <Label for="summary">Professional Summary</Label>
        <button
          type="button"
          onclick={() => { showSummaryGen = !showSummaryGen; summaryPreview = ''; }}
          class="inline-flex items-center gap-1.5 text-xs font-medium text-primary hover:text-primary/80 transition-colors"
        >
          <SparklesIcon class="w-3.5 h-3.5" />
          Generate with AI
          <ChevronDown class="w-3 h-3 transition-transform {showSummaryGen ? 'rotate-180' : ''}" />
        </button>
      </div>

      {#if showSummaryGen}
        <div class="rounded-xl border border-primary/20 bg-primary/5 p-4 space-y-4 animate-in fade-in slide-in-from-top-2 duration-200">
          <!-- Tone selector -->
          <div class="space-y-2">
            <p class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Choose tone</p>
            <div class="grid grid-cols-2 gap-2">
              {#each SUMMARY_TONES as t}
                <button
                  type="button"
                  onclick={() => summaryTone = t.id}
                  class="flex flex-col items-start px-3 py-2.5 rounded-lg border text-left transition-all duration-150
                         {summaryTone === t.id
                           ? 'bg-primary text-primary-foreground border-primary shadow-sm'
                           : 'bg-background border-border hover:border-primary/40 hover:bg-primary/5'}"
                >
                  <span class="text-sm font-semibold">{t.label}</span>
                  <span class="text-[11px] {summaryTone === t.id ? 'text-primary-foreground/70' : 'text-muted-foreground'}">{t.desc}</span>
                </button>
              {/each}
            </div>
          </div>

          <!-- Extra context -->
          <div class="space-y-1.5">
            <label for="summaryContext" class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Extra context <span class="font-normal normal-case tracking-normal">(optional)</span>
            </label>
            <textarea
              id="summaryContext"
              bind:value={summaryContext}
              placeholder="e.g. Emphasize my leadership experience, I'm transitioning from frontend to full-stack, I have 8 years total experience..."
              rows={2}
              class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground/50 resize-none focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
            ></textarea>
          </div>

          <!-- Generate button -->
          <Button
            onclick={generateSummary}
            disabled={summaryGenerating}
            size="sm"
            class="w-full"
          >
            {#if summaryGenerating}
              <Loader2 class="w-4 h-4 mr-2 animate-spin" />
              Generating…
            {:else}
              <SparklesIcon class="w-4 h-4 mr-2" />
              Generate Summary
            {/if}
          </Button>

          <!-- Preview -->
          {#if summaryPreview || summaryGenerating}
            <div class="space-y-2">
              <p class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Preview</p>
              <div class="min-h-20 p-3 rounded-lg bg-background border border-border text-sm leading-relaxed text-foreground whitespace-pre-wrap">
                {summaryPreview}{#if summaryGenerating}<span class="inline-block w-1.5 h-4 bg-primary ml-0.5 animate-pulse rounded-sm"></span>{/if}
              </div>
              {#if summaryPreview && !summaryGenerating}
                <div class="flex gap-2">
                  <Button onclick={applySummary} size="sm" class="flex-1">
                    <Check class="w-4 h-4 mr-1.5" />
                    Apply to Profile
                  </Button>
                  <Button onclick={generateSummary} variant="outline" size="sm">
                    <RefreshCw class="w-4 h-4 mr-1.5" />
                    Regenerate
                  </Button>
                </div>
              {/if}
            </div>
          {/if}
        </div>
      {/if}
      <Textarea 
        id="summary" 
        bind:value={profile.summary} 
        placeholder="Brief professional summary explaining who you are and what you do…" 
        rows={6} 
        class="bg-background transition-all duration-500 resize-y text-sm sm:text-base p-5 rounded-2xl border-muted-foreground/20 focus:border-primary {summaryGenerating ? 'ai-shimmer bg-primary/5' : ''}" 
      />
    </div>
  </div>
</div>
