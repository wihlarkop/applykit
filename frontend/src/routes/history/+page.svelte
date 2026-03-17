<script lang="ts">
  import { goto } from '$app/navigation';
  import { activeProfile } from '$lib/activeProfile.svelte';
  import {
      bulkDeleteCoverLetters,
      bulkDeleteCvs,
      deleteCoverLetterHistoryEntry,
      deleteCvHistoryEntry,
      getCoverLetterHistory,
      getCvHistory,
      updateCoverLetterStatus,
      updateCvStatus,
  } from '$lib/api';
  import CoverLetterPreview from '$lib/components/CoverLetterPreview.svelte';
  import CvPreview from '$lib/components/CvPreview.svelte';
  import { Badge } from '$lib/components/ui/badge';
  import { Button } from '$lib/components/ui/button';
  import { profiles } from '$lib/profiles.svelte';
  import type { GeneratedCVEntry, GeneratedCoverLetterEntry, ProfileData } from '$lib/types';
  import { Sparkles } from '@lucide/svelte';

  type Tab = 'cv' | 'cover-letter';
  let tab: Tab = $state('cv');
  let filterProfileId: number | undefined = $state(undefined);

  let cvItems: GeneratedCVEntry[] = $state([]);
  let clItems: GeneratedCoverLetterEntry[] = $state([]);
  let loading = $state(true);
  let errorMsg = $state('');
  let loadSeq = 0;

  let selectedCv: GeneratedCVEntry | null = $state(null);
  let selectedCl: GeneratedCoverLetterEntry | null = $state(null);
  let previewTab = $state<'letter' | 'analysis'>('letter');

  // Cover letter filters
  let clSearch = $state('');
  let clMatchFilter = $state<'all' | 'high' | 'medium' | 'low'>('all');
  let clSort = $state<'date_desc' | 'date_asc' | 'match_desc' | 'company_asc'>('date_desc');
  let clTotal = $state(0);
  let clSearchTimer: ReturnType<typeof setTimeout>;

  // Bulk delete
  let selectedClIds = $state<Set<number>>(new Set());
  let selectedCvIds = $state<Set<number>>(new Set());
  let confirmBulkDelete = $state(false);

  // Status options
  const STATUS_OPTIONS = [
    { value: null, label: '—' },
    { value: 'applied', label: 'Applied' },
    { value: 'interviewing', label: 'Interviewing' },
    { value: 'offer', label: 'Offer' },
    { value: 'rejected', label: 'Rejected' },
  ];

  const STATUS_PIPELINE = [
    { value: 'applied',      label: 'Applied',      activeClass: 'bg-blue-500/20 text-blue-600 border border-blue-500/40' },
    { value: 'interviewing', label: 'Interviewing',  activeClass: 'bg-amber-500/20 text-amber-600 border border-amber-500/40' },
    { value: 'offer',        label: 'Offer',         activeClass: 'bg-green-500/20 text-green-600 border border-green-500/40' },
    { value: 'rejected',     label: 'Rejected',      activeClass: 'bg-red-500/20 text-red-600 border border-red-500/40' },
  ];

  const allProfiles = $derived(profiles.all);

  async function loadCoverLetters() {
    const filters: any = { sort: clSort };
    if (filterProfileId != null) filters.profile_id = filterProfileId;
    if (clSearch) filters.search = clSearch;
    if (clMatchFilter === 'high') filters.match_min = 70;
    else if (clMatchFilter === 'medium') { filters.match_min = 40; filters.match_max = 69; }
    else if (clMatchFilter === 'low') filters.match_max = 39;
    const res = await getCoverLetterHistory(filters);
    clItems = res.items;
    clTotal = res.total;
  }

  async function handleClStatusChange(id: number, status: string | null) {
    try {
      const updated = await updateCoverLetterStatus(id, status);
      clItems = clItems.map((e) => (e.id === id ? updated : e));
    } catch (e: any) {
      errorMsg = `Failed to update status: ${e.message}`;
    }
  }

  async function handleBulkDeleteCl() {
    try {
      await bulkDeleteCoverLetters([...selectedClIds]);
      clItems = clItems.filter((e) => !selectedClIds.has(e.id));
      selectedClIds = new Set();
      confirmBulkDelete = false;
    } catch (e: any) {
      errorMsg = `Failed to delete: ${e.message}`;
    }
  }

  $effect(() => {
    const profileId = filterProfileId;
    const seq = ++loadSeq;
    loading = true;
    errorMsg = '';
    selectedCv = null;
    selectedCl = null;
    // CV tab — simple call unchanged
    getCvHistory(profileId !== undefined ? { profile_id: profileId } : {})
      .then((r) => {
        if (seq !== loadSeq) return;
        cvItems = r.items;
      })
      .catch((e: any) => {
        if (seq !== loadSeq) return;
        errorMsg = e.message;
      })
      .finally(() => {
        if (seq !== loadSeq) return;
        loading = false;
      });
    // Cover letter tab — use filter-aware loader
    loadCoverLetters();
  });

  $effect(() => {
    if (selectedCl) previewTab = 'letter';
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

  function parseCvProfile(entry: GeneratedCVEntry): ProfileData | null {
    try {
      return JSON.parse(entry.profile_snapshot) as ProfileData;
    } catch {
      return null;
    }
  }

  function handlePrint() {
    window.print();
  }

  async function handleCopyCl() {
    try {
      await navigator.clipboard.writeText(selectedCl?.cover_letter_text ?? '');
    } catch {
      errorMsg = 'Failed to copy to clipboard.';
    }
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

  function displayRole(entry: GeneratedCoverLetterEntry): string {
    const firstLine = entry.job_description.split('\n')[0].trim();
    if (!firstLine) return '';
    return firstLine.length > 50 ? firstLine.slice(0, 47) + '…' : firstLine;
  }

  function scoreColor(score: number): string {
    if (score >= 70) return 'bg-green-500/10 text-green-600';
    if (score >= 40) return 'bg-yellow-500/10 text-yellow-600';
    return 'bg-red-500/10 text-red-600';
  }

  function scoreBarColor(score: number): string {
    if (score >= 70) return 'bg-green-500';
    if (score >= 40) return 'bg-yellow-500';
    return 'bg-red-500';
  }

  function formatDateShort(iso: string): string {
    return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
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
                {#if parseCvProfile(selectedCv)}
                  <CvPreview profile={parseCvProfile(selectedCv)!} />
                {:else}
                  <p class="p-8 text-sm text-destructive">Could not parse CV snapshot.</p>
                {/if}
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
        <!-- Filter bar -->
        <div class="flex items-center gap-2 flex-wrap mb-4">
          <input
            class="flex-1 min-w-[160px] bg-card border border-border rounded-md px-3 py-1.5 text-sm"
            placeholder="🔍 Search company or role..."
            bind:value={clSearch}
            oninput={() => { clearTimeout(clSearchTimer); clSearchTimer = setTimeout(loadCoverLetters, 300); }}
          />
          <select
            class="bg-card border border-border rounded-md px-2 py-1.5 text-sm"
            bind:value={clMatchFilter}
            onchange={loadCoverLetters}
          >
            <option value="all">All matches</option>
            <option value="high">High (≥70%)</option>
            <option value="medium">Medium (40–69%)</option>
            <option value="low">Low (&lt;40%)</option>
          </select>
          <select
            class="bg-card border border-border rounded-md px-2 py-1.5 text-sm"
            bind:value={clSort}
            onchange={loadCoverLetters}
          >
            <option value="date_desc">Newest first</option>
            <option value="date_asc">Oldest first</option>
            <option value="match_desc">Best match</option>
            <option value="company_asc">Company A–Z</option>
          </select>
          {#if selectedClIds.size > 0}
            <button
              onclick={() => (confirmBulkDelete = true)}
              class="px-3 py-1.5 text-sm bg-destructive text-destructive-foreground rounded-md hover:bg-destructive/90"
            >Delete selected ({selectedClIds.size})</button>
          {/if}
        </div>

        {#if confirmBulkDelete}
          <div class="border border-destructive/30 rounded-lg p-3 bg-destructive/5 flex items-center gap-3 mb-3">
            <p class="text-sm flex-1">Delete {selectedClIds.size} cover letter(s)?</p>
            <button onclick={handleBulkDeleteCl} class="text-sm text-destructive underline">Confirm</button>
            <button onclick={() => (confirmBulkDelete = false)} class="text-sm text-muted-foreground underline">Cancel</button>
          </div>
        {/if}

        <div class="grid gap-4 lg:grid-cols-[280px_1fr]">
          <div class="space-y-2">
            {#each clItems as entry}
              <div class="flex items-start gap-2">
                <input
                  type="checkbox"
                  class="mt-3 rounded"
                  checked={selectedClIds.has(entry.id)}
                  onchange={() => {
                    const s = new Set(selectedClIds);
                    if (s.has(entry.id)) s.delete(entry.id); else s.add(entry.id);
                    selectedClIds = s;
                  }}
                />
                <button
                  onclick={() => selectedCl = entry}
                  class="flex-1 text-left border rounded-lg p-3 transition-colors hover:bg-accent
                    {selectedCl?.id === entry.id ? 'border-primary bg-accent' : 'bg-card'}"
                >
                  <div class="flex items-center justify-between gap-2">
                    <span class="text-sm font-medium truncate">{displayCompany(entry)}</span>
                    <div class="flex items-center gap-1.5 shrink-0">
                      {#if entry.match_score !== null}
                        <span class="text-xs px-1.5 py-0.5 rounded font-medium
                          {entry.match_score >= 70 ? 'bg-green-500/10 text-green-600'
                           : entry.match_score >= 40 ? 'bg-yellow-500/10 text-yellow-600'
                           : 'bg-red-500/10 text-red-600'}">{entry.match_score}%</span>
                      {/if}
                      {#if entry.tone && entry.tone !== 'professional'}
                        <span class="text-xs bg-muted border border-border rounded px-1.5 py-0.5 capitalize">{entry.tone}</span>
                      {/if}
                      {#if entry.profile_color && entry.profile_icon}
                        <span class="flex items-center gap-1 text-xs text-muted-foreground">
                          <span class="w-2 h-2 rounded-full" style="background:{entry.profile_color}"></span>
                          {entry.profile_icon}
                        </span>
                      {/if}
                    </div>
                  </div>
                  <div class="text-xs text-muted-foreground mt-0.5">{formatDate(entry.created_at)}</div>
                  <!-- Status dropdown -->
                  <div class="mt-2 flex items-center gap-2" role="presentation" onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.stopPropagation()}>
                    <select
                      class="text-xs bg-background border border-border rounded px-2 py-1"
                      value={entry.application_status ?? ''}
                      onchange={(e) => handleClStatusChange(entry.id, (e.target as HTMLSelectElement).value || null)}
                    >
                      {#each STATUS_OPTIONS as opt}
                        <option value={opt.value ?? ''} disabled={!opt.value && !!entry.application_id}>{opt.label}</option>
                      {/each}
                    </select>
                    {#if entry.application_id}
                      <a href="/tracker" class="text-[10px] text-primary hover:underline" title="View in Tracker">📌 Tracked</a>
                    {/if}
                  </div>
                </button>
              </div>
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
                    onclick={handleCopyCl}
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
