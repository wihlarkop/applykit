<script lang="ts">
	import { goto } from '$app/navigation';
	import { activeProfile } from '$lib/activeProfile.svelte';
	import {
	    bulkDeleteCoverLetters,
	    deleteCoverLetterHistoryEntry,
	    deleteCvHistoryEntry,
	    generateCvPdf,
	    generateCoverLetterPdf,
	    getCoverLetterHistory,
	    getCvHistory,
	    updateCoverLetterStatus
	} from '$lib/api';
	import CoverLetterPreview from '$lib/components/CoverLetterPreview.svelte';
	import CvPreview from '$lib/components/CvPreview.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import ScoreRing from '$lib/components/ScoreRing.svelte';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import CvCard from '$lib/components/history/CvCard.svelte';
	import ClCard from '$lib/components/history/ClCard.svelte';
	import ClPreviewHeader from '$lib/components/history/ClPreviewHeader.svelte';
	import FitAnalysisTab from '$lib/components/history/FitAnalysisTab.svelte';
	import { STATUS_CONFIG } from '$lib/constants';
	import { profiles } from '$lib/profiles.svelte';
	import type { GeneratedCVEntry, GeneratedCoverLetterEntry, ProfileData } from '$lib/types';
	import { errorMessage, formatDate, formatDateShort, getScoreBarColor, getScoreColor } from '$lib/utils';
	import { toastState } from '$lib/toast.svelte';
	import { Clock, Download, FileText, Sparkles } from '@lucide/svelte';

	type Tab = 'cv' | 'cover-letter';
	let tab: Tab = $state('cv');
	let filterProfileId: number | undefined = $state(undefined);

	let cvItems: GeneratedCVEntry[] = $state([]);
	let clItems: GeneratedCoverLetterEntry[] = $state([]);
	let loading = $state(true);
	let errorMsg = $state('');
	let loadSeq = 0;

	let selectedCv: GeneratedCVEntry | null = $state(null);
	let cvPreviewEl: HTMLDivElement | undefined = $state(undefined);
	let downloading = $state(false);
	let selectedCl: GeneratedCoverLetterEntry | null = $state(null);
	let previewTab = $state<'letter' | 'analysis'>('letter');

	let clSearch = $state('');
	let clMatchFilter = $state<'all' | 'high' | 'medium' | 'low'>('all');
	let clSort = $state<'date_desc' | 'date_asc' | 'match_desc' | 'company_asc'>('date_desc');
	let clTotal = $state(0);
	let clSearchTimer: ReturnType<typeof setTimeout>;

	let selectedClIds = $state<Set<number>>(new Set());
	let selectedCvIds = $state<Set<number>>(new Set());
	let confirmBulkDelete = $state(false);

	const STATUS_PIPELINE = Object.entries(STATUS_CONFIG).map(([value, config]) => ({
		value,
		...config,
	}));

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
    } catch (e: unknown) {
      toastState.error(`Failed to update status: ${errorMessage(e)}`);
    }
  }

  async function handleBulkDeleteCl() {
    try {
      await bulkDeleteCoverLetters([...selectedClIds]);
      clItems = clItems.filter((e) => !selectedClIds.has(e.id));
      if (selectedCl && selectedClIds.has(selectedCl.id)) selectedCl = null;
      selectedClIds = new Set();
      confirmBulkDelete = false;
    } catch (e: unknown) {
      toastState.error(`Failed to delete: ${errorMessage(e)}`);
    }
  }

  $effect(() => {
    const profileId = filterProfileId;
    const seq = ++loadSeq;
    loading = true;
    selectedCv = null;
    selectedCl = null;
    // CV tab — simple call unchanged
    getCvHistory(profileId !== undefined ? { profile_id: profileId } : {})
      .then((r) => {
        if (seq !== loadSeq) return;
        cvItems = r.items;
      })
      .catch((e: unknown) => {
        if (seq !== loadSeq) return;
        toastState.error(`Failed to load CV history: ${errorMessage(e)}`);
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

  async function handleDeleteCv(id: number) {
    try {
      await deleteCvHistoryEntry(id);
      cvItems = cvItems.filter((e) => e.id !== id);
      if (selectedCv?.id === id) selectedCv = null;
    } catch (e: unknown) {
      toastState.error(`Failed to delete: ${errorMessage(e)}`);
    }
  }

  async function handleDeleteCl(id: number) {
    try {
      await deleteCoverLetterHistoryEntry(id);
      clItems = clItems.filter((e) => e.id !== id);
      if (selectedCl?.id === id) selectedCl = null;
    } catch (e: unknown) {
      toastState.error(`Failed to delete: ${errorMessage(e)}`);
    }
  }

  function parseCvProfile(entry: GeneratedCVEntry): ProfileData | null {
    try {
      return JSON.parse(entry.profile_snapshot) as ProfileData;
    } catch {
      return null;
    }
  }


  async function handleCopyCl() {
    try {
      await navigator.clipboard.writeText(selectedCl?.cover_letter_text ?? '');
      toastState.success('Copied to clipboard!');
    } catch {
      toastState.error('Failed to copy to clipboard.');
    }
  }

  function handleRegenerate(entry: GeneratedCVEntry) {
    if (entry.profile_id) {
      const p = profiles.all.find(p => p.id === entry.profile_id);
      if (p) activeProfile.set({ id: p.id, label: p.label, color: p.color, icon: p.icon, name: p.name });
    }
    goto('/generate');
  }

  async function handleDownloadCv() {
    if (!selectedCv) return;
    const profileData = parseCvProfile(selectedCv);
    if (!profileData) return;
    downloading = true;
    try {
      const blob = await generateCvPdf({ profile: profileData });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'cv.pdf';
      a.click();
      URL.revokeObjectURL(url);
      toastState.success('CV Downloaded!');
    } catch (e: unknown) {
      toastState.error(`Download failed: ${errorMessage(e)}`);
    } finally {
      downloading = false;
    }
  }

  async function handleDownloadCl() {
    if (!selectedCl) return;
    downloading = true;
    try {
      const blob = await generateCoverLetterPdf({ text: selectedCl.cover_letter_text });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'cover-letter.pdf';
      a.click();
      URL.revokeObjectURL(url);
      toastState.success('Cover Letter Downloaded!');
    } catch (e: unknown) {
      toastState.error(`Download failed: ${errorMessage(e)}`);
    } finally {
      downloading = false;
    }
  }

  function displayCompany(entry: GeneratedCoverLetterEntry): string {
    if (entry.company_name) return entry.company_name;
    // Strip common prefixes like "Title:", "Position:", etc.
    const firstLine = entry.job_description.split('\n')[0].trim()
      .replace(/^(title|job title|position|role)\s*:\s*/i, '');
    // "Role at Company..." → extract company after "at"
    const atMatch = firstLine.match(/\bat\s+([^,(\n]+)/i);
    if (atMatch) return atMatch[1].trim().slice(0, 30);
    // "Role - Company..." → extract first word(s) after dash
    const dashMatch = firstLine.match(/\s[-–]\s*([A-Za-z]\S+)/);
    if (dashMatch) return dashMatch[1].slice(0, 30);
    return firstLine.length > 30 ? firstLine.slice(0, 27) + '…' : firstLine;
  }

  function displayRole(entry: GeneratedCoverLetterEntry): string {
    const firstLine = entry.job_description.split('\n')[0].trim()
      .replace(/^(title|job title|position|role)\s*:\s*/i, '');
    if (!firstLine) return '';
    // Strip " - Company" suffix to show just the role
    const clean = firstLine.replace(/\s[-–]\s*\S+.*$/, '').trim();
    const text = clean || firstLine;
    return text.length > 50 ? text.slice(0, 47) + '…' : text;
  }

  function getMatchBgClass(score: number): string {
    return getScoreColor(score).bg;
  }

  function scoreColorClass(score: number): string {
    const colors = getScoreColor(score);
    return `${colors.bg} ${colors.text}`;
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

  <!-- Tabs (Segmented Control Style) -->
  <div class="flex p-1 bg-muted/40 rounded-xl w-fit border border-border/50 shadow-sm">
    <button
      class="px-6 py-2 rounded-lg text-sm font-bold transition-all
        {tab === 'cv' ? 'bg-background text-foreground shadow-sm ring-1 ring-border/50' : 'text-muted-foreground hover:text-foreground hover:bg-muted/60'}"
      onclick={() => { tab = 'cv'; selectedCv = null; }}
    >
      Generated CVs <span class="ml-1 text-[10px] opacity-60 bg-muted px-1.5 py-0.5 rounded-md">{loading ? '…' : cvItems.length}</span>
    </button>
    <button
      class="px-6 py-2 rounded-lg text-sm font-bold transition-all
        {tab === 'cover-letter' ? 'bg-background text-foreground shadow-sm ring-1 ring-border/50' : 'text-muted-foreground hover:text-foreground hover:bg-muted/60'}"
      onclick={() => { tab = 'cover-letter'; selectedCl = null; }}
    >
      Cover Letters <span class="ml-1 text-[10px] opacity-60 bg-muted px-1.5 py-0.5 rounded-md">{loading ? '…' : clItems.length}</span>
    </button>
  </div>

  {#if loading}
    <div class="grid gap-4 lg:grid-cols-[280px_1fr]">
      <div class="space-y-2">
        {#each Array(3) as _}
          <div class="border rounded-lg p-3">
            <Skeleton class="h-4 w-20 mb-2" />
            <Skeleton class="h-3 w-16" />
          </div>
        {/each}
      </div>
      <div class="border rounded-lg p-8">
        <Skeleton class="h-6 w-48 mx-auto mb-4" />
        <Skeleton class="h-4 w-full mb-2" />
        <Skeleton class="h-4 w-3/4 mb-4" />
        <Skeleton class="h-4 w-full mb-2" />
        <Skeleton class="h-4 w-5/6" />
      </div>
    </div>
  {:else if errorMsg}
    <EmptyState
      icon={Clock}
      iconClass="text-destructive"
      iconBg="bg-destructive/10"
      title="Failed to load history"
      description={errorMsg}
    />
  {:else}

    {#if tab === 'cv'}
      {#if cvItems.length === 0}
        <EmptyState
          icon={FileText}
          title="No CVs generated yet"
          description={filterProfileId != null ? 'Generate a CV for this profile.' : 'Create your first CV to see it here.'}
        >
          <Button href="/generate" size="sm">Generate CV</Button>
        </EmptyState>
      {:else}
        <div class="grid gap-4 lg:grid-cols-[280px_1fr]">
          <div class="space-y-2">
            {#each cvItems as entry}
              <CvCard
                {entry}
                selected={selectedCv?.id === entry.id}
                onSelect={() => selectedCv = entry}
              />
            {/each}
          </div>

          {#if selectedCv}
            <div class="border rounded-lg overflow-hidden bg-white dark:bg-zinc-950/40 print:bg-white shadow-sm transition-colors">
              <div class="flex items-center justify-between gap-2 p-3 border-b bg-muted/30">
                <span class="text-sm text-muted-foreground">{formatDate(selectedCv.created_at)}</span>
                <div class="flex gap-2">
                  <Button variant="outline" size="sm" onclick={handleDownloadCv} disabled={downloading}>
                    <Download class="w-4 h-4 mr-1" />
                    {downloading ? 'Downloading…' : 'Download'}
                  </Button>
                  <Button variant="outline" size="sm" onclick={() => selectedCv && handleRegenerate(selectedCv)}>
                    <Sparkles class="w-4 h-4 mr-1" /> Regenerate
                  </Button>
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
            <EmptyState
              icon={FileText}
              iconClass="text-muted-foreground"
              title="Select a CV to preview"
              description="Choose a CV from the list to see the details."
            />
          {/if}
        </div>
      {/if}
    {/if}

    {#if tab === 'cover-letter'}
      {#if clItems.length === 0}
        <EmptyState
          icon={FileText}
          title="No cover letters generated yet"
          description={filterProfileId != null ? 'Write a cover letter for this profile.' : 'Create your first cover letter to see it here.'}
        >
          <Button href="/cover-letter" size="sm">Write Cover Letter</Button>
        </EmptyState>
      {:else}
        <!-- Filter bar -->
        <div class="flex items-center gap-2 flex-wrap mb-4">
          <input
            class="flex-1 min-w-40 bg-card border border-border rounded-md px-3 py-1.5 text-sm"
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

        <!-- Gmail two-column layout -->
        <div class="grid md:grid-cols-[360px_1fr] h-[calc(100vh-260px)] overflow-hidden border-t border-border">

          <!-- LEFT: Sidebar (card list) -->
          <div class="overflow-y-auto border-r border-border bg-muted/20 {selectedCl ? 'hidden md:block' : ''}">
            <div class="p-2 space-y-1.5">
              {#each clItems as entry}
                <ClCard
                  {entry}
                  selected={selectedCl?.id === entry.id}
                  onSelect={() => selectedCl = entry}
                  selectedForBatch={selectedClIds.has(entry.id)}
                  onToggleBatchSelect={() => {
                    const s = new Set(selectedClIds);
                    if (s.has(entry.id)) s.delete(entry.id); else s.add(entry.id);
                    selectedClIds = s;
                  }}
                  onStatusChange={handleClStatusChange}
                />
              {/each}
            </div>
          </div>

          <!-- RIGHT: Preview panel -->
          <div class="flex flex-col overflow-hidden">
            {#if !selectedCl}
              <!-- Empty state -->
              <div class="flex-1 flex flex-col items-center justify-center gap-2 text-muted-foreground">
                <span class="text-4xl">📄</span>
                <p class="text-sm font-medium">Select a cover letter to preview</p>
                <p class="text-xs text-muted-foreground/70">Click any card on the left</p>
              </div>
            {:else}
              <ClPreviewHeader
                {selectedCl}
                onClose={() => selectedCl = null}
                onDownload={handleDownloadCl}
                {downloading}
                onCopy={handleCopyCl}
                onDelete={() => selectedCl && handleDeleteCl(selectedCl.id)}
              />

              <!-- Tab bar (only when fit_analysis available) -->
              {#if selectedCl.fit_analysis}
                <div class="flex border-b border-border shrink-0 bg-background">
                  <button
                    class="px-4 py-2 text-sm font-medium transition-colors
                      {previewTab === 'letter' ? 'border-b-2 border-primary text-foreground' : 'text-muted-foreground hover:text-foreground'}"
                    onclick={() => (previewTab = 'letter')}
                  >📄 Cover Letter</button>
                  <button
                    class="px-4 py-2 text-sm font-medium transition-colors
                      {previewTab === 'analysis' ? 'border-b-2 border-primary text-foreground' : 'text-muted-foreground hover:text-foreground'}"
                    onclick={() => (previewTab = 'analysis')}
                  >📊 Fit Analysis</button>
                </div>
              {/if}

              <!-- Scrollable content -->
              <div class="overflow-y-auto flex-1 bg-muted/10 relative">
                {#if previewTab === 'letter' || !selectedCl.fit_analysis}
                  <div class="p-6 md:p-8 max-w-4xl mx-auto">
                    <div class="bg-card border border-border/60 rounded-xl shadow-sm p-6 sm:p-8 md:p-10">
                      <CoverLetterPreview text={selectedCl.cover_letter_text} />
                    </div>
                  </div>
                {:else}
                  <div class="h-full">
                    <FitAnalysisTab analysis={selectedCl.fit_analysis} />
                  </div>
                {/if}
              </div>
            {/if}
          </div>

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
