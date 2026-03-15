<script lang="ts">
  import { deleteProfile, getProfile, listProfiles } from '$lib/api';
  import { profiles } from '$lib/profiles.svelte';
  import { activeProfile } from '$lib/activeProfile.svelte';
  import ProfileModal from '$lib/components/ProfileModal.svelte';
  import type { ProfileListItem } from '$lib/types';
  import { Button } from '$lib/components/ui/button';
  import { goto } from '$app/navigation';

  let modalMode = $state<'create' | 'edit' | null>(null);
  let editingProfile = $state<ProfileListItem | null>(null);
  let deletingId = $state<number | null>(null);
  let error = $state('');

  const allProfiles = $derived(profiles.all);

  function openCreate() { modalMode = 'create'; editingProfile = null; }
  function openEdit(p: ProfileListItem) { editingProfile = p; modalMode = 'edit'; }
  function closeModal() { modalMode = null; editingProfile = null; }

  async function handleDelete(p: ProfileListItem) {
    if (!confirm(`Delete profile "${p.label}"? This cannot be undone.`)) return;
    deletingId = p.id;
    error = '';
    try {
      await deleteProfile(p.id);
      profiles.remove(p.id);
      const ap = activeProfile.current;
      if (ap?.id === p.id) {
        const remaining = profiles.all;
        if (remaining.length > 0) {
          activeProfile.set({ id: remaining[0].id, label: remaining[0].label, color: remaining[0].color, icon: remaining[0].icon });
        } else {
          activeProfile.clear();
          goto('/onboarding');
          return;
        }
      }
    } catch (e: any) {
      error = e.message ?? 'Could not delete profile';
    } finally {
      deletingId = null;
    }
  }

  async function handleSaved() {
    const res = await listProfiles();
    profiles.set(res.items);
  }
</script>

<div class="space-y-6">
  <div class="flex items-center justify-between">
    <h1 class="text-2xl font-bold">Profiles</h1>
    <Button onclick={openCreate}>＋ New Profile</Button>
  </div>

  {#if error}
    <p class="text-sm text-destructive">{error}</p>
  {/if}

  {#if allProfiles.length === 0}
    <p class="text-muted-foreground">No profiles yet.</p>
  {:else}
    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {#each allProfiles as p}
        <div class="border rounded-xl p-5 bg-card space-y-3">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-lg flex items-center justify-center text-2xl shrink-0" style="background:{p.color}20; border: 1.5px solid {p.color}">
              {p.icon}
            </div>
            <div class="flex-1 min-w-0">
              <div class="font-semibold text-sm">{p.label}</div>
              <div class="text-xs text-muted-foreground truncate">{p.name || 'No name set'}</div>
              <!-- Completeness bar -->
              <div class="mt-1.5 flex items-center gap-2">
                <div class="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                  <div
                    class="h-full rounded-full transition-all"
                    style="width:{p.completeness}%; background:{p.completeness >= 70 ? '#10b981' : p.completeness >= 40 ? p.color : '#f59e0b'}"
                  ></div>
                </div>
                <span class="text-xs text-muted-foreground shrink-0">{p.completeness}%</span>
              </div>
            </div>
            {#if activeProfile.current?.id === p.id}
              <span class="shrink-0 text-xs px-2 py-0.5 rounded-full border font-medium" style="border-color:{p.color};color:{p.color}">active</span>
            {/if}
          </div>
          <div class="flex gap-2">
            <Button variant="outline" size="sm" class="flex-1" onclick={() => openEdit(p)}>Edit</Button>
            <Button
              variant="destructive"
              size="sm"
              disabled={deletingId === p.id}
              onclick={() => handleDelete(p)}
            >
              {deletingId === p.id ? '…' : 'Delete'}
            </Button>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

{#if modalMode === 'create'}
  <ProfileModal mode="create" onclose={closeModal} onsaved={handleSaved} />
{:else if modalMode === 'edit' && editingProfile}
  {#await getProfile(editingProfile.id) then fullProfile}
    <ProfileModal mode="edit" profile={fullProfile} onclose={closeModal} onsaved={handleSaved} />
  {:catch}
    {closeModal()}
  {/await}
{/if}
