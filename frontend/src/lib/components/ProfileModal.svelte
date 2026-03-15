<script lang="ts">
  import { createProfile, saveProfile, listProfiles } from '$lib/api';
  import type { ProfileData, CreateProfileRequest } from '$lib/types';
  import { profiles } from '$lib/profiles.svelte';
  import { activeProfile } from '$lib/activeProfile.svelte';
  import { toastState } from '$lib/toast.svelte';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { Label } from '$lib/components/ui/label';

  function portal(node: HTMLElement) {
    document.body.appendChild(node);
    return { destroy() { node.remove(); } };
  }

  type Mode = 'create' | 'edit';

  type Props = {
    mode: Mode;
    profile?: ProfileData | null;
    onclose: () => void;
    onsaved?: () => void;
  };

  let { mode, profile = null, onclose, onsaved }: Props = $props();

  const COLORS = ['#6366f1', '#f59e0b', '#10b981', '#ef4444', '#3b82f6', '#8b5cf6', '#ec4899', '#14b8a6'];
  const ICONS  = ['💼', '🏢', '🎨', '💻', '🚀', '⚡', '🎯', '🌟'];

  let label = $state(profile?.label ?? '');
  let color = $state(profile?.color ?? COLORS[0]);
  let icon  = $state(profile?.icon  ?? ICONS[0]);
  let cloneEnabled = $state(false);
  let cloneFromId  = $state<number | null>(null);
  let saving = $state(false);
  let error  = $state('');

  const allProfiles = $derived(profiles.all);

  async function handleSubmit() {
    if (!label.trim()) { error = 'Label is required'; return; }
    saving = true;
    error = '';
    try {
      if (mode === 'create') {
        const req: CreateProfileRequest = {
          label: label.trim(),
          color,
          icon,
          clone_from_id: cloneEnabled ? cloneFromId : null,
        };
        const created = await createProfile(req);
        const fresh = await listProfiles();
        profiles.set(fresh.items);
        if (created.id) {
          activeProfile.set({ id: created.id, label: created.label ?? label, color: created.color ?? color, icon: created.icon ?? icon, name: created.name ?? '' });
        }
        if (!cloneEnabled) {
          toastState.info('Profile created — fill in your details before generating.');
        }
      } else if (mode === 'edit' && profile?.id) {
        const updated = await saveProfile(profile.id, { ...profile, label: label.trim(), color, icon });
        const fresh = await listProfiles();
        profiles.set(fresh.items);
        const ap = activeProfile.current;
        if (ap?.id === profile.id) {
          activeProfile.set({ id: profile.id, label: updated.label ?? label, color: updated.color ?? color, icon: updated.icon ?? icon, name: updated.name ?? '' });
        }
      }
      onsaved?.();
      onclose();
    } catch (e: any) {
      error = e.message ?? 'Something went wrong';
    } finally {
      saving = false;
    }
  }
</script>

<!-- Backdrop -->
<div
  use:portal
  class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
  onclick={onclose}
>
  <!-- Modal -->
  <div
    class="bg-card border rounded-xl shadow-xl p-6 w-full max-w-sm mx-4 space-y-5"
    onclick={(e) => e.stopPropagation()}
  >
    <h2 class="text-lg font-semibold">{mode === 'create' ? 'New Profile' : 'Edit Identity'}</h2>

    <!-- Label -->
    <div class="space-y-2">
      <Label for="profile-label">Label</Label>
      <Input id="profile-label" bind:value={label} placeholder="e.g. Software Engineer" />
    </div>

    <!-- Color -->
    <div class="space-y-2">
      <Label>Color</Label>
      <div class="flex gap-2 flex-wrap">
        {#each COLORS as c}
          <button
            type="button"
            onclick={() => color = c}
            class="w-7 h-7 rounded-full transition-transform hover:scale-110"
            style="background:{c}; outline: {color === c ? '3px solid currentColor' : 'none'}; outline-offset: 2px;"
            title={c}
          ></button>
        {/each}
      </div>
    </div>

    <!-- Icon -->
    <div class="space-y-2">
      <Label>Icon</Label>
      <div class="flex gap-2 flex-wrap">
        {#each ICONS as ic}
          <button
            type="button"
            onclick={() => icon = ic}
            class="w-9 h-9 rounded-lg border text-lg flex items-center justify-center transition-colors
              {icon === ic ? 'border-primary bg-primary/10' : 'border-border hover:bg-accent'}"
          >{ic}</button>
        {/each}
      </div>
    </div>

    <!-- Preview -->
    <div class="flex items-center gap-2 text-sm">
      <span>Preview:</span>
      <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border font-medium text-sm" style="border-color:{color}">
        <span class="w-2 h-2 rounded-full inline-block" style="background:{color}"></span>
        {icon} {label || 'Profile'}
      </span>
    </div>

    <!-- Clone (create mode only) -->
    {#if mode === 'create' && allProfiles.length > 0}
      <div class="space-y-2">
        <label class="flex items-center gap-2 text-sm cursor-pointer">
          <input type="checkbox" bind:checked={cloneEnabled} class="rounded" />
          Copy work experience, skills &amp; education from another profile
        </label>
        {#if cloneEnabled}
          <select
            bind:value={cloneFromId}
            class="w-full border rounded-md px-3 py-2 text-sm bg-background"
          >
            <option value={null}>— select profile —</option>
            {#each allProfiles as p}
              <option value={p.id}>{p.icon} {p.label} ({p.name})</option>
            {/each}
          </select>
        {/if}
      </div>
    {/if}

    {#if error}
      <p class="text-sm text-destructive">{error}</p>
    {/if}

    <div class="flex gap-2 justify-end pt-1">
      <Button variant="outline" onclick={onclose} disabled={saving}>Cancel</Button>
      <Button onclick={handleSubmit} disabled={saving}>
        {saving ? 'Saving…' : mode === 'create' ? 'Create Profile' : 'Save'}
      </Button>
    </div>
  </div>
</div>
