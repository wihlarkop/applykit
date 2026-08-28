<script lang="ts">
	import type { ApplicationEntry } from '$lib/types';
	import { STATUS_CONFIG } from '$lib/constants';
	import { formatDateShort, getScoreColor, errorMessage } from '$lib/utils';
	import { compareApplications, type ApplicationSortColumn, type SortDirection } from '$lib/tracker-sort';
	import { updateApplication } from '$lib/api';
	import { toastState } from '$lib/toast.svelte';
	import { ArrowUpDown, ChevronUp, ChevronDown } from '@lucide/svelte';

	let {
		apps,
		onSelect,
		onUpdate
	}: {
		apps: ApplicationEntry[];
		onSelect: (app: ApplicationEntry) => void;
		onUpdate: (updated: ApplicationEntry) => void;
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
</script>

<div class="bg-card border border-border rounded-xl overflow-x-auto">
	<table class="w-full text-sm">
		<thead>
			<tr class="border-b border-border">
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
				>
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
