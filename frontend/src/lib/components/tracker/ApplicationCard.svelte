<script lang="ts">
	import type { ApplicationEntry } from '$lib/types';
	import { formatDateShort, getScoreColor } from '$lib/utils';

	let { app, onclick }: { app: ApplicationEntry; onclick: () => void } = $props();

	const matchColor = $derived(
		app.match_score === null
			? null
			: `${getScoreColor(app.match_score).text} ${getScoreColor(app.match_score).bg}`
	);
</script>

<button
	type="button"
	onclick={onclick}
	class="w-full text-left bg-card border border-border rounded-lg p-3 cursor-pointer hover:border-primary/50 hover:shadow-sm transition-all group relative overflow-hidden"
	class:border-dashed={!app.linked_cover_letter_id && !app.linked_cv_id}
>
	<!-- Status Dot & Company -->
	<div class="flex items-center gap-2 mb-1.5">
		<span
			class="w-2 h-2 rounded-full shrink-0 shadow-sm"
			style="background-color: {app.profile_color ?? '#6366f1'}"
		></span>
		<span class="text-sm font-bold truncate group-hover:text-primary transition-colors">
			{app.company_name}
		</span>
	</div>

	<p class="text-xs text-muted-foreground mb-2 pl-4 truncate">{app.role_title || '—'}</p>

	<!-- Date & Indicators -->
	<div class="flex items-center justify-between pl-4 mt-1">
		<span class="text-[10px] font-medium text-muted-foreground/70">
			{formatDateShort(app.applied_date ?? '') ?? ''}
		</span>
		<div class="flex items-center gap-1.5">
			{#if app.linked_cover_letter_id}
				<span class="text-[9px] font-bold bg-blue-500/10 text-blue-500 px-1.5 py-0.5 rounded-sm border border-blue-500/20" title="Cover Letter Linked">
					CL
				</span>
			{/if}
			{#if app.linked_cv_id}
				<span class="text-[9px] font-bold bg-purple-500/10 text-purple-500 px-1.5 py-0.5 rounded-sm border border-purple-500/20" title="CV Linked">
					CV
				</span>
			{/if}
		</div>
	</div>

	<!-- Match Score Progress Bar -->
	{#if app.match_score !== null}
		<div class="mt-3 pl-4 space-y-1">
			<div class="flex items-center justify-between text-[9px] font-semibold">
				<span class="text-muted-foreground/60 uppercase tracking-tighter">Match</span>
				<span class={getScoreColor(app.match_score).text}>{app.match_score}%</span>
			</div>
			<div class="h-1 w-full bg-muted rounded-full overflow-hidden">
				<div 
					class="h-full transition-all duration-500 {getScoreColor(app.match_score).bg}"
					style="width: {app.match_score}%"
				></div>
			</div>
		</div>
	{/if}

	{#if !app.linked_cover_letter_id && !app.linked_cv_id}
		<p class="text-[10px] text-muted-foreground/50 pl-4 mt-1 italic">no docs linked</p>
	{/if}
</button>
