<script lang="ts">
	import type { ApplicationEntry, ApplicationStatus } from '$lib/types';
	import { STATUS_CONFIG, STATUS_OPTIONS } from '$lib/constants';

	let {
		apps,
		activeStatus,
		onSelect
	}: {
		apps: ApplicationEntry[];
		activeStatus: ApplicationStatus | null;
		onSelect: (status: ApplicationStatus | null) => void;
	} = $props();

	const STAGES = STATUS_OPTIONS.filter(
		(o): o is { value: ApplicationStatus; label: string } => o.value !== null
	);

	const counts = $derived(
		Object.fromEntries(
			STAGES.map((s) => [s.value, apps.filter((a) => a.status === s.value).length])
		) as Record<ApplicationStatus, number>
	);
</script>

<div class="flex items-stretch gap-2 flex-wrap">
	{#each STAGES as stage}
		{@const isActive = activeStatus === stage.value}
		<button
			type="button"
			onclick={() => onSelect(isActive ? null : stage.value)}
			class="flex-1 min-w-32 flex flex-col items-center gap-0.5 py-2.5 rounded-lg border transition-colors
				{isActive ? STATUS_CONFIG[stage.value].activeClass : 'border-border text-muted-foreground hover:text-foreground hover:bg-accent'}"
		>
			<span class="text-xl font-black">{counts[stage.value]}</span>
			<span class="text-[10px] font-bold uppercase tracking-widest">{stage.label}</span>
		</button>
	{/each}
</div>
