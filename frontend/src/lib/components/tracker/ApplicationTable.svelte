<script lang="ts">
	import type { ApplicationEntry, ApplicationStatus } from '$lib/types';
	import { STATUS_CONFIG, STATUS_OPTIONS } from '$lib/constants';
	import { formatDateShort, getScoreColor, errorMessage } from '$lib/utils';
	import { compareApplications, type ApplicationSortColumn, type SortDirection } from '$lib/tracker-sort';
	import { updateApplication, deleteApplication } from '$lib/api';
	import { toastState } from '$lib/toast.svelte';
	import { ArrowUpDown, ChevronUp, ChevronDown, Trash2 } from '@lucide/svelte';

	let {
		apps,
		onSelect,
		onUpdate,
		onBulkUpdate,
		onBulkDelete
	}: {
		apps: ApplicationEntry[];
		onSelect: (app: ApplicationEntry) => void;
		onUpdate: (updated: ApplicationEntry) => void;
		onBulkUpdate: (updated: ApplicationEntry[]) => void;
		onBulkDelete: (ids: number[]) => void;
	} = $props();

	let sortColumn = $state<ApplicationSortColumn>('applied_date');
	let sortDirection = $state<SortDirection>('desc');

	const COLUMNS: { key: ApplicationSortColumn; label: string }[] = [
		{ key: 'company_name', label: 'Company' },
		{ key: 'role_title', label: 'Role' },
		{ key: 'status', label: 'Status' },
		{ key: 'salary', label: 'Salary' },
		{ key: 'location', label: 'Location' },
		{ key: 'match_score', label: 'Match' },
		{ key: 'applied_date', label: 'Applied' },
	];

	function toggleSort(col: ApplicationSortColumn) {
		if (sortColumn === col) {
			sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
		} else {
			sortColumn = col;
			sortDirection = 'asc';
		}
	}

	const sortedApps = $derived(
		[...apps].sort((a, b) => compareApplications(a, b, sortColumn, sortDirection))
	);

	// --- Inline quick-edit for location / applied_date ---
	type EditableField = 'location' | 'applied_date';
	let editingCell = $state<{ id: number; field: EditableField } | null>(null);
	let editValue = $state('');

	function focusOnMount(node: HTMLInputElement) {
		node.focus();
		node.select();
	}

	function startEdit(app: ApplicationEntry, field: EditableField) {
		editingCell = { id: app.id, field };
		editValue = app[field] ?? '';
	}

	function cancelEdit() {
		editingCell = null;
	}

	async function saveEdit(app: ApplicationEntry) {
		const cell = editingCell;
		if (!cell) return;
		editingCell = null;

		const value = editValue.trim() || null;
		if (value === (app[cell.field] ?? null)) return;

		try {
			const updated = await updateApplication(app.id, { [cell.field]: value });
			onUpdate(updated);
		} catch (e: unknown) {
			toastState.error(errorMessage(e));
		}
	}

	function onEditKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') (e.currentTarget as HTMLInputElement).blur();
		else if (e.key === 'Escape') cancelEdit();
	}

	// --- Bulk selection ---
	let selected = $state<Set<number>>(new Set());
	let confirmBulkDelete = $state(false);
	let bulkBusy = $state(false);
	const BULK_STATUS_OPTIONS = STATUS_OPTIONS.filter(
		(o): o is { value: ApplicationStatus; label: string } => o.value !== null
	);

	// Drop selections for rows that are no longer in view (filtered out, deleted, etc.)
	$effect(() => {
		const validIds = new Set(apps.map((a) => a.id));
		if ([...selected].some((id) => !validIds.has(id))) {
			selected = new Set([...selected].filter((id) => validIds.has(id)));
		}
	});

	const allSelected = $derived(sortedApps.length > 0 && selected.size === sortedApps.length);

	function toggleRow(id: number) {
		const next = new Set(selected);
		if (next.has(id)) next.delete(id);
		else next.add(id);
		selected = next;
	}

	function toggleAll() {
		selected = allSelected ? new Set() : new Set(sortedApps.map((a) => a.id));
	}

	function clearSelection() {
		selected = new Set();
		confirmBulkDelete = false;
	}

	async function bulkSetStatus(status: ApplicationStatus) {
		const ids = [...selected];
		if (ids.length === 0) return;
		bulkBusy = true;
		try {
			const results = await Promise.allSettled(ids.map((id) => updateApplication(id, { status })));
			const succeeded = results
				.filter((r): r is PromiseFulfilledResult<ApplicationEntry> => r.status === 'fulfilled')
				.map((r) => r.value);
			if (succeeded.length > 0) onBulkUpdate(succeeded);
			const failedCount = results.length - succeeded.length;
			if (failedCount > 0) {
				toastState.error(`Failed to update ${failedCount} application${failedCount === 1 ? '' : 's'}`);
			}
			clearSelection();
		} finally {
			bulkBusy = false;
		}
	}

	async function bulkDelete() {
		const ids = [...selected];
		if (ids.length === 0) return;
		bulkBusy = true;
		try {
			const results = await Promise.allSettled(ids.map((id) => deleteApplication(id)));
			const succeededIds = ids.filter((_, i) => results[i].status === 'fulfilled');
			if (succeededIds.length > 0) onBulkDelete(succeededIds);
			const failedCount = ids.length - succeededIds.length;
			if (failedCount > 0) {
				toastState.error(`Failed to delete ${failedCount} application${failedCount === 1 ? '' : 's'}`);
			}
			clearSelection();
		} finally {
			bulkBusy = false;
		}
	}
</script>

{#if selected.size > 0}
	<div class="flex items-center gap-2 mb-2 px-3 py-2 bg-accent/50 border border-border rounded-lg text-sm">
		<span class="text-xs font-bold text-muted-foreground">{selected.size} selected</span>

		{#if confirmBulkDelete}
			<span class="text-xs font-bold text-destructive">Delete {selected.size} application{selected.size === 1 ? '' : 's'}?</span>
			<button
				type="button"
				disabled={bulkBusy}
				onclick={bulkDelete}
				class="bg-destructive text-destructive-foreground text-xs font-bold px-2.5 py-1 rounded-md hover:bg-destructive/90 transition-colors disabled:opacity-50"
			>Confirm</button>
			<button
				type="button"
				onclick={() => (confirmBulkDelete = false)}
				class="border border-border text-xs font-bold px-2.5 py-1 rounded-md hover:bg-accent transition-colors"
			>Cancel</button>
		{:else}
			<select
				disabled={bulkBusy}
				onchange={(e) => {
					const value = e.currentTarget.value as ApplicationStatus | '';
					if (value) bulkSetStatus(value);
					e.currentTarget.value = '';
				}}
				class="bg-card border border-border rounded-md px-2 py-1 text-xs"
			>
				<option value="">Set status…</option>
				{#each BULK_STATUS_OPTIONS as opt}
					<option value={opt.value}>{opt.label}</option>
				{/each}
			</select>
			<button
				type="button"
				disabled={bulkBusy}
				onclick={() => (confirmBulkDelete = true)}
				class="flex items-center gap-1 text-destructive/70 hover:text-destructive border border-destructive/20 text-xs font-bold px-2.5 py-1 rounded-md hover:bg-destructive/5 transition-colors disabled:opacity-50"
			>
				<Trash2 class="w-3 h-3" /> Delete
			</button>
			<button
				type="button"
				onclick={clearSelection}
				class="ml-auto text-xs text-muted-foreground hover:text-foreground"
			>Clear selection</button>
		{/if}
	</div>
{/if}

<div class="bg-card border border-border rounded-xl overflow-x-auto">
	<table class="w-full text-sm">
		<thead>
			<tr class="border-b border-border">
				<th class="px-3 py-2 w-8">
					<input
						type="checkbox"
						checked={allSelected}
						onclick={toggleAll}
						aria-label="Select all"
					/>
				</th>
				{#each COLUMNS as col}
					<th class="text-left px-3 py-2 whitespace-nowrap">
						<button
							type="button"
							onclick={() => toggleSort(col.key)}
							class="flex items-center gap-1 text-[10px] font-black uppercase tracking-widest text-muted-foreground hover:text-foreground transition-colors"
						>
							{col.label}
							{#if sortColumn === col.key}
								{#if sortDirection === 'asc'}
									<ChevronUp class="w-3 h-3" />
								{:else}
									<ChevronDown class="w-3 h-3" />
								{/if}
							{:else}
								<ArrowUpDown class="w-3 h-3 opacity-30" />
							{/if}
						</button>
					</th>
				{/each}
			</tr>
		</thead>
		<tbody>
			{#each sortedApps as app (app.id)}
				<tr
					onclick={() => onSelect(app)}
					class="border-b border-border/40 last:border-0 cursor-pointer hover:bg-accent/50 transition-colors"
					class:bg-accent={selected.has(app.id)}
				>
					<td class="px-3 py-2" onclick={(e) => e.stopPropagation()}>
						<input
							type="checkbox"
							checked={selected.has(app.id)}
							onclick={() => toggleRow(app.id)}
							aria-label="Select {app.company_name}"
						/>
					</td>
					<td class="px-3 py-2 font-semibold whitespace-nowrap">{app.company_name}</td>
					<td class="px-3 py-2 text-muted-foreground whitespace-nowrap">{app.role_title || '—'}</td>
					<td class="px-3 py-2 whitespace-nowrap">
						<span class="text-[10px] font-black uppercase tracking-widest {STATUS_CONFIG[app.status].color}">
							{STATUS_CONFIG[app.status].label}
						</span>
					</td>
					<td class="px-3 py-2 text-muted-foreground whitespace-nowrap">{app.salary || '—'}</td>
					<td class="px-3 py-2 text-muted-foreground whitespace-nowrap" onclick={(e) => e.stopPropagation()}>
						{#if editingCell?.id === app.id && editingCell.field === 'location'}
							<input
								type="text"
								class="w-full min-w-24 bg-background border border-border rounded px-1.5 py-1 text-sm"
								bind:value={editValue}
								use:focusOnMount
								onblur={() => saveEdit(app)}
								onkeydown={onEditKeydown}
							/>
						{:else}
							<button
								type="button"
								onclick={() => startEdit(app, 'location')}
								class="text-left hover:text-foreground hover:underline decoration-dotted underline-offset-2"
							>
								{app.location || 'Add location'}
							</button>
						{/if}
					</td>
					<td class="px-3 py-2 whitespace-nowrap">
						{#if app.match_score !== null}
							<span class={getScoreColor(app.match_score).text}>{app.match_score}%</span>
						{:else}
							<span class="text-muted-foreground">—</span>
						{/if}
					</td>
					<td class="px-3 py-2 text-muted-foreground whitespace-nowrap" onclick={(e) => e.stopPropagation()}>
						{#if editingCell?.id === app.id && editingCell.field === 'applied_date'}
							<input
								type="date"
								class="w-full bg-background border border-border rounded px-1.5 py-1 text-sm"
								bind:value={editValue}
								use:focusOnMount
								onblur={() => saveEdit(app)}
								onkeydown={onEditKeydown}
							/>
						{:else}
							<button
								type="button"
								onclick={() => startEdit(app, 'applied_date')}
								class="text-left hover:text-foreground hover:underline decoration-dotted underline-offset-2"
							>
								{formatDateShort(app.applied_date ?? '') || 'Add date'}
							</button>
						{/if}
					</td>
				</tr>
			{/each}
		</tbody>
	</table>
	{#if sortedApps.length === 0}
		<div class="py-12 text-center text-sm text-muted-foreground">No applications</div>
	{/if}
</div>
