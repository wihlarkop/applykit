<script lang="ts">
  import type { ApplicationEntry } from '$lib/types';

  let { app, onclick }: { app: ApplicationEntry; onclick: () => void } = $props();

  const matchColor = $derived(
    app.match_score === null
      ? null
      : app.match_score >= 70
        ? 'text-green-500 bg-green-500/10'
        : app.match_score >= 40
          ? 'text-yellow-500 bg-yellow-500/10'
          : 'text-red-500 bg-red-500/10'
  );

  const formatDate = (d: string | null) =>
    d ? new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : null;
</script>

<button
  type="button"
  onclick={onclick}
  class="w-full text-left bg-card border border-border rounded-lg p-3 cursor-pointer hover:border-primary/50 transition-colors group"
  class:border-dashed={!app.linked_cover_letter_id && !app.linked_cv_id}
>
  <div class="flex items-center gap-2 mb-1">
    <span
      class="w-2 h-2 rounded-full flex-shrink-0"
      style="background-color: {app.profile_color ?? '#6366f1'}"
    ></span>
    <span class="text-sm font-semibold truncate">{app.company_name}</span>
  </div>

  <p class="text-xs text-muted-foreground mb-2 pl-4 truncate">{app.role_title || '—'}</p>

  <div class="flex items-center justify-between pl-4">
    <span class="text-[10px] text-muted-foreground">{formatDate(app.applied_date) ?? ''}</span>
    <div class="flex items-center gap-1">
      {#if app.match_score !== null}
        <span class="text-[10px] font-medium px-1.5 py-0.5 rounded {matchColor}">
          {app.match_score}%
        </span>
      {/if}
      {#if app.linked_cover_letter_id}
        <span class="text-[10px] bg-blue-500/10 text-blue-400 px-1.5 py-0.5 rounded">CL</span>
      {/if}
      {#if app.linked_cv_id}
        <span class="text-[10px] bg-purple-500/10 text-purple-400 px-1.5 py-0.5 rounded">CV</span>
      {/if}
    </div>
  </div>

  {#if !app.linked_cover_letter_id && !app.linked_cv_id}
    <p class="text-[10px] text-muted-foreground/50 pl-4 mt-1 italic">no docs linked</p>
  {/if}
</button>
