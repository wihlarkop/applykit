<script lang="ts">
  import { GraduationCap, Plus, Trash2 } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { Label } from '$lib/components/ui/label';
  import type { ProfileData } from '$lib/types';

  interface Props {
    profile: ProfileData;
  }
  let { profile = $bindable() }: Props = $props();

  function addEdu() {
    profile.education = [
      ...profile.education,
      { institution: '', degree: '', field: '', start_date: '', end_date: '' },
    ];
  }

  function removeEdu(i: number) {
    profile.education = profile.education.filter((_, idx) => idx !== i);
  }
</script>

<div class="grid lg:grid-cols-12 gap-x-12 gap-y-10 text-left">
  <!-- Left Column (Title & Add Action) -->
  <div class="lg:col-span-4 space-y-6">
    <div class="space-y-2">
      <h2 class="text-xl font-bold tracking-tight flex items-center gap-3 text-foreground">
        <div class="p-2 bg-primary/10 rounded-lg">
          <GraduationCap class="w-5 h-5 text-primary" />
        </div>
        Education
      </h2>
      <p class="text-sm text-muted-foreground leading-relaxed">Your academic background and formal qualifications.</p>
    </div>
    
    <div class="hidden lg:block pt-4">
      <Button 
        onclick={addEdu} 
        variant="outline" 
        size="lg" 
        class="w-full h-12 px-6 font-bold border-dashed border-2 hover:border-primary hover:bg-primary/5 transition-all rounded-xl shadow-sm hover:shadow-md group"
      >
        <Plus class="w-5 h-5 mr-2 transition-transform group-hover:rotate-90" />
        Add Education
      </Button>
    </div>
  </div>

  <!-- Right Column (Entry Cards) -->
  <div class="lg:col-span-8 space-y-10">
    {#if profile.education.length === 0}
      <div class="text-center py-10 text-muted-foreground text-sm border-2 border-dashed rounded-xl bg-muted/20">
        No education added yet.
      </div>
    {:else}
      {#each profile.education as edu, i}
        <div class="relative border border-border/50 rounded-2xl p-6 space-y-8 bg-muted/5 group transition-all hover:bg-muted/10 hover:shadow-sm">
          <div class="absolute right-4 top-4 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button variant="ghost" size="icon" class="h-8 w-8 text-destructive hover:bg-destructive/10" onclick={() => removeEdu(i)}>
              <Trash2 class="w-4 h-4" />
            </Button>
          </div>
          
          <div class="grid gap-8">
            <div class="space-y-2 text-left">
              <Label class="text-xs font-bold uppercase tracking-wider text-muted-foreground">Educational Institution</Label>
              <Input bind:value={edu.institution} placeholder="e.g. Massachusetts Institute of Technology" class="bg-background h-11 text-base border-muted-foreground/20 focus:border-primary transition-all" />
            </div>

            <div class="grid gap-6 sm:grid-cols-3">
              <div class="space-y-2 text-left">
                <Label class="text-xs font-bold uppercase tracking-wider text-muted-foreground">Degree / Level</Label>
                <Input bind:value={edu.degree} placeholder="e.g. Bachelor's" class="bg-background h-10 border-muted-foreground/20 focus:border-primary transition-all" />
              </div>
              <div class="space-y-2 text-left">
                <Label class="text-xs font-bold uppercase tracking-wider text-muted-foreground">Start Date</Label>
                <Input bind:value={edu.start_date} placeholder="e.g. Sep 2018" class="bg-background h-10 border-muted-foreground/20 focus:border-primary transition-all" />
              </div>
              <div class="space-y-2 text-left">
                <Label class="text-xs font-bold uppercase tracking-wider text-muted-foreground">End Date</Label>
                <Input bind:value={edu.end_date} placeholder="e.g. Jun 2022" class="bg-background h-10 border-muted-foreground/20 focus:border-primary transition-all" />
              </div>
            </div>

            <div class="space-y-2 text-left">
              <Label class="text-xs font-bold uppercase tracking-wider text-muted-foreground">Field of Study</Label>
              <Input bind:value={edu.field} placeholder="e.g. Computer Science & Engineering" class="bg-background h-11 text-base border-muted-foreground/20 focus:border-primary transition-all" />
            </div>
          </div>
        </div>
      {/each}
    {/if}

    <!-- Mobile-only Add Button (at bottom) -->
    <div class="lg:hidden pt-6 flex justify-center">
      <Button 
        onclick={addEdu} 
        variant="outline" 
        size="lg" 
        class="w-full h-12 font-bold border-dashed border-2 hover:border-primary hover:bg-primary/5 rounded-xl transition-all"
      >
        <Plus class="w-5 h-5 mr-2" />
        Add Education
      </Button>
    </div>
  </div>
</div>
