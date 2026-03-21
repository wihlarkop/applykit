<script lang="ts">
  import { Award, Plus, Trash2 } from '@lucide/svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { Label } from '$lib/components/ui/label';
  import type { ProfileData } from '$lib/types';

  interface Props {
    profile: ProfileData;
  }
  let { profile = $bindable() }: Props = $props();

  function addCert() {
    profile.certifications = [
      ...profile.certifications,
      { name: '', issuer: '', date: '' },
    ];
  }

  function removeCert(i: number) {
    profile.certifications = profile.certifications.filter((_, idx) => idx !== i);
  }
</script>

<div class="grid lg:grid-cols-12 gap-x-12 gap-y-10 text-left">
  <!-- Left Column (Title & Add Action) -->
  <div class="lg:col-span-4 space-y-6">
    <div class="space-y-2">
      <h2 class="text-xl font-bold tracking-tight flex items-center gap-3 text-foreground">
        <div class="p-2 bg-primary/10 rounded-lg">
          <Award class="w-5 h-5 text-primary" />
        </div>
        Certifications
      </h2>
      <p class="text-sm text-muted-foreground leading-relaxed">Official validations of your expertise.</p>
    </div>
    
    <div class="hidden lg:block pt-4">
      <Button 
        onclick={addCert} 
        variant="outline" 
        size="lg" 
        class="w-full h-12 px-6 font-bold border-dashed border-2 hover:border-primary hover:bg-primary/5 transition-all rounded-xl shadow-sm hover:shadow-md group"
      >
        <Plus class="w-5 h-5 mr-2 transition-transform group-hover:rotate-90" />
        Add Certification
      </Button>
    </div>
  </div>

  <!-- Right Column (Entry Cards) -->
  <div class="lg:col-span-8 space-y-10">
    {#if profile.certifications.length === 0}
      <div class="text-center py-10 text-muted-foreground text-sm border-2 border-dashed rounded-xl bg-muted/20">
        No certifications added yet.
      </div>
    {:else}
      {#each profile.certifications as cert, i}
        <div class="relative border border-border/50 rounded-2xl p-6 space-y-8 bg-muted/5 group transition-all hover:bg-muted/10 hover:shadow-sm">
          <div class="absolute right-4 top-4 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button variant="ghost" size="icon" class="h-8 w-8 text-destructive hover:bg-destructive/10" onclick={() => removeCert(i)}>
              <Trash2 class="w-4 h-4" />
            </Button>
          </div>
          
          <div class="grid gap-8">
            <div class="grid gap-6 sm:grid-cols-2 text-left">
              <div class="space-y-2">
                <Label class="text-xs font-bold uppercase tracking-wider text-muted-foreground">Certification Name</Label>
                <Input bind:value={cert.name} placeholder="e.g. AWS Certified Developer" class="bg-background h-11 text-base border-muted-foreground/20 focus:border-primary transition-all" />
              </div>
              <div class="space-y-2">
                <Label class="text-xs font-bold uppercase tracking-wider text-muted-foreground">Issuing Organization</Label>
                <Input bind:value={cert.issuer} placeholder="e.g. Amazon Web Services" class="bg-background h-11 text-base border-muted-foreground/20 focus:border-primary transition-all" />
              </div>
            </div>
            
            <div class="space-y-2 text-left max-w-60">
              <Label class="text-xs font-bold uppercase tracking-wider text-muted-foreground">Date Issued</Label>
              <Input bind:value={cert.date} placeholder="e.g. March 2024" class="bg-background h-10 border-muted-foreground/20 focus:border-primary transition-all" />
            </div>
          </div>
        </div>
      {/each}
    {/if}

    <!-- Mobile-only Add Button (at bottom) -->
    <div class="lg:hidden pt-6 flex justify-center">
      <Button 
        onclick={addCert} 
        variant="outline" 
        size="lg" 
        class="w-full h-12 font-bold border-dashed border-2 hover:border-primary hover:bg-primary/5 rounded-xl transition-all"
      >
        <Plus class="w-5 h-5 mr-2" />
        Add Certification
      </Button>
    </div>
  </div>
</div>
