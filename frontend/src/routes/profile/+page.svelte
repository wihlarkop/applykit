<script lang="ts">
  import { beforeNavigate, invalidateAll } from '$app/navigation';
  import { page } from '$app/state';
  import { activeProfile } from '$lib/activeProfile.svelte';
  import { getProfile, saveProfile } from '$lib/api';
  import PersonalInfoTab from '$lib/components/profile/PersonalInfoTab.svelte';
  import ExperienceTab from '$lib/components/profile/ExperienceTab.svelte';
  import SkillsTab from '$lib/components/profile/SkillsTab.svelte';
  import EducationTab from '$lib/components/profile/EducationTab.svelte';
  import ProjectsTab from '$lib/components/profile/ProjectsTab.svelte';
  import CertificationsTab from '$lib/components/profile/CertificationsTab.svelte';
  import CvImporter from '$lib/components/CvImporter.svelte';
  import { Badge } from '$lib/components/ui/badge';
  import { Button } from '$lib/components/ui/button';
  import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';
  import { Input } from '$lib/components/ui/input';
  import { Label } from '$lib/components/ui/label';
  import { Skeleton } from '$lib/components/ui/skeleton';
  import { Textarea } from '$lib/components/ui/textarea';
  import { consumeStream } from '$lib/stream';
  import { toastState } from '$lib/toast.svelte';
  import type { ProfileData, Project, WorkExperience } from '$lib/types';
  import { errorMessage } from '$lib/utils';
  import { Award, Building2, Check, ChevronDown, FileUp, FolderGit2, GraduationCap, Loader2, Plus, RefreshCw, Save, Sparkles as SparklesIcon, Trash2, User, X } from '@lucide/svelte';
  import { fly, fade, scale } from 'svelte/transition';

  let profile: ProfileData = $state({
    name: '',
    email: '',
    phone: '',
    location: '',
    linkedin: '',
    github: '',
    portfolio: '',
    summary: '',
    work_experience: [],
    education: [],
    skills: [],
    projects: [],
    certifications: [],
  });
  let loading = $state(true);
  let saving = $state(false);
  let showImporter = $state(false);

  let activeTab = $state('personal-info');
  let loadedProfileJson = $state('');
  const isDirty = $derived(loadedProfileJson !== '' && JSON.stringify(profile) !== loadedProfileJson);

  const isProfileEmpty = $derived(!profile.name && !profile.email && profile.work_experience.length === 0);

  let loadSeq = 0;

  $effect(() => {
    const ap = activeProfile.current;
    if (!ap) return;
    const seq = ++loadSeq;
    loading = true;
    getProfile(ap.id)
      .then((data) => {
        if (seq !== loadSeq) return;
        profile = { ...data };
        loadedProfileJson = JSON.stringify({ ...data });
      })
      .catch((e: unknown) => {
        if (seq !== loadSeq) return;
        toastState.error('Failed to load profile. Please refresh the page.');
      })
      .finally(() => {
        if (seq !== loadSeq) return;
        loading = false;
      });
  });

  beforeNavigate(({ cancel }) => {
    if (isDirty && !confirm('You have unsaved changes. Leave this page?')) {
      cancel();
    }
  });

  $effect(() => {
    const handler = (e: BeforeUnloadEvent) => { if (isDirty) e.preventDefault(); };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  });

  async function handleSave() {
    const ap = activeProfile.current;
    if (!ap) return;
    saving = true;
    try {
      await saveProfile(ap.id, profile);
      toastState.success('Profile saved successfully!');
      loadedProfileJson = JSON.stringify(profile);
      await invalidateAll();
    } catch (e: unknown) {
      toastState.error(`Save failed: ${errorMessage(e)}`);
    } finally {
      saving = false;
    }
  }

  async function onImportSuccess() {
    showImporter = false;
    const ap = activeProfile.current;
    if (ap) {
      try {
        const data = await getProfile(ap.id);
        profile = { ...data };
        loadedProfileJson = JSON.stringify({ ...data });
      } catch (e: unknown) {
        toastState.error(`Failed to reload profile: ${errorMessage(e)}`);
      }
    }
    await invalidateAll();
  }


  const sections = [
    { id: 'personal-info', label: 'Personal Info', icon: User },
    { id: 'skills', label: 'Core Skills', icon: Award },
    { id: 'experience', label: 'Experience', icon: Building2 },
    { id: 'education', label: 'Education', icon: GraduationCap },
    { id: 'projects', label: 'Projects', icon: FolderGit2 },
    { id: 'certifications', label: 'Certifications & Training', icon: Award },
  ];

  const profileHealth = $derived.by(() => {
    let score = 0;
    if (profile.name) score += 15;
    if (profile.email) score += 10;
    if (profile.summary) score += 10;
    if (profile.work_experience.length > 0) score += 30;
    if (profile.education.length > 0) score += 20;
    if (profile.skills.length > 0) score += 15;
    return score;
  });

  const healthMessage = $derived.by(() => {
    if (profileHealth === 100) return "Profile is 100% complete!";
    if (!profile.name || !profile.email) return "Add your name and email to get started.";
    if (profile.work_experience.length === 0) return "Add work experience — it's worth 30%.";
    if (profile.education.length === 0) return "Add your education background.";
    if (profile.skills.length === 0) return "Add skills to complete your profile.";
    if (!profile.summary) return "Add a professional summary to reach 100%.";
    return "Complete more sections to reach 100%.";
  });
</script>

<svelte:window onkeydown={e => {
  if (e.ctrlKey && e.key === 's') {
    e.preventDefault();
    handleSave();
  }
}} />

<div class="space-y-8 max-w-6xl pb-20 relative px-4 mx-auto">  <!-- Sticky Header -->
  <div class="sticky top-0 z-50 bg-background/60 backdrop-blur-xl border-b border-border/50 -mx-4 px-4 py-4 mb-8 transition-all duration-300">
    <div class="flex items-start sm:items-center justify-between flex-col sm:flex-row gap-4 max-w-6xl mx-auto">
      <div>
        {#if !page.data.isOnboarded}
          <a href="/onboarding" class="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-widest text-muted-foreground hover:text-primary mb-1.5 transition-colors">
            ← Back to setup
          </a>
        {/if}
        <h1 class="text-2xl font-extrabold tracking-tight flex items-center gap-3">
          <div class="p-2 bg-primary/10 rounded-lg">
            <User class="w-6 h-6 text-primary" />
          </div>
          Profile Setup
        </h1>
        <p class="text-[11px] text-muted-foreground mt-1.5 font-bold uppercase tracking-widest flex items-center gap-2">
          {#if activeProfile.current}
            <span class="w-1.5 h-1.5 rounded-full animate-pulse" style="background-color:{activeProfile.current.color}"></span>
            Editing: <span class="text-foreground/80">{activeProfile.current.icon} {activeProfile.current.label}</span>
          {:else}
            Secure your professional baseline.
          {/if}
        </p>
      </div>
      <div class="flex items-center gap-2.5 self-end sm:self-auto">
        <Button variant="outline" size="sm" onclick={() => showImporter = !showImporter} class="shadow-sm h-10 px-4 font-semibold border-primary/20 hover:border-primary/50 transition-colors">
          <SparklesIcon class="w-4 h-4 mr-2 text-primary" />
          {showImporter ? 'Cancel' : 'AI Sync'}
        </Button>
 
        <Button 
          onclick={handleSave} 
          disabled={saving || loading} 
          size="sm" 
          class="shadow-lg h-10 px-5 font-bold transition-all relative overflow-hidden group {isDirty ? 'bg-primary' : ''}"
        >
          {#if isDirty}
            <div class="absolute inset-0 bg-white/10 translate-y-full group-hover:translate-y-0 transition-transform duration-300"></div>
          {/if}
          <Save class="w-4 h-4 mr-2 relative z-10" />
          <span class="relative z-10">{saving ? 'Saving…' : isDirty ? 'Save Changes' : 'All Saved'}</span>
          {#if isDirty}
            <span class="absolute right-2 top-2 w-1.5 h-1.5 bg-white rounded-full animate-ping"></span>
          {/if}
        </Button>
      </div>
    </div>
  </div>

  {#if showImporter}
    <div class="animate-in fade-in slide-in-from-top-4 duration-500">
      <Card class="border-primary/30 shadow-lg bg-primary/5">
        <CardHeader>
          <CardTitle class="text-lg flex items-center gap-2">
            <RefreshCw class="w-5 h-5 text-primary" />
            AI Profile Sync
          </CardTitle>
          <p class="text-sm text-muted-foreground">Sync your profile with an existing CV using AI extraction.</p>
        </CardHeader>
        <CardContent>
          <CvImporter onSaveSuccess={onImportSuccess} />
        </CardContent>
      </Card>
    </div>
  {/if}

  {#if isProfileEmpty && !loading && !showImporter}
    <div class="animate-in fade-in slide-in-from-top-4 duration-500">
      <Card class="bg-primary/5 border-primary/20 shadow-sm overflow-hidden relative">
        <div class="absolute right-0 top-0 w-32 h-32 bg-primary/5 rounded-full -mr-16 -mt-16 pointer-events-none"></div>
        <CardContent class="p-6 flex flex-col sm:flex-row items-center gap-6 relative z-10">
          <div class="w-12 h-12 bg-primary/10 text-primary rounded-xl flex items-center justify-center shrink-0">
            <FileUp class="w-6 h-6" />
          </div>
          <div class="flex-1 text-center sm:text-left">
            <h3 class="font-bold text-primary">New here? Save time with AI!</h3>
            <p class="text-sm text-muted-foreground mt-1">
              Manually fill your info below, or use <span class="font-bold text-primary">AI Sync</span> to extract everything instantly.
            </p>
          </div>
          <Button onclick={() => showImporter = true} variant="default" class="rounded-full shadow-md shrink-0">
            <SparklesIcon class="w-4 h-4 mr-2" />
            Start AI Sync
          </Button>
        </CardContent>
      </Card>
    </div>
  {/if}

      <div class="lg:flex lg:gap-10 items-start">
    <!-- Mobile Tabs -->
    <div class="lg:hidden flex overflow-x-auto pb-4 mb-4 gap-2 no-scrollbar -mx-4 px-4 sticky top-18.25 z-40 bg-background/80 backdrop-blur-md border-b border-border/50">
      {#each sections as section}
        <button
          onclick={() => activeTab = section.id}
          class="whitespace-nowrap flex items-center gap-2 px-4 py-2.5 rounded-full border transition-all
                 {activeTab === section.id
                   ? 'bg-primary text-primary-foreground border-primary shadow-sm font-semibold'
                   : 'bg-muted/50 text-muted-foreground border-transparent hover:bg-muted hover:text-foreground'}"
        >
          <section.icon class="w-4 h-4" />
          <span class="text-sm">{section.label}</span>
        </button>
      {/each}
    </div>

    <!-- Desktop Sidebar -->
    <aside class="hidden lg:block w-72 sticky top-28 h-fit space-y-2">
      <div class="p-2 space-y-1">
        {#each sections as section}
          <button
            onclick={() => activeTab = section.id}
            class="w-full flex items-center gap-3 px-4 py-3.5 rounded-xl transition-all duration-300 group relative
                   {activeTab === section.id
                     ? 'bg-primary/5 text-primary shadow-sm border-primary/20'
                     : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground border-transparent'}"
          >
            {#if activeTab === section.id}
              <div class="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-primary rounded-r-full shadow-[0_0_8px_rgba(59,130,246,0.5)]" in:fade></div>
            {/if}
            <section.icon class="w-5 h-5 {activeTab === section.id ? 'text-primary' : 'text-muted-foreground group-hover:text-primary transition-colors'}" />
            <span class="font-bold text-sm tracking-tight">{section.label}</span>
          </button>
        {/each}
      </div>

      <div class="mt-8 p-6 rounded-2xl bg-primary/5 border border-primary/10">
        <div class="flex items-center justify-between mb-2">
          <h3 class="text-xs font-bold uppercase tracking-wider text-primary">Profile Health</h3>
          <span class="text-xs font-bold text-primary">{profileHealth}%</span>
        </div>
        <div class="h-2 w-full bg-muted rounded-full overflow-hidden mb-2">
          <div class="h-full bg-primary transition-all duration-500 ease-out" style="width: {profileHealth}%"></div>
        </div>
        <p class="text-[11px] text-muted-foreground leading-relaxed">{healthMessage}</p>
      </div>
    </aside>

    <div class="flex-1">
      <Card class="shadow-sm border-border/50">
        <CardContent class="p-0">
          {#if loading}
            <div class="p-8 space-y-12">
              {#each Array(3) as _}
                <div class="grid lg:grid-cols-3 gap-8">
                  <div class="space-y-2"><Skeleton class="h-6 w-1/2" /><Skeleton class="h-4 w-full" /></div>
                  <div class="lg:col-span-2 grid gap-4 sm:grid-cols-2">
                    <Skeleton class="h-10 w-full" /><Skeleton class="h-10 w-full" />
                  </div>
                </div>
              {/each}
            </div>
          {:else}
            <div class="p-0">
              {#key activeTab}
                <div in:fly={{ y: 20, duration: 400, delay: 100 }} out:fade={{ duration: 100 }}>
                  {#if activeTab === 'personal-info'}
                    <section id="personal-info" class="p-8">
                      <PersonalInfoTab bind:profile={profile} />
                    </section>
                  {/if}

                  {#if activeTab === 'skills'}
                    <section id="skills" class="p-8">
                      <SkillsTab bind:profile={profile} />
                    </section>
                  {/if}

                  {#if activeTab === 'experience'}
                    <section id="experience" class="p-8">
                      <ExperienceTab bind:profile={profile} />
                    </section>
                  {/if}

                  {#if activeTab === 'education'}
                    <section id="education" class="p-8">
                      <EducationTab bind:profile={profile} />
                    </section>
                  {/if}

                  {#if activeTab === 'projects'}
                    <section id="projects" class="p-8">
                      <ProjectsTab bind:profile={profile} />
                    </section>
                  {/if}

                  {#if activeTab === 'certifications'}
                    <section id="certifications" class="p-8">
                      <CertificationsTab bind:profile={profile} />
                    </section>
                  {/if}
                </div>
              {/key}
            </div>
          {/if}
        </CardContent>
      </Card>
    </div>
  </div>
</div>
