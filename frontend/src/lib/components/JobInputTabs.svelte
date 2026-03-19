<script lang="ts">
	import { Link } from 'lucide-svelte';
	import type { Snippet } from 'svelte';

	interface Props {
		mode?: 'paste' | 'url';
		style?: 'tabs' | 'pill';
		pasteLabel?: string;
		urlLabel?: string;
		pastePlaceholder?: string;
		urlPlaceholder?: string;
		showUrlHelper?: boolean;
		urlHelperText?: string;
		onmodechange?: (mode: 'paste' | 'url') => void;
		onscrape?: (url: string) => void;
		onscrapeclick?: () => void;
		scraping?: boolean;
		jobUrl?: string;
		jobText?: string;
		children?: Snippet;
		urlInput?: Snippet;
		pasteInput?: Snippet;
	}

	let {
		mode = $bindable('paste'),
		style = 'tabs',
		pasteLabel = 'Paste Text',
		urlLabel = 'Import URL',
		pastePlaceholder = 'Paste the full job posting here...',
		urlPlaceholder = 'https://boards.greenhouse.io/...',
		showUrlHelper = false,
		urlHelperText = 'Supports Greenhouse, Lever, and most job boards.',
		onmodechange,
		onscrape,
		onscrapeclick,
		scraping = false,
		jobUrl = $bindable(''),
		jobText = $bindable(''),
		children,
		urlInput,
		pasteInput,
	}: Props = $props();
</script>

{#if style === 'pill'}
	<div class="flex gap-1 p-1 rounded-lg bg-muted w-fit">
		<button
			onclick={() => { mode = 'url'; onmodechange?.('url'); }}
			class="px-4 py-1.5 rounded-md text-sm font-medium transition-all {mode === 'url' ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground'}"
		>
			{urlLabel}
		</button>
		<button
			onclick={() => { mode = 'paste'; onmodechange?.('paste'); }}
			class="px-4 py-1.5 rounded-md text-sm font-medium transition-all {mode === 'paste' ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground'}"
		>
			{pasteLabel}
		</button>
	</div>
{:else}
	<div class="flex gap-1 border-b border-border mb-2">
		<button
			class="px-3 py-1.5 text-sm font-medium transition-colors cursor-pointer {mode === 'paste' ? 'border-b-2 border-primary text-foreground' : 'text-muted-foreground hover:text-foreground'}"
			onclick={() => { mode = 'paste'; onmodechange?.('paste'); }}
		>
			{pasteLabel}
		</button>
		<button
			class="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium transition-colors cursor-pointer {mode === 'url' ? 'border-b-2 border-primary text-foreground' : 'text-muted-foreground hover:text-foreground'}"
			onclick={() => { mode = 'url'; onmodechange?.('url'); }}
		>
			<Link class="w-3.5 h-3.5" />
			{urlLabel}
		</button>
	</div>
{/if}

{#if mode === 'url'}
	<div class="space-y-2">
		{#if urlInput}
			{@render urlInput()}
		{:else}
			<input
				type="url"
				bind:value={jobUrl}
				placeholder={urlPlaceholder}
				class="flex-1 h-9 bg-card border border-border rounded-md px-3 py-2 text-sm"
			/>
		{/if}
		{#if showUrlHelper}
			<p class="text-xs text-muted-foreground">{urlHelperText}</p>
		{/if}
	</div>
{:else}
	{#if pasteInput}
		{@render pasteInput()}
	{:else}
		<textarea
			bind:value={jobText}
			placeholder={pastePlaceholder}
			rows={8}
			class="w-full bg-background/50 border border-border rounded-md px-3 py-2 text-sm placeholder:text-muted-foreground/50 resize-y max-h-[35vh] focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
		></textarea>
	{/if}
{/if}
