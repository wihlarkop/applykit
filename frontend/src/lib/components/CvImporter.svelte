<script lang="ts">
  import { activeProfile } from '$lib/activeProfile.svelte';
  import { importCvFile, importCvText, saveProfile } from '$lib/api';
  import { Button } from '$lib/components/ui/button';
  import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '$lib/components/ui/card';
  import { Label } from '$lib/components/ui/label';
  import { Textarea } from '$lib/components/ui/textarea';
  import { errorMessage } from '$lib/utils';
  import type { ProfileData } from '$lib/types';
  import { CheckCircle2, Save, Sparkles, Type, Upload } from '@lucide/svelte';

  let { onSaveSuccess } = $props<{ onSaveSuccess?: () => void }>();

  type Tab = 'file' | 'text';
  let tab: Tab = $state('file');

  let file: File | null = $state(null);
  let pastedText = $state('');
  let preview: ProfileData | null = $state(null);
  let loading = $state(false);
  let saving = $state(false);
  let errorMsg = $state('');
  let successMsg = $state('');

  function handleFileInput(e: Event) {
    const input = e.target as HTMLInputElement;
    file = input.files?.[0] ?? null;
    errorMsg = '';
    preview = null;
    successMsg = '';
  }

  async function handleImport() {
    errorMsg = '';
    preview = null;
    successMsg = '';
    loading = true;
    try {
      if (tab === 'file') {
        if (!file) { errorMsg = 'Please select a file.'; return; }
        preview = await importCvFile(file);
      } else {
        if (!pastedText.trim()) { errorMsg = 'Please paste some text.'; return; }
        preview = await importCvText(pastedText);
      }
    } catch (e: unknown) {
      errorMsg = errorMessage(e);
    } finally {
      loading = false;
    }
  }

  async function handleSave() {
    if (!preview) return;
    const ap = activeProfile.current;
    if (!ap) { errorMsg = 'No active profile. Please refresh the page.'; return; }
    saving = true;
    errorMsg = '';
    try {
      await saveProfile(ap.id, preview);
      successMsg = 'Profile successfully updated!';
      if (onSaveSuccess) onSaveSuccess();
    } catch (e: unknown) {
      errorMsg = errorMessage(e);
    } finally {
      saving = false;
    }
  }
</script>

<div class="space-y-6">
  <Card class="shadow-sm border-primary/20 bg-background/50 backdrop-blur-sm">
    <CardHeader class="pb-4">
      <div class="flex gap-2">
        <button
          class="flex items-center gap-2 px-4 py-2 text-sm font-medium transition-all rounded-md
            {tab === 'file' ? 'bg-primary text-primary-foreground shadow-sm' : 'bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground'}"
          onclick={() => { tab = 'file'; preview = null; errorMsg = ''; successMsg = ''; }}
        >
          <Upload class="w-4 h-4" />
          Upload File
        </button>
        <button
          class="flex items-center gap-2 px-4 py-2 text-sm font-medium transition-all rounded-md
            {tab === 'text' ? 'bg-primary text-primary-foreground shadow-sm' : 'bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground'}"
          onclick={() => { tab = 'text'; preview = null; errorMsg = ''; successMsg = ''; }}
        >
          <Type class="w-4 h-4" />
          Paste Text
        </button>
      </div>
    </CardHeader>

    <CardContent class="space-y-6">
      {#if tab === 'file'}
        <div class="space-y-3">
          <Label for="cv-file">CV File (PDF or DOCX, max 5 MB)</Label>
          <div class="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
            <input
              id="cv-file"
              type="file"
              accept=".pdf,.docx"
              oninput={handleFileInput}
              class="block w-full text-sm text-muted-foreground file:mr-4 file:rounded-md file:border-0
                    file:bg-primary file:text-primary-foreground file:px-4 file:py-2.5 file:text-sm file:font-medium
                    hover:file:bg-primary/90 cursor-pointer border rounded-md p-1 bg-background"
            />
            <Button onclick={handleImport} disabled={loading || !file} size="lg" class="w-full sm:w-auto shadow-sm min-w-35">
              {#if loading}
                <Sparkles class="w-4 h-4 mr-2 animate-pulse" /> Extracting…
              {:else}
                <Sparkles class="w-4 h-4 mr-2" /> Extract Profile
              {/if}
            </Button>
          </div>
        </div>
      {:else}
        <div class="space-y-3">
          <Label for="cv-text">Paste CV text</Label>
          <Textarea
            id="cv-text"
            bind:value={pastedText}
            placeholder="Paste your plain text CV content here…"
            rows={10}
            class="bg-background/50 resize-y font-mono text-sm leading-relaxed"
          />
          <div class="flex justify-end pt-2">
            <Button onclick={handleImport} disabled={loading || !pastedText.trim()} size="lg" class="shadow-sm min-w-35">
              {#if loading}
                <Sparkles class="w-4 h-4 mr-2 animate-pulse" /> Extracting…
              {:else}
                <Sparkles class="w-4 h-4 mr-2" /> Extract Profile
              {/if}
            </Button>
          </div>
        </div>
      {/if}

      {#if errorMsg}
        <div class="p-3 rounded-md bg-destructive/10 text-destructive text-sm font-medium border border-destructive/20 animate-in fade-in zoom-in-95 duration-200">
          {errorMsg}
        </div>
      {/if}
    </CardContent>
  </Card>

  {#if preview}
    <div class="animate-in fade-in slide-in-from-bottom-4 duration-500">
      <Card class="shadow-md border-green-500/20 bg-green-500/5 overflow-hidden">
        <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-4 bg-green-500/10">
          <div>
            <CardTitle class="flex items-center gap-2 text-lg text-green-700 dark:text-green-400">
              <CheckCircle2 class="w-5 h-5" />
              Extraction Successful
            </CardTitle>
            <CardDescription class="mt-1 text-green-600/80">Review your profile components extracted by AI.</CardDescription>
          </div>
          <Button onclick={handleSave} disabled={saving} size="sm" class="bg-green-600 hover:bg-green-700 text-white shadow-sm px-6">
            <Save class="w-4 h-4 mr-2" />
            {saving ? 'Saving…' : 'Save & Continue'}
          </Button>
        </CardHeader>

        <CardContent class="pt-6">
          {#if successMsg}
            <div class="mb-6 p-3 rounded-md bg-green-500/20 text-green-700 dark:text-green-400 text-sm font-medium animate-in fade-in duration-300">
              {successMsg}
            </div>
          {/if}

          <div class="space-y-6">
            <div class="grid gap-x-6 gap-y-4 text-sm sm:grid-cols-2 bg-background/50 p-4 rounded-xl border border-green-500/10">
              <div class="flex flex-col gap-1">
                <span class="text-[10px] uppercase tracking-wider font-bold text-muted-foreground/70">Full Name</span>
                <span class="font-medium text-foreground">{preview.name || '—'}</span>
              </div>
              <div class="flex flex-col gap-1">
                <span class="text-[10px] uppercase tracking-wider font-bold text-muted-foreground/70">Email Address</span>
                <span class="font-medium text-foreground">{preview.email || '—'}</span>
              </div>
              <div class="flex flex-col gap-1">
                <span class="text-[10px] uppercase tracking-wider font-bold text-muted-foreground/70">Phone Number</span>
                <span class="font-medium text-foreground">{preview.phone || '—'}</span>
              </div>
              <div class="flex flex-col gap-1">
                <span class="text-[10px] uppercase tracking-wider font-bold text-muted-foreground/70">Location</span>
                <span class="font-medium text-foreground">{preview.location || '—'}</span>
              </div>
            </div>

            <div class="grid gap-4 sm:grid-cols-3">
              <div class="bg-background/50 p-4 rounded-xl border border-green-500/10 text-center flex flex-col items-center justify-center">
                <div class="text-3xl font-black text-primary/80">{preview.work_experience.length}</div>
                <div class="text-[10px] uppercase tracking-wider font-bold text-muted-foreground/70">Experience Items</div>
              </div>
              <div class="bg-background/50 p-4 rounded-xl border border-green-500/10 text-center flex flex-col items-center justify-center">
                <div class="text-3xl font-black text-purple-500/80">{preview.education.length}</div>
                <div class="text-[10px] uppercase tracking-wider font-bold text-muted-foreground/70">Education Items</div>
              </div>
              <div class="bg-background/50 p-4 rounded-xl border border-green-500/10 text-center flex flex-col items-center justify-center">
                <div class="text-3xl font-black text-amber-500/80">{preview.skills.length}</div>
                <div class="text-[10px] uppercase tracking-wider font-bold text-muted-foreground/70">Skills Detected</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  {/if}
</div>
