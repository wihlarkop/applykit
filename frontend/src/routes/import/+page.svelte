<script lang="ts">
  import { activeProfile } from '$lib/activeProfile.svelte';
  import { importCvFile, importCvText, saveProfile } from '$lib/api';
  import { Button } from '$lib/components/ui/button';
  import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '$lib/components/ui/card';
  import { Label } from '$lib/components/ui/label';
  import { Textarea } from '$lib/components/ui/textarea';
  import { errorMessage } from '$lib/utils';
  import type { ProfileData } from '$lib/types';
  import { CircleCheck, FileText, Save, Sparkles, Type, Upload } from '@lucide/svelte';

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
  }

  async function handleImport() {
    errorMsg = '';
    preview = null;
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
      successMsg = 'Profile saved from import!';
    } catch (e: unknown) {
      errorMsg = errorMessage(e);
    } finally {
      saving = false;
    }
  }
</script>

<div class="space-y-8 max-w-3xl pb-10 relative">
  <!-- Sticky Header -->
  <div class="sticky top-0 z-50 bg-background/80 backdrop-blur-md border-b border-border -mx-4 px-4 py-4 mb-8">
    <div class="flex items-start sm:items-center justify-between flex-col sm:flex-row gap-4 max-w-3xl mx-auto">
      <div>
        <h1 class="text-2xl font-bold flex items-center gap-2">
          <FileText class="w-6 h-6 text-primary" />
          Import CV
        </h1>
        <p class="text-xs text-muted-foreground mt-0.5">Quickly populate your profile by extracting data from an existing CV using AI.</p>
      </div>
    </div>
  </div>

  <Card class="shadow-sm border-primary/20">
    <CardHeader class="pb-4">
      <!-- Tab toggle -->
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
                    hover:file:bg-primary/90 cursor-pointer border rounded-md p-1"
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
        <div class="p-3 rounded-md bg-destructive/10 text-destructive text-sm font-medium border border-destructive/20">
          {errorMsg}
        </div>
      {/if}
    </CardContent>
  </Card>

  <!-- Preview -->
  {#if preview}
    <div class="animate-in fade-in slide-in-from-bottom-4 duration-500">
      <Card class="shadow-sm border-green-500/20 bg-green-500/5">
        <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-4">
          <div>
            <CardTitle class="flex items-center gap-2 text-lg text-green-700 dark:text-green-400">
              <CircleCheck class="w-5 h-5" />
              Extraction Successful
            </CardTitle>
            <CardDescription class="mt-1">Review the extracted data below before saving it to your profile.</CardDescription>
          </div>
          <Button onclick={handleSave} disabled={saving} size="sm" class="bg-green-600 hover:bg-green-700 text-white shadow-sm">
            <Save class="w-4 h-4 mr-2" />
            {saving ? 'Saving…' : 'Save to Profile'}
          </Button>
        </CardHeader>

        <CardContent>
          {#if successMsg}
            <div class="mb-6 p-3 rounded-md bg-green-500/20 text-green-700 dark:text-green-400 text-sm font-medium">
              {successMsg}
            </div>
          {/if}

          <div class="space-y-6">
            <div class="grid gap-x-4 gap-y-2 text-sm sm:grid-cols-2 bg-background p-4 rounded-lg border">
              <div><span class="font-semibold text-muted-foreground w-20 inline-block">Name:</span> <span>{preview.name || '—'}</span></div>
              <div><span class="font-semibold text-muted-foreground w-20 inline-block">Email:</span> <span>{preview.email || '—'}</span></div>
              <div><span class="font-semibold text-muted-foreground w-20 inline-block">Phone:</span> <span>{preview.phone || '—'}</span></div>
              <div><span class="font-semibold text-muted-foreground w-20 inline-block">Location:</span> <span>{preview.location || '—'}</span></div>
            </div>

            {#if preview.summary}
              <div class="text-sm bg-background p-4 rounded-lg border">
                <span class="font-semibold text-muted-foreground">Professional Summary</span>
                <p class="mt-2 text-foreground leading-relaxed">{preview.summary}</p>
              </div>
            {/if}

            <div class="grid gap-4 sm:grid-cols-3">
              <div class="text-sm bg-background p-4 rounded-lg border text-center">
                <div class="text-2xl font-bold text-primary mb-1">{preview.work_experience.length}</div>
                <div class="text-muted-foreground font-medium">Work Entries</div>
              </div>
              <div class="text-sm bg-background p-4 rounded-lg border text-center">
                <div class="text-2xl font-bold text-purple-500 mb-1">{preview.education.length}</div>
                <div class="text-muted-foreground font-medium">Education Entries</div>
              </div>
              <div class="text-sm bg-background p-4 rounded-lg border text-center">
                <div class="text-2xl font-bold text-amber-500 mb-1">{preview.skills.length}</div>
                <div class="text-muted-foreground font-medium">Skills Found</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  {/if}
</div>
