<script lang="ts">
	import { getLlmUsage, getLlmUsageStats } from '$lib/api';
	import type { LlmUsageEntry, LlmUsageStats } from '$lib/types';
	import { ArrowLeft, Calendar, Clock, Coins, Cpu, ChevronRight } from '@lucide/svelte';

	let stats: LlmUsageStats | null = $state(null);
	let usageData: { items: LlmUsageEntry[]; total: number; total_tokens: number; total_cost: number } | null = $state(null);
	let loading = $state(true);

	let dateFrom = $state('');
	let dateTo = $state('');

	let offset = $state(0);
	const limit = 20;

	async function loadData() {
		loading = true;
		try {
			const [statsRes, usageRes] = await Promise.all([
				getLlmUsageStats(),
				getLlmUsage({ date_from: dateFrom || undefined, date_to: dateTo || undefined, limit, offset }),
			]);
			stats = statsRes;
			usageData = usageRes;
		} finally {
			loading = false;
		}
	}

	async function loadMore() {
		if (!usageData) return;
		const newOffset = offset + limit;
		const res = await getLlmUsage({
			date_from: dateFrom || undefined,
			date_to: dateTo || undefined,
			limit,
			offset: newOffset,
		});
		offset = newOffset;
		usageData = {
			...res,
			items: [...usageData.items, ...res.items],
		};
	}

	function clearFilters() {
		dateFrom = '';
		dateTo = '';
		offset = 0;
		loadData();
	}

	$effect(() => {
		loadData();
	});

	function formatDate(dateStr: string) {
		return new Date(dateStr).toLocaleString();
	}

	function formatCost(cost: number | null) {
		if (cost === null) return '-';
		return `$${cost.toFixed(6)}`;
	}

	function formatTokens(tokens: number | null) {
		if (tokens === null) return '-';
		return tokens.toLocaleString();
	}

	function formatLatency(ms: number | null) {
		if (ms === null) return '-';
		return `${(ms / 1000).toFixed(2)}s`;
	}

	function operationLabel(op: string) {
		return op.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
	}
</script>

<div class="max-w-6xl mx-auto w-full px-4 py-8 space-y-6">
	<div class="flex items-center justify-between">
		<div class="flex items-center gap-3">
			<a href="/settings" class="flex items-center justify-center w-9 h-9 rounded-lg border border-border hover:bg-muted transition-colors">
				<ArrowLeft class="w-4 h-4" />
			</a>
			<div>
				<h1 class="text-2xl font-bold">LLM Usage</h1>
				<p class="text-sm text-muted-foreground">Track your AI API usage and costs</p>
			</div>
		</div>
	</div>

	{#if stats}
		<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
			<div class="bg-card border border-border rounded-xl p-5">
				<div class="flex items-center gap-2 text-sm text-muted-foreground mb-3">
					<Calendar class="w-4 h-4" />
					Today
				</div>
				<div class="space-y-2">
					<div class="flex justify-between items-baseline">
						<span class="text-2xl font-bold font-mono">{stats.today.calls}</span>
						<span class="text-xs text-muted-foreground">calls</span>
					</div>
					<div class="flex justify-between text-sm text-muted-foreground">
						<span>{formatTokens(stats.today.tokens)} tokens</span>
						<span class="font-mono">${stats.today.cost.toFixed(4)}</span>
					</div>
				</div>
			</div>

			<div class="bg-card border border-border rounded-xl p-5">
				<div class="flex items-center gap-2 text-sm text-muted-foreground mb-3">
					<Clock class="w-4 h-4" />
					This Week
				</div>
				<div class="space-y-2">
					<div class="flex justify-between items-baseline">
						<span class="text-2xl font-bold font-mono">{stats.this_week.calls}</span>
						<span class="text-xs text-muted-foreground">calls</span>
					</div>
					<div class="flex justify-between text-sm text-muted-foreground">
						<span>{formatTokens(stats.this_week.tokens)} tokens</span>
						<span class="font-mono">${stats.this_week.cost.toFixed(4)}</span>
					</div>
				</div>
			</div>

			<div class="bg-card border border-border rounded-xl p-5">
				<div class="flex items-center gap-2 text-sm text-muted-foreground mb-3">
					<Cpu class="w-4 h-4" />
					By Operation
				</div>
				<div class="space-y-2">
					{#each stats.by_operation as op}
						<div class="flex justify-between text-sm">
							<span class="text-muted-foreground">{operationLabel(op.operation)}</span>
							<span class="font-mono font-medium">{op.count}</span>
						</div>
					{:else}
						<p class="text-sm text-muted-foreground">No data</p>
					{/each}
				</div>
			</div>
		</div>
	{/if}

	<div class="bg-card border border-border rounded-xl overflow-hidden">
		<div class="p-4 border-b border-border flex items-center gap-4 flex-wrap">
			<div class="flex items-center gap-2">
				<span class="text-sm text-muted-foreground">From:</span>
				<input
					type="date"
					bind:value={dateFrom}
					onchange={() => { offset = 0; loadData(); }}
					class="bg-background border border-border rounded-md px-3 py-1.5 text-sm"
				/>
			</div>
			<div class="flex items-center gap-2">
				<span class="text-sm text-muted-foreground">To:</span>
				<input
					type="date"
					bind:value={dateTo}
					onchange={() => { offset = 0; loadData(); }}
					class="bg-background border border-border rounded-md px-3 py-1.5 text-sm"
				/>
			</div>
			{#if dateFrom || dateTo}
				<button onclick={clearFilters} class="text-sm text-muted-foreground hover:text-foreground">
					Clear filters
				</button>
			{/if}
		</div>

		<div class="overflow-x-auto">
			<table class="w-full min-w-[600px] text-sm">
				<thead class="bg-muted/50 border-b border-border">
					<tr>
						<th class="text-left px-4 py-3 font-medium text-muted-foreground">Date</th>
						<th class="text-left px-4 py-3 font-medium text-muted-foreground">Operation</th>
						<th class="text-left px-4 py-3 font-medium text-muted-foreground">Model</th>
						<th class="text-right px-4 py-3 font-medium text-muted-foreground">Tokens</th>
						<th class="hidden sm:table-cell text-right px-4 py-3 font-medium text-muted-foreground">Cost</th>
						<th class="hidden sm:table-cell text-right px-4 py-3 font-medium text-muted-foreground">Latency</th>
						<th class="text-center px-4 py-3 font-medium text-muted-foreground">Status</th>
					</tr>
				</thead>
				<tbody>
					{#each usageData?.items ?? [] as entry (entry.id)}
						<tr class="border-b border-border/50 hover:bg-muted/30">
							<td class="px-4 py-3 text-muted-foreground whitespace-nowrap">{formatDate(entry.created_at)}</td>
							<td class="px-4 py-3">{operationLabel(entry.operation)}</td>
							<td class="px-4 py-3 font-mono text-xs">{entry.model.split('/').pop()}</td>
							<td class="px-4 py-3 text-right font-mono">{formatTokens(entry.total_tokens)}</td>
							<td class="hidden sm:table-cell px-4 py-3 text-right font-mono">{formatCost(entry.cost)}</td>
							<td class="hidden sm:table-cell px-4 py-3 text-right font-mono">{formatLatency(entry.latency_ms)}</td>
							<td class="px-4 py-3 text-center">
								{#if entry.success}
									<span class="text-xs text-green-600 dark:text-green-400">✓</span>
								{:else}
									<span class="text-xs text-red-600 dark:text-red-400" title={entry.error_message ?? ''}>✗</span>
								{/if}
							</td>
						</tr>
					{:else}
						<tr>
							<td colspan="7" class="px-4 py-8 text-center text-muted-foreground">
								No usage data found
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>

		{#if usageData && usageData.total > offset + limit}
			<div class="p-4 border-t border-border flex justify-center">
				<button onclick={loadMore} class="px-4 py-2 text-sm border border-border rounded-md hover:bg-muted flex items-center gap-2">
					<ChevronRight class="w-4 h-4" />
					Load More
				</button>
			</div>
		{/if}
	</div>
</div>
