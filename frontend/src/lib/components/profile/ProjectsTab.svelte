<script lang="ts">
  import { FolderGit2, Plus, Trash2 } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { Label } from '$lib/components/ui/label';
  import { Textarea } from '$lib/components/ui/textarea';
  import type { ProfileData, Project } from '$lib/types';

  interface Props {
    profile: ProfileData;
  }
  let { profile = $bindable() }: Props = $props();

  function addProject() {
    profile.projects = [
      ...profile.projects,
      { name: '', description: '', tech_stack: [], link: null },
    ];
  }

  function removeProject(i: number) {
    profile.projects = profile.projects.filter((_, idx) => idx !== i);
  }

  function projectTechText(p: Project) {
    return p.tech_stack.join(', ');
  }

  function setProjectTech(i: number, text: string) {
    profile.projects[i].tech_stack = text
      .split(',')
      .map(s => s.trim())
      .filter(Boolean);
  }
</script>

<div class="grid lg:grid-cols-12 gap-x-12 gap-y-10 text-left">
  <!-- Left Column (Title & Add Action) -->
  <div class="lg:col-span-4 space-y-6">
    <div class="space-y-2">
      <h2 class="text-xl font-bold tracking-tight flex items-center gap-3 text-foreground">
        <div class="p-2 bg-primary/10 rounded-lg">
          <FolderGit2 class="w-5 h-5 text-primary" />
        </div>
        Projects
      </h2>
      <p class="text-sm text-muted-foreground leading-relaxed">Showcase your best work and technical projects.</p>
    </div>
    
    <div class="hidden lg:block pt-4">
      <Button 
        onclick={addProject} 
        variant="outline" 
        size="lg" 
        class="w-full h-12 px-6 font-bold border-dashed border-2 hover:border-primary hover:bg-primary/5 transition-all rounded-xl shadow-sm hover:shadow-md group"
      >
        <Plus class="w-5 h-5 mr-2 transition-transform group-hover:rotate-90" />
        Add Project
      </Button>
    </div>
  </div>

  <!-- Right Column (Entry Cards) -->
  <div class="lg:col-span-8 space-y-10">
    {#if profile.projects.length === 0}
      <div class="text-center py-10 text-muted-foreground text-sm border-2 border-dashed rounded-xl bg-muted/20">
        No projects added yet.
      </div>
    {:else}
      {#each profile.projects as proj, i}
        <div class="relative border border-border/50 rounded-2xl p-6 space-y-8 bg-muted/5 group transition-all hover:bg-muted/10 hover:shadow-sm">
          <div class="absolute right-4 top-4 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button variant="ghost" size="icon" class="h-8 w-8 text-destructive hover:bg-destructive/10" onclick={() => removeProject(i)}>
              <Trash2 class="w-4 h-4" />
            </Button>
          </div>
          
          <div class="grid gap-8">
            <div class="grid gap-6 sm:grid-cols-2">
              <div class="space-y-2 text-left">
                <Label class="text-xs font-bold uppercase tracking-wider text-muted-foreground">Project Name</Label>
                <Input bind:value={proj.name} placeholder="e.g. AI Workflow Automator" class="bg-background h-11 text-base border-muted-foreground/20 focus:border-primary transition-all" />
              </div>
              <div class="space-y-2 text-left">
                <Label class="text-xs font-bold uppercase tracking-wider text-muted-foreground">External Link</Label>
                <Input bind:value={proj.link} placeholder="https://github.com/..." class="bg-background h-11 text-base border-muted-foreground/20 focus:border-primary transition-all" />
              </div>
            </div>
            
            <div class="space-y-2 text-left">
              <Label class="text-xs font-bold uppercase tracking-wider text-muted-foreground">Description</Label>
              <Textarea bind:value={proj.description} placeholder="Describe the core problem, your approach, and key technical challenges..." rows={4} class="bg-background resize-y p-5 text-sm sm:text-base border-muted-foreground/20 focus:border-primary transition-all rounded-2xl shadow-inner-sm" />
            </div>
            
            <div class="space-y-2 text-left">
              <Label class="text-xs font-bold uppercase tracking-wider text-muted-foreground">Tech Stack (comma separated)</Label>
              <Input
                value={projectTechText(proj)}
                oninput={(e) => setProjectTech(i, (e.target as HTMLInputElement).value)}
                placeholder="e.g. React, Node.js, PostgreSQL"
                class="bg-background h-11 text-base border-muted-foreground/20 focus:border-primary transition-all"
              />
            </div>
          </div>
        </div>
      {/each}
    {/if}

    <!-- Mobile-only Add Button (at bottom) -->
    <div class="lg:hidden pt-6 flex justify-center">
      <Button 
        onclick={addProject} 
        variant="outline" 
        size="lg" 
        class="w-full h-12 font-bold border-dashed border-2 hover:border-primary hover:bg-primary/5 rounded-xl transition-all"
      >
        <Plus class="w-5 h-5 mr-2" />
        Add Project
      </Button>
    </div>
  </div>
</div>
