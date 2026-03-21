<script lang="ts">
  import { Award, Plus, X } from '@lucide/svelte';
  import { scale, fade } from 'svelte/transition';
  import { Badge } from '$lib/components/ui/badge';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import type { ProfileData } from '$lib/types';

  interface Props {
    profile: ProfileData;
  }
  let { profile = $bindable() }: Props = $props();

  let skillsText = $state('');

  function commitSkill() {
    const val = skillsText.trim().replace(/,$/, '');
    if (val && !profile.skills.includes(val)) {
      profile.skills = [...profile.skills, val];
      skillsText = '';
    }
  }

  function addSkill(e: KeyboardEvent) {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      commitSkill();
    }
  }

  function removeSkill(skill: string) {
    profile.skills = profile.skills.filter(s => s !== skill);
  }
</script>

<div class="grid lg:grid-cols-4 gap-12 text-left">
  <div class="space-y-2">
    <h2 class="text-xl font-bold tracking-tight flex items-center gap-3 text-foreground">
      <div class="p-2 bg-primary/10 rounded-lg">
        <Award class="w-5 h-5 text-primary" />
      </div>
      Core Skills
    </h2>
    <p class="text-sm text-muted-foreground leading-relaxed">The expertise and tools that define your professional baseline.</p>
  </div>
  <div class="lg:col-span-3">
    <div class="space-y-6 max-w-2xl">
      <!-- Tag list -->
      <div class="min-h-24 p-5 rounded-2xl border border-border/50 bg-muted/5 shadow-inner flex flex-wrap gap-2 items-start content-start transition-all">
        {#if profile.skills.length === 0}
          <div class="flex flex-col items-center justify-center w-full h-full py-4 opacity-40">
            <p class="text-xs font-bold uppercase tracking-widest text-muted-foreground text-center">Type a skill below and press Enter</p>
          </div>
        {/if}
        {#each profile.skills as skill (skill)}
          <div 
            in:scale={{ duration: 200, start: 0.8 }} 
            out:fade={{ duration: 150 }}
          >
            <Badge variant="secondary" class="h-8 text-sm font-bold rounded-lg gap-2 pl-3 pr-1.5 transition-all hover:bg-primary/10 hover:text-primary border border-transparent hover:border-primary/20 bg-background shadow-sm">
              {skill}
              <button
                type="button"
                class="w-5 h-5 rounded-md inline-flex items-center justify-center hover:bg-destructive/10 hover:text-destructive transition-colors group/x"
                onclick={() => removeSkill(skill)}
                tabindex={0}
                onkeydown={(e) => e.key === 'Enter' && removeSkill(skill)}
                aria-label="Remove skill {skill}"
              >
                <X class="w-3.5 h-3.5 opacity-60 group-hover/x:opacity-100" />
              </button>
            </Badge>
          </div>
        {/each}
      </div>

      <!-- Input row -->
      <div class="flex gap-3">
        <div class="flex-1 flex items-center gap-3 px-4 h-12 rounded-xl border bg-background transition-all focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary shadow-sm">
          <input
            id="skills-input"
            bind:value={skillsText}
            onkeydown={(e) => {
              if (e.key === 'Backspace' && !skillsText && profile.skills.length > 0) {
                removeSkill(profile.skills[profile.skills.length - 1]);
              } else {
                addSkill(e);
              }
            }}
            placeholder="e.g. JavaScript, React, PostgreSQL..."
            class="flex-1 bg-transparent border-none outline-none ring-0 text-base placeholder:text-muted-foreground/40 font-medium"
          />
          <span class="hidden sm:flex items-center gap-1 shrink-0 text-[10px] text-muted-foreground/40 font-bold uppercase tracking-wider">
            <kbd class="px-1.5 py-0.5 rounded border bg-muted/50 font-sans">Enter</kbd>
          </span>
        </div>
        <Button 
          type="button" 
          variant="default" 
          onclick={commitSkill} 
          disabled={!skillsText.trim()}
          class="h-12 px-6 font-bold shadow-md hover:shadow-lg transition-all"
        >
          <Plus class="w-4 h-4 mr-2" /> Add
        </Button>
      </div>
    </div>
  </div>
</div>
