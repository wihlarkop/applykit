<script lang="ts">
  import { Building2, Plus, Trash2, SparklesIcon, ChevronDown, Check, Loader2, RefreshCw } from '@lucide/svelte';
  import { Label } from '$lib/components/ui/label';
  import { Input } from '$lib/components/ui/input';
  import { Textarea } from '$lib/components/ui/textarea';
  import { Button } from '$lib/components/ui/button';
  import type { ProfileData, WorkExperience } from '$lib/types';
  import { activeProfile } from '$lib/activeProfile.svelte';
  import { generateBulletsStream } from '$lib/api';
  import { consumeStream } from '$lib/stream';
  import { toastState } from '$lib/toast.svelte';
  import { errorMessage } from '$lib/utils';

  interface Props {
    profile: ProfileData;
  }
  let { profile = $bindable() }: Props = $props();

  function addWork() {
    profile.work_experience = [
      ...profile.work_experience,
      { company: '', role: '', start_date: '', end_date: null, bullets: [] },
    ];
  }

  function removeWork(i: number) {
    profile.work_experience = profile.work_experience.filter((_, idx) => idx !== i);
  }

  function workBulletsText(w: WorkExperience) {
    return w.bullets.map(b => `- ${b}`).join('\n');
  }

  function setWorkBullets(i: number, text: string) {
    profile.work_experience[i].bullets = text
      .split('\n')
      .map(s => s.replace(/^[-•*]\s*/, '').trim())
      .filter(Boolean);
  }

  // Enhance Bullets
  let activeBulletIdx = $state<number | null>(null);
  let bulletMode = $state<'improve' | 'reorganize'>('improve');
  let bulletGenerating = $state(false);
  let bulletPreview = $state('');
  let bulletContext = $state('');

  const BULLET_MODES = [
    { id: 'improve' as const, label: 'Improve Writing', desc: 'Stronger verbs & outcomes' },
    { id: 'reorganize' as const, label: 'Sort by Impact', desc: 'Most impressive first' },
  ];

  async function generateBullets(i: number) {
    const ap = activeProfile.current;
    if (!ap) return;
    const work = profile.work_experience[i];
    bulletGenerating = true;
    bulletPreview = '';
    try {
      const res = await generateBulletsStream(ap.id, work.company, work.role, work.bullets, bulletMode, bulletContext || undefined);
      if (!res.ok) throw new Error('Generation failed');
      await consumeStream(res, {
        onChunk: (text) => { bulletPreview += text; },
        onDone: () => {},
        onError: (msg) => { toastState.error(msg); },
        transformChunk: (chunk) => chunk.replaceAll('<NL>', '\n'),
      });
    } catch (e: unknown) {
      toastState.error(`Generation failed: ${errorMessage(e)}`);
    } finally {
      bulletGenerating = false;
    }
  }

  function applyBullets(i: number) {
    const lines = bulletPreview
      .split('\n')
      .map(l => l.trim())
      .filter(Boolean)
      .join('\n');
    setWorkBullets(i, lines);
    bulletPreview = '';
    activeBulletIdx = null;
    toastState.success('Bullets applied! Remember to save.');
  }

  function toggleBulletGen(i: number) {
    if (activeBulletIdx === i) {
      activeBulletIdx = null;
      bulletPreview = '';
      bulletContext = '';
    } else {
      activeBulletIdx = i;
      bulletPreview = '';
      bulletContext = '';
    }
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

<div class="grid lg:grid-cols-12 gap-x-12 gap-y-10 text-left">
  <!-- Left Column (Title & Add Action) -->
  <div class="lg:col-span-4 space-y-6">
    <div class="space-y-2">
      <h2 class="text-xl font-bold tracking-tight flex items-center gap-3 text-foreground">
        <div class="p-2 bg-primary/10 rounded-lg">
          <Building2 class="w-5 h-5 text-primary" />
        </div>
        Experience
      </h2>
      <p class="text-sm text-muted-foreground leading-relaxed">Your professional journey and key achievements.</p>
    </div>
    
    <div class="hidden lg:block pt-4">
      <Button 
        onclick={addWork} 
        variant="outline" 
        size="lg" 
        class="w-full h-12 px-6 font-bold border-dashed border-2 hover:border-primary hover:bg-primary/5 transition-all rounded-xl shadow-sm hover:shadow-md group"
      >
        <Plus class="w-5 h-5 mr-2 transition-transform group-hover:rotate-90" />
        Add Work Exp
      </Button>
    </div>
  </div>

  <!-- Right Column (Entry Cards) -->
  <div class="lg:col-span-8 space-y-10">
    {#if profile.work_experience.length === 0}
      <div class="text-center py-10 text-muted-foreground text-sm border-2 border-dashed rounded-xl bg-muted/20">
        No work experience added yet.
      </div>
    {:else}
      {#each profile.work_experience as work, i}
        <div class="relative border border-border/50 rounded-2xl p-6 space-y-8 bg-muted/5 group transition-all hover:bg-muted/10 hover:shadow-sm">
          <div class="absolute right-4 top-4 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button variant="ghost" size="icon" class="h-8 w-8 text-destructive hover:bg-destructive/10" onclick={() => removeWork(i)}>
              <Trash2 class="w-4 h-4" />
            </Button>
          </div>
          
          <div class="grid gap-8">
            <div class="grid gap-6 sm:grid-cols-2">
              <div class="space-y-2 text-left">
                <Label class="text-xs font-bold uppercase tracking-wider text-muted-foreground">Company Name</Label>
                <Input bind:value={work.company} placeholder="e.g. Google" class="bg-background h-11 text-base border-muted-foreground/20 focus:border-primary transition-all" />
              </div>
              <div class="space-y-2 text-left">
                <Label class="text-xs font-bold uppercase tracking-wider text-muted-foreground">Your Role</Label>
                <Input bind:value={work.role} placeholder="e.g. Senior Product Designer" class="bg-background h-11 text-base border-muted-foreground/20 focus:border-primary transition-all" />
              </div>
            </div>
            <div class="grid gap-6 sm:grid-cols-2">
              <div class="space-y-2 text-left">
                <Label class="text-xs font-bold uppercase tracking-wider text-muted-foreground">Start Date</Label>
                <Input bind:value={work.start_date} placeholder="e.g. Jan 2022" class="bg-background h-10 border-muted-foreground/20 focus:border-primary transition-all" />
              </div>
              <div class="space-y-2 text-left">
                <Label class="text-xs font-bold uppercase tracking-wider text-muted-foreground">End Date</Label>
                <Input bind:value={work.end_date} placeholder="Present" class="bg-background h-10 border-muted-foreground/20 focus:border-primary transition-all" />
              </div>
            </div>
          </div>
          <div class="space-y-2 text-left">
            <div class="flex items-center justify-between pr-1">
              <Label class="text-xs font-bold uppercase tracking-wider text-muted-foreground">Key Accomplishments</Label>
              <button
                type="button"
                onclick={() => toggleBulletGen(i)}
                class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary/10 text-[10px] font-bold text-primary hover:bg-primary/20 transition-all uppercase tracking-widest border border-primary/20"
              >
                <SparklesIcon class="w-3 h-3" />
                AI Enhance
                <ChevronDown class="w-3 h-3 transition-transform {activeBulletIdx === i ? 'rotate-180' : ''}" />
              </button>
            </div>
            <Textarea
              value={workBulletsText(work)}
              oninput={(e) => setWorkBullets(i, (e.target as HTMLTextAreaElement).value)}
              placeholder="- Built X that improved Y by Z%"
              rows={5}
              class="bg-background transition-all duration-500 resize-y p-5 text-sm sm:text-base selection:bg-primary/20 rounded-2xl border-muted-foreground/20 focus:border-primary {activeBulletIdx === i && bulletGenerating ? 'ai-shimmer bg-primary/5' : ''}"
            />

            {#if activeBulletIdx === i}
              <div class="rounded-xl border border-primary/20 bg-primary/5 p-4 space-y-4 animate-in fade-in slide-in-from-top-2 duration-200">
                <!-- Mode selector -->
                <div class="space-y-2">
                  <p class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Choose action</p>
                  <div class="grid grid-cols-2 gap-2">
                    {#each BULLET_MODES as m}
                      <button
                        type="button"
                        onclick={() => bulletMode = m.id}
                        class="flex flex-col items-start px-3 py-2.5 rounded-lg border text-left transition-all duration-150
                               {bulletMode === m.id
                                 ? 'bg-primary text-primary-foreground border-primary shadow-sm'
                                 : 'bg-background border-border hover:border-primary/40 hover:bg-primary/5'}"
                      >
                        <span class="text-sm font-semibold">{m.label}</span>
                        <span class="text-[11px] {bulletMode === m.id ? 'text-primary-foreground/70' : 'text-muted-foreground'}">{m.desc}</span>
                      </button>
                    {/each}
                  </div>
                </div>

                <!-- Extra context -->
                <div class="space-y-1.5">
                  <label for="bulletContext" class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Extra context <span class="font-normal normal-case tracking-normal">(optional)</span>
                  </label>
                  <textarea
                    id="bulletContext"
                    bind:value={bulletContext}
                    placeholder="e.g. I also managed a team of 4 engineers, we reduced costs by 30%, I led the migration to Kubernetes..."
                    rows={2}
                    class="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground/50 resize-none focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  ></textarea>
                </div>

                {#if work.bullets.length === 0}
                  <p class="text-xs text-muted-foreground text-center py-1">Add some accomplishments above first.</p>
                {:else}
                  <Button
                    onclick={() => generateBullets(i)}
                    disabled={bulletGenerating}
                    size="sm"
                    class="w-full"
                  >
                    {#if bulletGenerating}
                      <Loader2 class="w-4 h-4 mr-2 animate-spin" />
                      Enhancing…
                    {:else}
                      <SparklesIcon class="w-4 h-4 mr-2" />
                      {bulletMode === 'improve' ? 'Improve Bullets' : 'Sort by Impact'}
                    {/if}
                  </Button>
                {/if}

                {#if bulletPreview || bulletGenerating}
                  <div class="space-y-2">
                    <p class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Preview</p>
                    <div class="min-h-20 p-3 rounded-lg bg-background border border-border text-sm leading-relaxed text-foreground whitespace-pre-wrap font-mono">
                      {bulletPreview}{#if bulletGenerating}<span class="inline-block w-1.5 h-4 bg-primary ml-0.5 animate-pulse rounded-sm"></span>{/if}
                    </div>
                    {#if bulletPreview && !bulletGenerating}
                      <div class="flex gap-2">
                        <Button onclick={() => applyBullets(i)} size="sm" class="flex-1">
                          <Check class="w-4 h-4 mr-1.5" />
                          Apply to Entry
                        </Button>
                        <Button onclick={() => generateBullets(i)} variant="outline" size="sm">
                          <RefreshCw class="w-4 h-4 mr-1.5" />
                          Regenerate
                        </Button>
                      </div>
                    {/if}
                  </div>
                {/if}
              </div>
            {/if}
          </div>
        </div>
      {/each}
    {/if}

    <!-- Mobile-only Add Button (at bottom) -->
    <div class="lg:hidden pt-6 flex justify-center">
      <Button 
        onclick={addWork} 
        variant="outline" 
        size="lg" 
        class="w-full h-12 font-bold border-dashed border-2 hover:border-primary hover:bg-primary/5 rounded-xl transition-all"
      >
        <Plus class="w-5 h-5 mr-2" />
        Add Work Experience
      </Button>
    </div>
  </div>
</div>
