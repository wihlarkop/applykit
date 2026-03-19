<script lang="ts">
	import { deleteApplication, updateApplication } from '$lib/api';
	import { STATUS_CONFIG } from '$lib/constants';
	import { toastState } from '$lib/toast.svelte';
	import type { ApplicationEntry, ApplicationStatus, UpdateApplicationRequest } from '$lib/types';
	import { errorMessage } from '$lib/utils';

	let {
		app,
		onclose,
		onupdate,
		ondelete,
	}: {
		app: ApplicationEntry;
		onclose: () => void;
		onupdate: (updated: ApplicationEntry) => void;
		ondelete: (id: number) => void;
	} = $props();

	const STATUS_OPTIONS: ApplicationStatus[] = ['applied', 'interviewing', 'offer', 'rejected'];

	let confirmDelete = $state(false);
	let saving = $state(false);
	let savedRecently = $state(false);
	let saveTimer: ReturnType<typeof setTimeout>;

  async function patch(data: UpdateApplicationRequest) {
    try {
      saving = true;
      const updated = await updateApplication(app.id, data);
      onupdate(updated);
      clearTimeout(saveTimer);
      savedRecently = true;
      saveTimer = setTimeout(() => (savedRecently = false), 2000);
    } catch (e: unknown) {
      toastState.error(errorMessage(e));
    } finally {
      saving = false;
    }
  }

  async function handleDelete() {
    try {
      await deleteApplication(app.id);
      ondelete(app.id);
    } catch (e: unknown) {
      toastState.error(errorMessage(e));
    }
  }
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<div
  role="complementary"
  class="fixed top-14 bottom-0 right-0 w-90 bg-card border-l border-t border-border shadow-xl z-50 flex flex-col animate-in slide-in-from-right duration-200"
  onkeydown={(e) => e.key === 'Escape' && onclose()}
>
  <!-- Header -->
  <div class="flex items-start justify-between px-4 py-3 border-b border-border bg-muted/30">
    <div class="flex-1 min-w-0 pr-3">
      <h2 class="font-semibold truncate">{app.company_name}</h2>
      <p class="text-xs text-muted-foreground truncate mt-0.5">{app.role_title || '—'}</p>
    </div>
    <div class="flex items-center gap-2 shrink-0">
      {#if saving}
        <span class="text-xs text-muted-foreground">Saving…</span>
      {:else if savedRecently}
        <span class="text-xs text-green-500">✓ Saved</span>
      {/if}
      <button
        onclick={onclose}
        class="text-muted-foreground hover:text-foreground p-1 rounded hover:bg-accent transition-colors"
        aria-label="Close panel"
      >✕</button>
    </div>
  </div>

  <!-- Body -->
  <div class="flex-1 overflow-y-auto p-4 space-y-4">
    <!-- Status -->
    <div>
      <label for="dp-status" class="text-xs font-medium text-muted-foreground block mb-1">Status</label>
      <select
        id="dp-status"
        class="w-full bg-background border border-border rounded-md px-3 py-2 text-sm font-medium {STATUS_CONFIG[app.status].color}"
        value={app.status}
        onchange={(e) => patch({ status: (e.target as HTMLSelectElement).value as ApplicationStatus })}
      >
        {#each STATUS_OPTIONS as s}
          <option value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
        {/each}
      </select>
    </div>

    <!-- Company -->
    <div>
      <label for="dp-company" class="text-xs font-medium text-muted-foreground block mb-1">Company</label>
      <input
        id="dp-company"
        class="w-full bg-background border border-border rounded-md px-3 py-2 text-sm"
        value={app.company_name}
        onblur={(e) => {
          const v = (e.target as HTMLInputElement).value.trim();
          if (v && v !== app.company_name) patch({ company_name: v });
        }}
      />
    </div>

    <!-- Role -->
    <div>
      <label for="dp-role" class="text-xs font-medium text-muted-foreground block mb-1">Role</label>
      <input
        id="dp-role"
        class="w-full bg-background border border-border rounded-md px-3 py-2 text-sm"
        placeholder="e.g. Backend Engineer"
        value={app.role_title}
        onblur={(e) => {
          const v = (e.target as HTMLInputElement).value;
          if (v !== app.role_title) patch({ role_title: v });
        }}
      />
    </div>

    <!-- Applied date -->
    <div>
      <label for="dp-date" class="text-xs font-medium text-muted-foreground block mb-1">Applied date</label>
      <input
        id="dp-date"
        type="date"
        class="w-full bg-background border border-border rounded-md px-3 py-2 text-sm"
        value={app.applied_date ?? ''}
        onblur={(e) => {
          const v = (e.target as HTMLInputElement).value || null;
          if (v !== app.applied_date) patch({ applied_date: v });
        }}
      />
    </div>

    <!-- Job URL -->
    <div>
      <label for="dp-url" class="text-xs font-medium text-muted-foreground block mb-1">Job URL</label>
      <input
        id="dp-url"
        class="w-full bg-background border border-border rounded-md px-3 py-2 text-sm"
        placeholder="https://..."
        value={app.job_url ?? ''}
        onblur={(e) => {
          const v = (e.target as HTMLInputElement).value || null;
          if (v !== app.job_url) patch({ job_url: v });
        }}
      />
    </div>

    <!-- Notes -->
    <div>
      <label for="dp-notes" class="text-xs font-medium text-muted-foreground block mb-1">Notes</label>
      <textarea
        id="dp-notes"
        class="w-full bg-background border border-border rounded-md px-3 py-2 text-sm min-h-35 resize-y"
        placeholder="Interview notes, contacts, deadlines…"
        onblur={(e) => {
          const v = (e.target as HTMLTextAreaElement).value || null;
          if (v !== app.notes) patch({ notes: v });
        }}
      >{app.notes ?? ''}</textarea>
    </div>

    <!-- Linked Documents -->
    {#if app.linked_cover_letter_id || app.linked_cv_id}
      <div>
        <p class="text-xs font-medium text-muted-foreground block mb-2">Linked documents</p>
        <div class="space-y-1">
          {#if app.linked_cover_letter_id}
            <a
              href="/history?cl={app.linked_cover_letter_id}"
              class="flex items-center gap-2 text-sm text-primary hover:underline"
            >📄 Cover Letter →</a>
          {/if}
          {#if app.linked_cv_id}
            <a
              href="/history?cv={app.linked_cv_id}"
              class="flex items-center gap-2 text-sm text-primary hover:underline"
            >📋 CV →</a>
          {/if}
        </div>
      </div>
    {/if}
  </div>

  <!-- Footer -->
  <div class="p-4 border-t border-border">
    {#if confirmDelete}
      <p class="text-sm text-muted-foreground mb-2">Delete this application?</p>
      <div class="flex gap-2">
        <button
          onclick={handleDelete}
          class="flex-1 bg-destructive text-destructive-foreground text-sm py-2 rounded-md hover:bg-destructive/90"
        >Confirm delete</button>
        <button
          onclick={() => (confirmDelete = false)}
          class="flex-1 border border-border text-sm py-2 rounded-md hover:bg-accent"
        >Cancel</button>
      </div>
    {:else}
      <button
        onclick={() => (confirmDelete = true)}
        class="w-full text-destructive border border-destructive/30 text-sm py-2 rounded-md hover:bg-destructive/10 transition-colors"
      >Delete application</button>
    {/if}
  </div>
</div>
