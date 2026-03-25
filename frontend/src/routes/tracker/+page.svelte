<script lang="ts">
	import { page } from '$app/state';
	import {
	    createApplication,
	    listApplications,
	    updateApplication
	} from '$lib/api';
	import type { ApplicationFilters } from '$lib/types';
	import ApplicationCard from '$lib/components/tracker/ApplicationCard.svelte';
	import DetailPanel from '$lib/components/tracker/DetailPanel.svelte';
	import { STATUS_CONFIG } from '$lib/constants';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import { toastState } from '$lib/toast.svelte';
	import type { ApplicationEntry, ApplicationStatus, CreateApplicationRequest } from '$lib/types';
	import { errorMessage } from '$lib/utils';
	import { Briefcase, CircleAlert } from '@lucide/svelte';
	import { dndzone } from 'svelte-dnd-action';
	import { flip } from 'svelte/animate';

	let apps = $state<ApplicationEntry[]>([]);
	let loading = $state(true);
	let loadError = $state('');
	let selectedApp = $state<ApplicationEntry | null>(null);

	let search = $state('');
	let dateRange = $state('all');
	let matchFilter = $state('all');
	let searchTimer: ReturnType<typeof setTimeout>;

	let addingInColumn = $state<ApplicationStatus | null>(null);
	let newCompany = $state('');
	let newRole = $state('');
	let newDate = $state(new Date().toISOString().split('T')[0]);

	const COLUMNS: { status: ApplicationStatus; label: string; color: string }[] = [
		{ status: 'applied', label: STATUS_CONFIG.applied.label, color: 'text-muted-foreground' },
		{ status: 'interviewing', label: STATUS_CONFIG.interviewing.label, color: STATUS_CONFIG.interviewing.color },
		{ status: 'offer', label: STATUS_CONFIG.offer.label, color: STATUS_CONFIG.offer.color },
		{ status: 'rejected', label: STATUS_CONFIG.rejected.label, color: STATUS_CONFIG.rejected.color },
	];

  // --- Derived ---
  const filtersActive = $derived(search !== '' || dateRange !== 'all' || matchFilter !== 'all');
  const colItems = $derived(
    Object.fromEntries(
      COLUMNS.map((c) => [c.status, apps.filter((a) => a.status === c.status)])
    ) as Record<ApplicationStatus, ApplicationEntry[]>
  );

  // --- Data loading ---
  async function load() {
    loading = true;
    loadError = '';
    try {
      const filters: ApplicationFilters = { sort: 'date_desc' };
      if (search) filters.search = search;
      if (matchFilter === 'high') { filters.match_min = 70; }
      else if (matchFilter === 'medium') { filters.match_min = 40; filters.match_max = 69; }
      else if (matchFilter === 'low') { filters.match_max = 39; }

      const today = new Date();
      if (dateRange === 'week') {
        const d = new Date(today); d.setDate(d.getDate() - 7);
        filters.date_from = d.toISOString().split('T')[0];
      } else if (dateRange === 'month') {
        filters.date_from = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-01`;
      } else if (dateRange === '3months') {
        const d = new Date(today); d.setMonth(d.getMonth() - 3);
        filters.date_from = d.toISOString().split('T')[0];
      }

      const res = await listApplications(filters);
      apps = res.items;

      // Highlight newly created application if redirected from Smart Apply
      const newId = page.url.searchParams.get('new');
      if (newId) {
        const target = apps.find(a => a.id === Number(newId));
        if (target) selectedApp = target;
      }
    } catch (e: unknown) {
      loadError = errorMessage(e);
      toastState.error(loadError);
    } finally {
      loading = false;
    }
  }

  $effect(() => { load(); });

  function onSearchInput() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(load, 300);
  }

  // --- Drag and drop ---
  function handleDndConsider(status: ApplicationStatus, e: CustomEvent) {
    // Update local state optimistically during drag
    const updated = apps.filter((a) => a.status !== status);
    apps = [...updated, ...e.detail.items.map((i: ApplicationEntry) => ({ ...i, status }))];
  }

  async function handleDndFinalize(status: ApplicationStatus, e: CustomEvent) {
    const { items: newItems, info: { id: draggedId } } = e.detail;
    
    // Update local state
    const updated = apps.filter((a) => a.status !== status);
    apps = [...updated, ...newItems.map((i: ApplicationEntry) => ({ ...i, status }))];

    // Only update backend if the item was dropped into this column
    const isPresent = newItems.some((i: ApplicationEntry) => i.id === draggedId);
    if (isPresent) {
      try {
        await updateApplication(draggedId, { status });
      } catch (err: unknown) {
        toastState.error('Failed to update application. Please try again.');
        await load();
      }
    }
  }

  // --- Add application ---
  function startAdding(status: ApplicationStatus) {
    addingInColumn = status;
    newCompany = '';
    newRole = '';
    newDate = new Date().toISOString().split('T')[0];
  }

  async function submitAdd() {
    if (!newCompany.trim() || !addingInColumn) return;
    try {
      const req: CreateApplicationRequest = {
        company_name: newCompany.trim(),
        role_title: newRole.trim(),
        status: addingInColumn,
        applied_date: newDate || null,
      };
      const created = await createApplication(req);
      apps = [created, ...apps];
      addingInColumn = null;
    } catch (e: unknown) {
      toastState.error(errorMessage(e));
    }
  }

  // --- Detail panel ---
  function handleUpdate(updated: ApplicationEntry) {
    apps = apps.map((a) => (a.id === updated.id ? updated : a));
    selectedApp = updated;
  }

  function handleDelete(id: number) {
    apps = apps.filter((a) => a.id !== id);
    selectedApp = null;
  }
</script>

<div class="space-y-4 transition-[padding-right] duration-200 {selectedApp ? 'md:pr-94' : ''}"
>
  <div class="flex items-center justify-between mt-2">
    <div>
      <h1 class="text-3xl font-black tracking-tight">Tracker</h1>
      <p class="text-sm text-muted-foreground">Manage and track your job applications in one place.</p>
    </div>
  </div>

  <!-- Filter bar -->
  <div class="flex items-center gap-3 flex-wrap">
    <input
      class="flex-1 min-w-50 bg-card border border-border rounded-md px-3 py-2 text-sm"
      placeholder="🔍 Search company or role..."
      bind:value={search}
      oninput={onSearchInput}
    />
    <select
      class="bg-card border border-border rounded-md px-3 py-2 text-sm"
      bind:value={dateRange}
      onchange={load}
    >
      <option value="all">All time</option>
      <option value="week">This week</option>
      <option value="month">This month</option>
      <option value="3months">Last 3 months</option>
    </select>
    <select
      class="bg-card border border-border rounded-md px-3 py-2 text-sm"
      bind:value={matchFilter}
      onchange={load}
    >
      <option value="all">All matches</option>
      <option value="high">High (≥70%)</option>
      <option value="medium">Medium (40–69%)</option>
      <option value="low">Low (&lt;40%)</option>
    </select>

    {#if filtersActive}
      <button 
        onclick={() => { search = ''; dateRange = 'all'; matchFilter = 'all'; load(); }}
        class="text-xs text-primary font-bold px-2 py-1 hover:bg-primary/5 rounded-md transition-colors"
      >
        ✕ Clear filters
      </button>
    {/if}
  </div>

  {#if loading}
    <div class="grid grid-cols-4 gap-4">
      {#each COLUMNS as _}
        <div class="bg-card border border-border rounded-xl p-3 h-64 animate-pulse"></div>
      {/each}
    </div>
  {:else if loadError}
    <div class="flex flex-col items-center justify-center py-20 text-center gap-3">
      <CircleAlert class="w-8 h-8 text-destructive" />
      <p class="text-sm font-medium text-destructive">Failed to load applications</p>
      <p class="text-xs text-muted-foreground">{loadError}</p>
      <button onclick={load} class="text-xs text-primary hover:underline mt-1">Try again</button>
    </div>
  {:else if filtersActive && apps.length === 0}
    <div class="flex flex-col items-center justify-center py-20 text-center gap-3">
      <p class="text-sm font-medium text-muted-foreground">No applications match your filters</p>
      <button
        onclick={() => { search = ''; dateRange = 'all'; matchFilter = 'all'; load(); }}
        class="text-xs text-primary hover:underline"
      >Clear filters</button>
    </div>
  {:else}
    <!-- Kanban board -->
    <div class="grid grid-cols-4 gap-4 items-start">
      {#each COLUMNS as col}
        {@const items = colItems[col.status] ?? []}
        <div class="bg-card border border-border rounded-xl p-3 flex flex-col">
          <!-- Column header (sticky) -->
          <div class="sticky top-0 bg-card/95 backdrop-blur-sm z-10 flex items-center justify-between mb-3 py-1 border-b border-border/40">
            <span class="text-[10px] font-black uppercase tracking-widest {col.color}">{col.label}</span>
            <span class="text-[10px] font-bold text-muted-foreground bg-muted/50 rounded-full px-2 py-0.5 border border-border/40">{items.length}</span>
          </div>

          <!-- Cards (dnd zone) -->
          <div class="relative flex-1 flex flex-col min-h-32 mt-2">
            {#if items.length === 0}
              <div class="absolute inset-0 flex flex-col items-center justify-center py-8 text-center pointer-events-none opacity-40">
                <EmptyState
                  icon={Briefcase}
                  title="Empty"
                  description="Drop here"
                />
              </div>
            {/if}

            <div
              class="flex-1 flex flex-col gap-2 max-h-[60vh] overflow-y-auto pb-4"
              use:dndzone={{ items, flipDurationMs: 150, type: 'applications' }}
              onconsider={(e) => handleDndConsider(col.status, e)}
              onfinalize={(e) => handleDndFinalize(col.status, e)}
            >
              {#each items as app (app.id)}
                <div animate:flip={{ duration: 150 }}>
                  <ApplicationCard {app} onclick={() => (selectedApp = app)} />
                </div>
              {/each}
            </div>
          </div>

          <!-- Add form or button -->
          {#if addingInColumn === col.status}
            <form
              class="mt-3 space-y-2 border-t border-border pt-3"
              onsubmit={(e) => { e.preventDefault(); submitAdd(); }}
            >
              <input
                class="w-full bg-background border border-border rounded px-2 py-1.5 text-sm"
                placeholder="Company name *"
                bind:value={newCompany}
                required
              />
              <input
                class="w-full bg-background border border-border rounded px-2 py-1.5 text-sm"
                placeholder="Role title"
                bind:value={newRole}
              />
              <input
                type="date"
                class="w-full bg-background border border-border rounded px-2 py-1.5 text-sm"
                bind:value={newDate}
              />
              <div class="flex gap-2">
                <button
                  type="button"
                  onclick={() => (addingInColumn = null)}
                  class="flex-1 border border-border text-xs py-1.5 rounded hover:bg-accent"
                >Cancel</button>
                <button
                  type="submit"
                  class="flex-1 bg-primary text-primary-foreground text-xs py-1.5 rounded hover:bg-primary/90"
                >Add →</button>
              </div>
            </form>
          {:else}
            <button
              type="button"
              onclick={() => startAdding(col.status)}
              class="mt-3 w-full border border-dashed border-border rounded-md py-2 text-xs text-muted-foreground hover:text-foreground hover:border-muted-foreground transition-colors"
            >+ Add application</button>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>

<!-- Detail panel -->
{#if selectedApp}
  <DetailPanel
    app={selectedApp}
    onclose={() => (selectedApp = null)}
    onupdate={handleUpdate}
    ondelete={handleDelete}
  />
{/if}
