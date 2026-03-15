<script lang="ts">
  import { onMount } from 'svelte';
  import {
    getCvHistory,
    getCoverLetterHistory,
    deleteCvHistoryEntry,
    deleteCoverLetterHistoryEntry,
  } from '$lib/api';
  import type { GeneratedCVEntry, GeneratedCoverLetterEntry, ProfileData } from '$lib/types';
  import { Button } from '$lib/components/ui/button';
  import { Badge } from '$lib/components/ui/badge';
  import CvPreview from '$lib/components/CvPreview.svelte';
  import CoverLetterPreview from '$lib/components/CoverLetterPreview.svelte';

  type Tab = 'cv' | 'cover-letter';
  let tab: Tab = $state('cv');

  let cvItems: GeneratedCVEntry[] = $state([]);
  let clItems: GeneratedCoverLetterEntry[] = $state([]);
  let loading = $state(true);
  let errorMsg = $state('');

  let selectedCv: GeneratedCVEntry | null = $state(null);
  let selectedCl: GeneratedCoverLetterEntry | null = $state(null);

  onMount(async () => {
    try {
      const [cvRes, clRes] = await Promise.all([getCvHistory(), getCoverLetterHistory()]);
      cvItems = cvRes.items;
      clItems = clRes.items;
    } catch (e: any) {
      errorMsg = e.message;
    } finally {
      loading = false;
    }
  });

  function formatDate(iso: string) {
    return new Date(iso).toLocaleString(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    });
  }

  async function handleDeleteCv(id: number) {
    await deleteCvHistoryEntry(id);
    cvItems = cvItems.filter((e) => e.id !== id);
    if (selectedCv?.id === id) selectedCv = null;
  }

  async function handleDeleteCl(id: number) {
    await deleteCoverLetterHistoryEntry(id);
    clItems = clItems.filter((e) => e.id !== id);
    if (selectedCl?.id === id) selectedCl = null;
  }

  function parseCvProfile(entry: GeneratedCVEntry): ProfileData {
    return JSON.parse(entry.profile_snapshot) as ProfileData;
  }

  function handlePrint() {
    window.print();
  }
</script>

<div class="space-y-6">
  <h1 class="text-2xl font-bold">History</h1>

  <!-- Tabs -->
  <div class="flex gap-2 border-b">
    <button
      class="px-4 py-2 text-sm font-medium transition-colors
        {tab === 'cv' ? 'border-b-2 border-primary text-foreground' : 'text-muted-foreground hover:text-foreground'}"
      onclick={() => { tab = 'cv'; selectedCv = null; }}
    >
      Generated CVs ({cvItems.length})
    </button>
    <button
      class="px-4 py-2 text-sm font-medium transition-colors
        {tab === 'cover-letter' ? 'border-b-2 border-primary text-foreground' : 'text-muted-foreground hover:text-foreground'}"
      onclick={() => { tab = 'cover-letter'; selectedCl = null; }}
    >
      Cover Letters ({clItems.length})
    </button>
  </div>

  {#if loading}
    <p class="text-muted-foreground">Loading…</p>
  {:else if errorMsg}
    <p class="text-sm text-destructive">{errorMsg}</p>
  {:else}

    {#if tab === 'cv'}
      {#if cvItems.length === 0}
        <p class="text-muted-foreground">No CVs generated yet. <a href="/generate" class="underline">Generate one</a>.</p>
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
        <p class="text-muted-foreground">No cover letters generated yet. <a href="/cover-letter" class="underline">Write one</a>.</p>
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
                  {entry.company_name ?? 'Unknown Company'}
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
                  <span class="text-sm font-medium">{selectedCl.company_name ?? 'Unknown Company'}</span>
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
