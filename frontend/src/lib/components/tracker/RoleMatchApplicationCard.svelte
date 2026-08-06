<script lang="ts">
  import type { ApplicationEntry } from '$lib/types';
  import { formatDateShort, getScoreColor } from '$lib/utils';

  interface SourceAwareApplication extends ApplicationEntry {
    match_score_source?: 'role_evidence_match' | 'legacy_llm_score' | 'none';
    role_match_analysis_id?: number | null;
  }

  let { app, onclick }: { app: SourceAwareApplication; onclick: () => void } = $props();

  const sourceLabel = $derived(
    app.match_score_source === 'role_evidence_match'
      ? 'Evidence match'
      : app.match_score_source === 'legacy_llm_score'
        ? 'Legacy score'
        : 'Match',
  );
</script>

<button
  type="button"
  onclick={onclick}
  class="group relative w-full cursor-pointer overflow-hidden rounded-lg border border-border bg-card p-3 text-left transition-all hover:border-primary/50 hover:shadow-sm"
  class:border-dashed={!app.linked_cover_letter_id && !app.linked_cv_id}
>
  <div class="mb-1.5 flex items-center gap-2">
    <span
      class="h-2 w-2 shrink-0 rounded-full shadow-sm"
      style={`background-color: ${app.profile_color ?? '#6366f1'}`}
    ></span>
    <span class="truncate text-sm font-bold transition-colors group-hover:text-primary">
      {app.company_name}
    </span>
  </div>

  <p class="mb-2 truncate pl-4 text-xs text-muted-foreground">{app.role_title || '—'}</p>

  <div class="mt-1 flex items-center justify-between pl-4">
    <span class="text-[10px] font-medium text-muted-foreground/70">
      {formatDateShort(app.applied_date ?? '') ?? ''}
    </span>
    <div class="flex items-center gap-1.5">
      {#if app.linked_cover_letter_id}
        <span class="rounded-sm border border-blue-500/20 bg-blue-500/10 px-1.5 py-0.5 text-[9px] font-bold text-blue-500" title="Cover Letter Linked">CL</span>
      {/if}
      {#if app.linked_cv_id}
        <span class="rounded-sm border border-purple-500/20 bg-purple-500/10 px-1.5 py-0.5 text-[9px] font-bold text-purple-500" title="CV Linked">CV</span>
      {/if}
    </div>
  </div>

  {#if app.match_score !== null}
    <div class="mt-3 space-y-1 pl-4">
      <div class="flex items-center justify-between text-[9px] font-semibold">
        <span class="uppercase tracking-wide text-muted-foreground/70">{sourceLabel}</span>
        <span class={getScoreColor(app.match_score).text}>{app.match_score}%</span>
      </div>
      <div class="h-1 w-full overflow-hidden rounded-full bg-muted">
        <div
          class="h-full transition-all duration-500 {getScoreColor(app.match_score).bg}"
          style={`width: ${app.match_score}%`}
        ></div>
      </div>
    </div>
  {/if}

  {#if !app.linked_cover_letter_id && !app.linked_cv_id}
    <span class="mt-1 inline-flex items-center gap-1 rounded border border-yellow-200 bg-yellow-50 px-1.5 py-0.5 text-[10px] font-medium text-yellow-600 dark:border-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400">
      ⚠ No docs linked
    </span>
  {/if}
</button>
