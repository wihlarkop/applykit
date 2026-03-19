<script lang="ts">
	import { DATE_RANGES, MATCH_FILTERS, SORT_OPTIONS } from '$lib/constants';

	interface FilterBarFeatures {
		dateRange?: boolean;
		sort?: boolean;
		bulkDelete?: boolean;
	}

	interface Props {
		search?: string;
		dateRange?: string;
		matchFilter?: string;
		sortBy?: string;
		features?: FilterBarFeatures;
		selectedCount?: number;
		searchPlaceholder?: string;
		onsearch?: (value: string) => void;
		ondatechange?: (value: string) => void;
		onmatchchange?: (value: string) => void;
		onsortchange?: (value: string) => void;
		onbulkdelete?: () => void;
	}

	let {
		search = $bindable(''),
		dateRange = $bindable('all'),
		matchFilter = $bindable('all'),
		sortBy = $bindable('date_desc'),
		features = {},
		selectedCount = 0,
		searchPlaceholder = '🔍 Search company or role...',
		onsearch,
		ondatechange,
		onmatchchange,
		onsortchange,
		onbulkdelete,
	}: Props = $props();

	function handleSearchInput(e: Event) {
		const target = e.target as HTMLInputElement;
		search = target.value;
		onsearch?.(target.value);
	}
</script>

<div class="flex items-center gap-2 flex-wrap mb-4">
	<input
		class="flex-1 min-w-40 bg-card border border-border rounded-md px-3 py-1.5 text-sm"
		placeholder={searchPlaceholder}
		value={search}
		oninput={handleSearchInput}
	/>

	{#if features.dateRange}
		<select
			class="bg-card border border-border rounded-md px-3 py-1.5 text-sm"
			bind:value={dateRange}
			onchange={() => ondatechange?.(dateRange)}
		>
			{#each DATE_RANGES as opt}
				<option value={opt.value}>{opt.label}</option>
			{/each}
		</select>
	{/if}

	<select
		class="bg-card border border-border rounded-md px-3 py-1.5 text-sm"
		bind:value={matchFilter}
		onchange={() => onmatchchange?.(matchFilter)}
	>
		{#each MATCH_FILTERS as opt}
			<option value={opt.value}>{opt.label}</option>
		{/each}
	</select>

	{#if features.sort}
		<select
			class="bg-card border border-border rounded-md px-3 py-1.5 text-sm"
			bind:value={sortBy}
			onchange={() => onsortchange?.(sortBy)}
		>
			{#each SORT_OPTIONS as opt}
				<option value={opt.value}>{opt.label}</option>
			{/each}
		</select>
	{/if}

	{#if features.bulkDelete && selectedCount > 0}
		<button
			onclick={onbulkdelete}
			class="px-3 py-1.5 text-sm bg-destructive text-destructive-foreground rounded-md hover:bg-destructive/90"
		>
			Delete selected ({selectedCount})
		</button>
	{/if}
</div>
