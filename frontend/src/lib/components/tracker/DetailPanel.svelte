<script lang="ts">
  import {
    deleteApplication,
    updateApplication,
  } from '$lib/api';
  import { toastState } from '$lib/toast.svelte';
  import type { ApplicationEntry, ApplicationStatus, UpdateApplicationRequest } from '$lib/types';

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

  async function patch(data: UpdateApplicationRequest) {
    try {
      saving = true;
      const updated = await updateApplication(app.id, data);
      onupdate(updated);
    } catch (e: any) {
      toastState.error(e.message);
    } finally {
      saving = false;
    }
  }

  async function handleDelete() {
    try {
      await deleteApplication(app.id);
      ondelete(app.id);
    } catch (e: any) {
      toastState.error(e.message);
    }
  }
</script>

<div
  class="fixed inset-y-0 right-0 w-96 bg-card border-l border-border shadow-xl z-50 flex flex-col animate-in slide-in-from-right duration-300"
>
  <!-- Header -->
  <div class="flex items-start justify-between p-4 border-b border-border">
    <div class="flex-1 min-w-0 pr-3">
      <h2 class="font-semibold truncate">{app.company_name}</h2>
      <p class="text-sm text-muted-foreground truncate">{app.role_title || '—'}</p>
    </div>
    <button onclick={onclose} class="text-muted-foreground hover:text-foreground p-1 rounded">✕</button>
  </div>

  <!-- Body -->
  <div class="flex-1 overflow-y-auto p-4 space-y-4">
    <!-- Status -->
    <div>
      <label class="text-xs font-medium text-muted-foreground uppercase tracking-wide block mb-1">Status</label>
      <select
        class="w-full bg-background border border-border rounded-md px-3 py-2 text-sm"
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
      <label class="text-xs font-medium text-muted-foreground uppercase tracking-wide block mb-1">Company</label>
      <input
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
      <label class="text-xs font-medium text-muted-foreground uppercase tracking-wide block mb-1">Role</label>
      <input
        class="w-full bg-background border border-border rounded-md px-3 py-2 text-sm"
        value={app.role_title}
        onblur={(e) => {
          const v = (e.target as HTMLInputElement).value;
          if (v !== app.role_title) patch({ role_title: v });
        }}
      />
    </div>

    <!-- Applied date -->
    <div>
      <label class="text-xs font-medium text-muted-foreground uppercase tracking-wide block mb-1">Applied date</label>
      <input
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
      <label class="text-xs font-medium text-muted-foreground uppercase tracking-wide block mb-1">Job URL</label>
      <input
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
      <label class="text-xs font-medium text-muted-foreground uppercase tracking-wide block mb-1">Notes</label>
      <textarea
        class="w-full bg-background border border-border rounded-md px-3 py-2 text-sm min-h-[80px] resize-none"
        placeholder="Add notes..."
        onblur={(e) => {
          const v = (e.target as HTMLTextAreaElement).value || null;
          if (v !== app.notes) patch({ notes: v });
        }}
      >{app.notes ?? ''}</textarea>
    </div>

    <!-- Linked Documents -->
    {#if app.linked_cover_letter_id || app.linked_cv_id}
      <div>
        <p class="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">Linked Documents</p>
        {#if app.linked_cover_letter_id}
          <a
            href="/history?cl={app.linked_cover_letter_id}"
            class="flex items-center gap-2 text-sm text-primary hover:underline mb-1"
          >
            📄 Cover Letter
          </a>
        {/if}
        {#if app.linked_cv_id}
          <a
            href="/history?cv={app.linked_cv_id}"
            class="flex items-center gap-2 text-sm text-primary hover:underline"
          >
            📋 CV
          </a>
        {/if}
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
        class="w-full text-destructive border border-destructive/30 text-sm py-2 rounded-md hover:bg-destructive/10"
      >Delete Application</button>
    {/if}
  </div>
</div>

<!-- Backdrop -->
<button
  type="button"
  class="fixed inset-0 z-40 bg-black/20"
  onclick={onclose}
  aria-label="Close panel"
></button>
