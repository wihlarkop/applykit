<script lang="ts">
	import { deleteApplication, updateApplication } from '$lib/api';
	import { STATUS_CONFIG } from '$lib/constants';
	import { toastState } from '$lib/toast.svelte';
	import type { ApplicationEntry, ApplicationStatus, UpdateApplicationRequest } from '$lib/types';
	import { errorMessage, getScoreColor } from '$lib/utils';
	import { Building2, MapPin, DollarSign, Calendar, Link, FileText, Trash2, ExternalLink } from '@lucide/svelte';

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
  <div class="flex items-start justify-between px-4 py-4 border-b border-border bg-muted/20">
    <div class="flex-1 min-w-0 pr-3">
      <div class="flex items-center gap-2 mb-0.5">
        <span class="w-2.5 h-2.5 rounded-full" style="background-color: {app.profile_color ?? '#6366f1'}"></span>
        <h2 class="font-bold text-lg truncate">{app.company_name}</h2>
      </div>
      <p class="text-xs text-muted-foreground truncate font-medium">{app.role_title || 'No Role Title'}</p>
    </div>
    <div class="flex flex-col items-end gap-1.5 shrink-0">
      <button
        onclick={onclose}
        class="text-muted-foreground hover:text-foreground p-1 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
        aria-label="Close panel"
      >✕</button>
      {#if saving}
        <span class="text-[10px] text-muted-foreground font-medium bg-muted px-1.5 py-0.5 rounded">Saving…</span>
      {:else if savedRecently}
        <span class="text-[10px] text-emerald-600 font-bold bg-emerald-500/10 px-1.5 py-0.5 rounded">✓ Saved</span>
      {/if}
    </div>
  </div>

  <!-- Body -->
  <div class="flex-1 overflow-y-auto p-4 space-y-4">
    <!-- Match & Status Section -->
    <div class="grid grid-cols-2 gap-3 pb-2">
      <div>
        <label for="dp-status" class="text-[10px] font-black uppercase tracking-wider text-muted-foreground block mb-1.5">Current Status</label>
        <select
          id="dp-status"
          class="w-full bg-background border border-border rounded-lg px-2.5 py-2 text-xs font-bold"
          value={app.status}
          onchange={(e) => patch({ status: (e.target as HTMLSelectElement).value as ApplicationStatus })}
        >
          {#each STATUS_OPTIONS as s}
            <option value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
          {/each}
        </select>
      </div>
      <div>
        <span class="text-[10px] font-black uppercase tracking-wider text-muted-foreground block mb-1.5">Match Score</span>
        {#if app.match_score !== null}
          <div class="bg-background border border-border rounded-lg p-2">
            <div class="flex items-center justify-between mb-1.5">
              <span class="text-xs font-black {getScoreColor(app.match_score).text}">{app.match_score}%</span>
            </div>
            <div class="h-1 w-full bg-muted rounded-full overflow-hidden">
              <div 
                class="h-full transition-all duration-500 {getScoreColor(app.match_score).bg}"
                style="width: {app.match_score}%"
              ></div>
            </div>
          </div>
        {:else}
          <div class="bg-muted/30 border border-dashed border-border rounded-lg p-2 text-[10px] text-muted-foreground flex items-center justify-center h-full min-h-[40px]">
            No score
          </div>
        {/if}
      </div>
    </div>

    <div class="h-px bg-border/40 my-4"></div>

    <!-- Details Section -->
    <div class="space-y-4">
      <h3 class="text-[10px] font-black uppercase tracking-widest text-muted-foreground/80 mb-4 flex items-center gap-1.5">
        <Building2 size={12} /> Company & Role Details
      </h3>
      
      <div class="space-y-3">
        <div>
          <label for="dp-company" class="text-xs font-bold text-muted-foreground/80 block mb-1.5">Company Name</label>
          <div class="relative">
            <Building2 size={14} class="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground/50" />
            <input
              id="dp-company"
              class="w-full bg-background border border-border rounded-lg pl-9 pr-3 py-2 text-sm focus:ring-1 focus:ring-primary outline-none transition-all"
              value={app.company_name}
              onblur={(e) => {
                const v = (e.target as HTMLInputElement).value.trim();
                if (v && v !== app.company_name) patch({ company_name: v });
              }}
            />
          </div>
        </div>

        <div>
          <label for="dp-role" class="text-xs font-bold text-muted-foreground/80 block mb-1.5">Position / Role</label>
          <input
            id="dp-role"
            class="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:ring-1 focus:ring-primary outline-none transition-all"
            placeholder="e.g. Backend Engineer"
            value={app.role_title}
            onblur={(e) => {
              const v = (e.target as HTMLInputElement).value;
              if (v !== app.role_title) patch({ role_title: v });
            }}
          />
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="dp-location" class="text-xs font-bold text-muted-foreground/80 block mb-1.5">Location</label>
            <div class="relative">
              <MapPin size={14} class="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground/50" />
              <input
                id="dp-location"
                class="w-full bg-background border border-border rounded-lg pl-9 pr-3 py-2 text-sm focus:ring-1 focus:ring-primary outline-none transition-all"
                placeholder="Remote, NY, etc."
                value={app.location ?? ''}
                onblur={(e) => {
                  const v = (e.target as HTMLInputElement).value || null;
                  if (v !== app.location) patch({ location: v });
                }}
              />
            </div>
          </div>
          <div>
            <label for="dp-salary" class="text-xs font-bold text-muted-foreground/80 block mb-1.5">Salary</label>
            <div class="relative">
              <DollarSign size={14} class="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground/50" />
              <input
                id="dp-salary"
                class="w-full bg-background border border-border rounded-lg pl-9 pr-3 py-2 text-sm focus:ring-1 focus:ring-primary outline-none transition-all"
                placeholder="Range or fixed"
                value={app.salary ?? ''}
                onblur={(e) => {
                  const v = (e.target as HTMLInputElement).value || null;
                  if (v !== app.salary) patch({ salary: v });
                }}
              />
            </div>
          </div>
        </div>

        <div>
          <label for="dp-date" class="text-xs font-bold text-muted-foreground/80 block mb-1.5">Applied On</label>
          <div class="relative">
            <Calendar size={14} class="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground/50" />
            <input
              id="dp-date"
              type="date"
              class="w-full bg-background border border-border rounded-lg pl-9 pr-3 py-2 text-sm focus:ring-1 focus:ring-primary outline-none transition-all"
              value={app.applied_date ?? ''}
              onblur={(e) => {
                const v = (e.target as HTMLInputElement).value || null;
                if (v !== app.applied_date) patch({ applied_date: v });
              }}
            />
          </div>
        </div>

        <div>
          <label for="dp-url" class="text-xs font-bold text-muted-foreground/80 block mb-1.5">Job Posting URL</label>
          <div class="flex gap-1.5">
            <div class="relative flex-1">
              <Link size={14} class="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground/50" />
              <input
                id="dp-url"
                class="w-full bg-background border border-border rounded-lg pl-9 pr-3 py-2 text-sm focus:ring-1 focus:ring-primary outline-none transition-all"
                placeholder="https://..."
                value={app.job_url ?? ''}
                onblur={(e) => {
                  const v = (e.target as HTMLInputElement).value || null;
                  if (v !== app.job_url) patch({ job_url: v });
                }}
              />
            </div>
            {#if app.job_url}
              <a 
                href={app.job_url} 
                target="_blank" 
                rel="noopener noreferrer"
                class="bg-muted hover:bg-accent p-2 rounded-lg border border-border transition-colors flex items-center justify-center"
                title="Open job link"
              >
                <ExternalLink size={16} />
              </a>
            {/if}
          </div>
        </div>
      </div>
    </div>

    <div class="h-px bg-border/40 my-6"></div>

    <!-- Notes & Description -->
    <div class="space-y-4">
      <h3 class="text-[10px] font-black uppercase tracking-widest text-muted-foreground/80 mb-4 flex items-center gap-1.5">
        <FileText size={12} /> Notes & Description
      </h3>

      <div class="space-y-4">
        <div>
          <label for="dp-notes" class="text-xs font-bold text-muted-foreground/80 block mb-1.5">Personal Notes</label>
          <textarea
            id="dp-notes"
            class="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm min-h-32 resize-y focus:ring-1 focus:ring-primary outline-none transition-all"
            placeholder="Interview notes, contacts, deadlines…"
            onblur={(e) => {
              const v = (e.target as HTMLTextAreaElement).value || null;
              if (v !== app.notes) patch({ notes: v });
            }}
          >{app.notes ?? ''}</textarea>
        </div>

        {#if app.job_description}
          <div>
            <p class="text-xs font-bold text-muted-foreground/80 block mb-1.5">Job Description Summary</p>
            <div class="bg-muted/40 border border-border/50 rounded-lg px-3 py-3 text-xs leading-relaxed max-h-48 overflow-y-auto whitespace-pre-wrap text-muted-foreground">
              {app.job_description.slice(0, 800)}{app.job_description.length > 800 ? '…' : ''}
            </div>
          </div>
        {/if}
      </div>
    </div>

    <div class="h-px bg-border/40 my-6"></div>

    <!-- Linked Documents -->
    {#if app.linked_cover_letter_id || app.linked_cv_id}
      <div class="pb-4">
        <h3 class="text-[10px] font-black uppercase tracking-widest text-muted-foreground/80 mb-4 flex items-center gap-1.5">
          <Link size={12} /> Generated Documents
        </h3>
        <div class="grid grid-cols-1 gap-2">
          {#if app.linked_cover_letter_id}
            <a
              href="/history?cl={app.linked_cover_letter_id}"
              class="flex items-center justify-between p-2.5 bg-blue-500/5 hover:bg-blue-500/10 border border-blue-500/10 rounded-lg transition-all group"
            >
              <div class="flex items-center gap-2">
                <FileText size={14} class="text-blue-500" />
                <span class="text-xs font-bold text-blue-700 dark:text-blue-300">Cover Letter</span>
              </div>
              <ExternalLink size={12} class="text-blue-500 opacity-0 group-hover:opacity-100 transition-opacity" />
            </a>
          {/if}
          {#if app.linked_cv_id}
            <a
              href="/history?cv={app.linked_cv_id}"
              class="flex items-center justify-between p-2.5 bg-purple-500/5 hover:bg-purple-500/10 border border-purple-500/10 rounded-lg transition-all group"
            >
              <div class="flex items-center gap-2">
                <FileText size={14} class="text-purple-500" />
                <span class="text-xs font-bold text-purple-700 dark:text-purple-300">Tailored CV</span>
              </div>
              <ExternalLink size={12} class="text-purple-500 opacity-0 group-hover:opacity-100 transition-opacity" />
            </a>
          {/if}
        </div>
      </div>
    {/if}
  </div>

  <!-- Footer -->
  <div class="p-4 border-t border-border bg-muted/10">
    {#if confirmDelete}
      <div class="bg-destructive/10 border border-destructive/20 rounded-lg p-3 mb-3">
        <p class="text-xs font-bold text-destructive mb-3 flex items-center gap-1.5"><Trash2 size={12} /> Irreversible Action</p>
        <div class="flex gap-2">
          <button
            onclick={handleDelete}
            class="flex-1 bg-destructive text-destructive-foreground text-xs font-bold py-2 rounded-md hover:bg-destructive/90 transition-colors"
          >Delete</button>
          <button
            onclick={() => (confirmDelete = false)}
            class="flex-1 bg-background border border-border text-xs font-bold py-2 rounded-md hover:bg-accent transition-colors"
          >Cancel</button>
        </div>
      </div>
    {:else}
      <button
        onclick={() => (confirmDelete = true)}
        class="w-full text-destructive/70 hover:text-destructive border border-destructive/20 text-xs font-bold py-2.5 rounded-lg hover:bg-destructive/5 transition-all flex items-center justify-center gap-2"
      >
        <Trash2 size={14} /> Delete Application
      </button>
    {/if}
  </div>
</div>
