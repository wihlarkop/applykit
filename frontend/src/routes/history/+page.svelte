<script lang="ts">
  import {
    getCvHistory,
    getCoverLetterHistory,
    deleteCvHistoryEntry,
    deleteCoverLetterHistoryEntry,
  } from '$lib/api';
  import { goto } from '$app/navigation';
  import { profiles } from '$lib/profiles.svelte';
  import { activeProfile } from '$lib/activeProfile.svelte';
  import type { GeneratedCVEntry, GeneratedCoverLetterEntry, ProfileData } from '$lib/types';
  import { Button } from '$lib/components/ui/button';
  import { Badge } from '$lib/components/ui/badge';
  import { Sparkles } from '@lucide/svelte';
  import CvPreview from '$lib/components/CvPreview.svelte';
  import CoverLetterPreview from '$lib/components/CoverLetterPreview.svelte';

  type Tab = 'cv' | 'cover-letter';
  let tab: Tab = $state('cv');
  let filterProfileId: number | undefined = $state(undefined);

  let cvItems: GeneratedCVEntry[] = $state([]);
  let clItems: GeneratedCoverLetterEntry[] = $state([]);
  let loading = $state(true);
  let errorMsg = $state('');

  let selectedCv: GeneratedCVEntry | null = $state(null);
  let selectedCl: GeneratedCoverLetterEntry | null = $state(null);

  const allProfiles = $derived(profiles.all);

  async function loadHistory() {
    loading = true;
    errorMsg = '';
    selectedCv = null;
    selectedCl = null;
    try {
      const [cvRes, clRes] = await Promise.all([
        getCvHistory(filterProfileId),
        getCoverLetterHistory(filterProfileId),
      ]);
      cvItems = cvRes.items;
      clItems = clRes.items;
    } catch (e: any) {
      errorMsg = e.message;
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    // Re-fetch whenever filterProfileId changes (runs on mount too)
    filterProfileId;
    loadHistory();
  });

  function formatDate(iso: string) {
    return new Date(iso).toLocaleString(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    });
  }

  async function handleDeleteCv(id: number) {
    try {
      await deleteCvHistoryEntry(id);
      cvItems = cvItems.filter((e) => e.id !== id);
      if (selectedCv?.id === id) selectedCv = null;
    } catch (e: any) {
      errorMsg = `Failed to delete: ${e.message}`;
    }
  }

  async function handleDeleteCl(id: number) {
    try {
      await deleteCoverLetterHistoryEntry(id);
      clItems = clItems.filter((e) => e.id !== id);
      if (selectedCl?.id === id) selectedCl = null;
    } catch (e: any) {
      errorMsg = `Failed to delete: ${e.message}`;
    }
  }

  function parseCvProfile(entry: GeneratedCVEntry): ProfileData {
    return JSON.parse(entry.profile_snapshot) as ProfileData;
  }

  function handlePrint() {
    window.print();
  }

  function handleRegenerate(entry: GeneratedCVEntry) {
    if (entry.profile_id) {
      const p = profiles.all.find(p => p.id === entry.profile_id);
      if (p) activeProfile.set({ id: p.id, label: p.label, color: p.color, icon: p.icon, name: p.name });
    }
    goto('/generate');
  }

  function displayCompany(entry: GeneratedCoverLetterEntry): string {
    if (entry.company_name) return entry.company_name;
    const jd = entry.job_description.trim();
    return jd.length > 45 ? jd.slice(0, 42) + '…' : jd;
  }
</script>

<div class="space-y-6">
  <h1 class="text-2xl font-bold">History</h1>

  <!-- Profile filter -->
  {#if allProfiles.length > 1}
    <div class="flex items-center gap-2 flex-wrap">
      <span class="text-xs text-muted-foreground uppercase tracking-wider">Filter:</span>
      <button
        onclick={() => filterProfileId = undefined}
        class="px-3 py-1 rounded-full text-xs font-medium border transition-colors
          {filterProfileId == null ? 'bg-primary text-primary-foreground border-primary' : 'border-border text-muted-foreground hover:text-foreground hover:bg-accent'}"
      >
        All profiles
      </button>
      {#each allProfiles as p}
        <button
          onclick={() => filterProfileId = p.id}
          class="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border transition-colors
            {filterProfileId === p.id ? 'text-white border-transparent' : 'border-border text-muted-foreground hover:text-foreground hover:bg-accent'}"
          style={filterProfileId === p.id ? `background:${p.color}; border-color:${p.color}` : ''}
        >
          <span class="w-1.5 h-1.5 rounded-full" style="background:{filterProfileId === p.id ? 'white' : p.color}"></span>
          {p.icon} {p.label}
        </button>
      {/each}
    </div>
  {/if}

  <!-- Tabs -->
  <div class="flex gap-2 border-b">
    <button
      class="px-4 py-2 text-sm font-medium transition-colors
        {tab === 'cv' ? 'border-b-2 border-primary text-foreground' : 'text-muted-foreground hover:text-foreground'}"
      onclick={() => { tab = 'cv'; selectedCv = null; }}
    >
      Generated CVs ({loading ? '…' : cvItems.length})
    </button>
    <button
      class="px-4 py-2 text-sm font-medium transition-colors
        {tab === 'cover-letter' ? 'border-b-2 border-primary text-foreground' : 'text-muted-foreground hover:text-foreground'}"
      onclick={() => { tab = 'cover-letter'; selectedCl = null; }}
    >
      Cover Letters ({loading ? '…' : clItems.length})
    </button>
  </div>

  {#if loading}
    <p class="text-muted-foreground">Loading…</p>
  {:else if errorMsg}
    <p class="text-sm text-destructive">{errorMsg}</p>
  {:else}

    {#if tab === 'cv'}
      {#if cvItems.length === 0}
        <p class="text-muted-foreground">No CVs generated yet{filterProfileId != null ? ' for this profile' : ''}. <a href="/generate" class="underline">Generate one</a>.</p>
      {:else}
        <div class="grid gap-4 lg:grid-cols-[280px_1fr]">
          <div class="space-y-2">
            {#each cvItems as entry}
              <button
                onclick={() => selectedCv = entry}
                class="w-full text-left border rounded-lg p-3 transition-colors hover:bg-accent
                  {selectedCv?.id === entry.id ? 'border-primary bg-accent' : 'bg-card'}"
              >
                <div class="flex items-center justify-between gap-2">
                  <span class="text-sm font-medium truncate">{formatDate(entry.created_at)}</span>
                  <div class="flex items-center gap-1.5 shrink-0">
                    {#if entry.profile_color && entry.profile_icon}
                      <span class="flex items-center gap-1 text-xs text-muted-foreground">
                        <span class="w-2 h-2 rounded-full" style="background:{entry.profile_color}"></span>
                        {entry.profile_icon}
                      </span>
                    {/if}
                    {#if entry.enhanced}
                      <Badge variant="default" class="text-xs">AI</Badge>
                    {:else}
                      <Badge variant="secondary" class="text-xs">Raw</Badge>
                    {/if}
                  </div>
                </div>
              </button>
            {/each}
          </div>

          {#if selectedCv}
            <div class="border rounded-lg overflow-hidden bg-white dark:bg-zinc-950/40 print:bg-white shadow-sm transition-colors">
              <div class="flex items-center justify-between gap-2 p-3 border-b bg-muted/30">
                <span class="text-sm text-muted-foreground">{formatDate(selectedCv.created_at)}</span>
                <div class="flex gap-2">
                  <Button variant="outline" size="sm" onclick={() => selectedCv && handleRegenerate(selectedCv)}>
                    <Sparkles class="w-4 h-4 mr-1" /> Regenerate
                  </Button>
                  <Button variant="outline" size="sm" onclick={handlePrint}>Print</Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    onclick={() => selectedCv && handleDeleteCv(selectedCv.id)}
                  >
                    Delete
                  </Button>
                </div>
              </div>
              <div class="overflow-auto max-h-[70vh]">
                <CvPreview profile={parseCvProfile(selectedCv)} />
              </div>
            </div>
          {:else}
            <div class="border rounded-lg p-8 text-center text-muted-foreground">
              Select an entry to preview.
            </div>
          {/if}
        </div>
      {/if}
    {/if}

    {#if tab === 'cover-letter'}
      {#if clItems.length === 0}
        <p class="text-muted-foreground">No cover letters generated yet{filterProfileId != null ? ' for this profile' : ''}. <a href="/cover-letter" class="underline">Write one</a>.</p>
      {:else}
        <div class="grid gap-4 lg:grid-cols-[280px_1fr]">
          <div class="space-y-2">
            {#each clItems as entry}
              <button
                onclick={() => selectedCl = entry}
                class="w-full text-left border rounded-lg p-3 transition-colors hover:bg-accent
                  {selectedCl?.id === entry.id ? 'border-primary bg-accent' : 'bg-card'}"
              >
                <div class="text-sm font-medium truncate">
                  {displayCompany(entry)}
                </div>
                {#if entry.profile_color && entry.profile_icon}
                  <span class="flex items-center gap-1 text-xs text-muted-foreground">
                    <span class="w-2 h-2 rounded-full" style="background:{entry.profile_color}"></span>
                    {entry.profile_icon}
                  </span>
                {/if}
                <div class="text-xs text-muted-foreground mt-0.5">{formatDate(entry.created_at)}</div>
              </button>
            {/each}
          </div>

          {#if selectedCl}
            <div class="border rounded-lg overflow-hidden bg-white dark:bg-zinc-950/40 print:bg-white shadow-sm transition-colors">
              <div class="flex items-center justify-between gap-2 p-3 border-b bg-muted/30">
                <div>
                  <span class="text-sm font-medium">{displayCompany(selectedCl)}</span>
                  <span class="text-xs text-muted-foreground ml-2">{formatDate(selectedCl.created_at)}</span>
                </div>
                <div class="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onclick={() => navigator.clipboard.writeText(selectedCl?.cover_letter_text ?? '')}
                  >
                    Copy
                  </Button>
                  <Button variant="outline" size="sm" onclick={handlePrint}>Print</Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    onclick={() => selectedCl && handleDeleteCl(selectedCl.id)}
                  >
                    Delete
                  </Button>
                </div>
              </div>
              <div class="overflow-auto max-h-[70vh]">
                <CoverLetterPreview text={selectedCl.cover_letter_text} />
              </div>
            </div>
          {:else}
            <div class="border rounded-lg p-8 text-center text-muted-foreground">
              Select an entry to preview.
            </div>
          {/if}
        </div>
      {/if}
    {/if}

  {/if}
</div>

<style>
  @media print {
    :global(header), :global(nav) { display: none !important; }
  }
</style>
