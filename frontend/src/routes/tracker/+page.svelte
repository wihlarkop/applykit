<script lang="ts">
  import { page } from '$app/state';
  import {
    createApplication,
    deleteApplication,
    listApplications,
    updateApplication,
    type ApplicationFilters,
  } from '$lib/api';
  import ApplicationCard from '$lib/components/tracker/ApplicationCard.svelte';
  import DetailPanel from '$lib/components/tracker/DetailPanel.svelte';
  import { toastState } from '$lib/toast.svelte';
  import type { ApplicationEntry, ApplicationStatus, CreateApplicationRequest } from '$lib/types';
  import { dndzone } from 'svelte-dnd-action';
  import { flip } from 'svelte/animate';

  // --- State ---
  let apps = $state<ApplicationEntry[]>([]);
  let loading = $state(true);
  let selectedApp = $state<ApplicationEntry | null>(null);

  // Filters
  let search = $state('');
  let dateRange = $state<'all' | 'week' | 'month' | '3months'>('all');
  let matchFilter = $state<'all' | 'high' | 'medium' | 'low'>('all');
  let searchTimer: ReturnType<typeof setTimeout>;

  // Add form state (one per column)
  let addingInColumn = $state<ApplicationStatus | null>(null);
  let newCompany = $state('');
  let newRole = $state('');
  let newDate = $state(new Date().toISOString().split('T')[0]);

  const COLUMNS: { status: ApplicationStatus; label: string; color: string }[] = [
    { status: 'applied', label: 'Applied', color: 'text-muted-foreground' },
    { status: 'interviewing', label: 'Interviewing', color: 'text-amber-500' },
    { status: 'offer', label: 'Offer', color: 'text-green-500' },
    { status: 'rejected', label: 'Rejected', color: 'text-red-500' },
  ];

  // --- Derived ---
  const colItems = $derived(
    Object.fromEntries(
      COLUMNS.map((c) => [c.status, apps.filter((a) => a.status === c.status)])
    ) as Record<ApplicationStatus, ApplicationEntry[]>
  );

  // --- Data loading ---
  async function load() {
    loading = true;
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
    } catch (e: any) {
      toastState.error(e.message);
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
    const draggedApp: ApplicationEntry = e.detail.items.find(
      (i: ApplicationEntry) => i.id === e.detail.info.id
    ) ?? e.detail.items[0];
    if (!draggedApp) return;

    const updated = apps.filter((a) => a.status !== status);
    const newItems = e.detail.items.map((i: ApplicationEntry) => ({ ...i, status }));
    apps = [...updated, ...newItems];

    try {
      await updateApplication(draggedApp.id, { status });
    } catch (err: any) {
      toastState.error(err.message);
      await load(); // revert on error
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
    } catch (e: any) {
      toastState.error(e.message);
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

<div class="space-y-4 transition-[padding-right] duration-200 {selectedApp ? 'pr-[376px]' : ''}"
>
  <div class="flex items-center justify-between">
    <h1 class="text-2xl font-bold">Application Tracker</h1>
  </div>

  <!-- Filter bar -->
  <div class="flex items-center gap-3 flex-wrap">
    <input
      class="flex-1 min-w-[200px] bg-card border border-border rounded-md px-3 py-2 text-sm"
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
  </div>

  {#if loading}
    <div class="grid grid-cols-4 gap-4">
      {#each COLUMNS as _}
        <div class="bg-card border border-border rounded-xl p-3 h-64 animate-pulse"></div>
      {/each}
    </div>
  {:else}
    <!-- Kanban board -->
    <div class="grid grid-cols-4 gap-4 items-start">
      {#each COLUMNS as col}
        {@const items = colItems[col.status] ?? []}
        <div class="bg-card border border-border rounded-xl p-3 flex flex-col">
          <!-- Column header -->
          <div class="flex items-center justify-between mb-3">
            <span class="text-xs font-semibold uppercase tracking-wide {col.color}">{col.label}</span>
            <span class="text-xs text-muted-foreground bg-muted rounded-full px-2 py-0.5">{items.length}</span>
          </div>

          <!-- Cards (dnd zone) -->
          <div
            class="flex flex-col gap-2 min-h-[120px] max-h-[60vh] overflow-y-auto"
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
