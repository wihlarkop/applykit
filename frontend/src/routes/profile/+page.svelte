<script lang="ts">
  import { getProfile, saveProfile } from '$lib/api';
  import { Button } from '$lib/components/ui/button';
  import { Input } from '$lib/components/ui/input';
  import { Label } from '$lib/components/ui/label';
  import { Separator } from '$lib/components/ui/separator';
  import { Textarea } from '$lib/components/ui/textarea';
  import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';
  import { User, Save, Plus, Trash2, Building2, GraduationCap, FolderGit2, Award, FileUp, Sparkles as SparklesIcon, RefreshCw } from '@lucide/svelte';
  import type { ProfileData, Project, WorkExperience } from '$lib/types';
  import CvImporter from '$lib/components/CvImporter.svelte';
  import { activeProfile } from '$lib/activeProfile.svelte';
  import { invalidateAll, beforeNavigate } from '$app/navigation';
  import { toastState } from '$lib/toast.svelte';
  import { Skeleton } from '$lib/components/ui/skeleton';
  import { Badge } from '$lib/components/ui/badge';
  import { X } from '@lucide/svelte';

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

  let skillsText = $state('');
  let loading = $state(true);
  let saving = $state(false);
  let showImporter = $state(false);
  let activeTab = $state('personal-info');
  let loadedProfileJson = $state('');
  const isDirty = $derived(loadedProfileJson !== '' && JSON.stringify(profile) !== loadedProfileJson);

  const isProfileEmpty = $derived(!profile.name && !profile.email && profile.work_experience.length === 0);

  function commitSkill() {
    const val = skillsText.trim().replace(/,$/, '');
    if (val && !profile.skills.includes(val)) {
      profile.skills = [...profile.skills, val];
      skillsText = '';
    }
  }

  function addSkill(e: KeyboardEvent) {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      commitSkill();
    }
  }

  function removeSkill(skill: string) {
    profile.skills = profile.skills.filter(s => s !== skill);
  }

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
        skillsText = '';
        loadedProfileJson = JSON.stringify({ ...data });
      })
      .catch((e: any) => {
        if (seq !== loadSeq) return;
        toastState.error(`Failed to load profile: ${e.message}`);
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
    } catch (e: any) {
      toastState.error(`Save failed: ${e.message}`);
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
        skillsText = '';
        loadedProfileJson = JSON.stringify({ ...data });
      } catch (e: any) {
        toastState.error(`Failed to reload profile: ${e.message}`);
      }
    }
    await invalidateAll();
  }

  function addWork() {
    profile.work_experience = [
      ...profile.work_experience,
      { company: '', role: '', start_date: '', end_date: null, bullets: [] },
    ];
  }

  function removeWork(i: number) {
    profile.work_experience = profile.work_experience.filter((_, idx) => idx !== i);
  }

  function addEdu() {
    profile.education = [
      ...profile.education,
      { institution: '', degree: '', field: '', start_date: '', end_date: null },
    ];
  }

  function removeEdu(i: number) {
    profile.education = profile.education.filter((_, idx) => idx !== i);
  }

  function addProject() {
    profile.projects = [
      ...profile.projects,
      { name: '', description: '', tech_stack: [], link: null },
    ];
  }

  function removeProject(i: number) {
    profile.projects = profile.projects.filter((_, idx) => idx !== i);
  }

  function addCert() {
    profile.certifications = [
      ...profile.certifications,
      { name: '', issuer: '', date: '' },
    ];
  }

  function removeCert(i: number) {
    profile.certifications = profile.certifications.filter((_, idx) => idx !== i);
  }

  function workBulletsText(w: WorkExperience) {
    return w.bullets.join('\n');
  }

  function setWorkBullets(i: number, text: string) {
    profile.work_experience[i].bullets = text.split('\n').map((s) => s.trim()).filter(Boolean);
  }

  function projectTechText(p: Project) {
    return p.tech_stack.join(', ');
  }

  function setProjectTech(i: number, text: string) {
    profile.projects[i].tech_stack = text.split(',').map((s) => s.trim()).filter(Boolean);
  }

  const sections = [
    { id: 'personal-info', label: 'Personal Info', icon: User },
    { id: 'skills', label: 'Core Skills', icon: Award },
    { id: 'experience', label: 'Experience', icon: Building2 },
    { id: 'education', label: 'Education', icon: GraduationCap },
    { id: 'projects', label: 'Projects', icon: FolderGit2 },
    { id: 'certifications', label: 'Certifications', icon: Award },
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

<div class="space-y-8 max-w-6xl pb-20 relative px-4 mx-auto">
  <!-- Sticky Header -->
  <div class="sticky top-0 z-50 bg-background/80 backdrop-blur-md border-b border-border -mx-4 px-4 py-4 mb-8">
    <div class="flex items-start sm:items-center justify-between flex-col sm:flex-row gap-4 max-w-6xl mx-auto">
      <div>
        <h1 class="text-2xl font-bold flex items-center gap-2">
          <User class="w-6 h-6 text-primary" />
          Profile Setup
        </h1>
        <p class="text-xs text-muted-foreground mt-0.5 font-medium uppercase tracking-wider">
          {#if activeProfile.current}
            Editing: <span style="color:{activeProfile.current.color}">{activeProfile.current.icon} {activeProfile.current.label}</span>
          {:else}
            Secure your professional baseline.
          {/if}
        </p>
      </div>
      <div class="flex items-center gap-2 self-end sm:self-auto">
        <Button variant="outline" size="sm" onclick={() => showImporter = !showImporter} class="shadow-sm h-9">
          <SparklesIcon class="w-4 h-4 mr-2 text-primary" />
          {showImporter ? 'Cancel' : 'AI Sync'}
        </Button>
        
        <Button onclick={handleSave} disabled={saving || loading} size="sm" class="shadow-sm h-9 {isDirty ? 'border-yellow-400' : ''}">
          <Save class="w-4 h-4 mr-2" />
          {saving ? 'Saving…' : isDirty ? 'Save Changes •' : 'Save Changes'}
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
    <div class="lg:hidden flex overflow-x-auto pb-4 mb-4 gap-2 no-scrollbar -mx-4 px-4 sticky top-[73px] z-40 bg-background/80 backdrop-blur-md border-b border-border/50">
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
            class="w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group
                   {activeTab === section.id 
                     ? 'bg-primary text-primary-foreground shadow-lg shadow-primary/20 translate-x-1' 
                     : 'text-muted-foreground hover:bg-muted hover:text-foreground'}"
          >
            <section.icon class="w-5 h-5 {activeTab === section.id ? 'text-primary-foreground' : 'text-muted-foreground group-hover:text-primary transition-colors'}" />
            <span class="font-medium">{section.label}</span>
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
              {#if activeTab === 'personal-info'}
                <section id="personal-info" class="p-8">
                  <div class="grid lg:grid-cols-4 gap-12 text-left">
                    <div class="space-y-1">
                      <h2 class="text-lg font-semibold flex items-center gap-2 text-foreground">
                        <User class="w-5 h-5 text-primary" />
                        Personal Info
                      </h2>
                      <p class="text-sm text-muted-foreground">Your basic identifier and contact details.</p>
                    </div>
                    <div class="lg:col-span-3 grid gap-6 sm:grid-cols-2">
                      <div class="space-y-2">
                        <Label for="name">Full Name *</Label>
                        <Input id="name" bind:value={profile.name} placeholder="Jane Doe" class="bg-background h-11 text-base" />
                      </div>
                      <div class="space-y-2">
                        <Label for="email">Email *</Label>
                        <Input id="email" type="email" bind:value={profile.email} placeholder="jane@example.com" class="bg-background h-11 text-base" />
                      </div>
                      <div class="space-y-2">
                        <Label for="phone">Phone</Label>
                        <Input id="phone" bind:value={profile.phone} placeholder="+1 234 567 8900" class="bg-background h-11 text-base" />
                      </div>
                      <div class="space-y-2">
                        <Label for="location">Location</Label>
                        <Input id="location" bind:value={profile.location} placeholder="City, Country" class="bg-background h-11 text-base" />
                      </div>
                      <div class="space-y-2">
                        <Label for="linkedin">LinkedIn</Label>
                        <Input id="linkedin" bind:value={profile.linkedin} placeholder="linkedin.com/in/username" class="bg-background h-11 text-base" />
                      </div>
                      <div class="space-y-2">
                        <Label for="github">GitHub</Label>
                        <Input id="github" bind:value={profile.github} placeholder="github.com/username" class="bg-background h-11 text-base" />
                      </div>
                      <div class="space-y-2 sm:col-span-2">
                        <Label for="portfolio">Portfolio</Label>
                        <Input id="portfolio" bind:value={profile.portfolio} placeholder="yoursite.com" class="bg-background h-11 text-base" />
                      </div>
                      <div class="space-y-2 sm:col-span-2">
                        <Label for="summary">Professional Summary</Label>
                        <Textarea id="summary" bind:value={profile.summary} placeholder="Brief professional summary explaining who you are and what you do…" rows={5} class="bg-background resize-y text-sm sm:text-base p-4" />
                      </div>
                    </div>
                  </div>
                </section>
              {/if}

              {#if activeTab === 'skills'}
                <section id="skills" class="p-8">
                  <div class="grid lg:grid-cols-4 gap-12 text-left">
                    <div class="space-y-1">
                      <h2 class="text-lg font-semibold flex items-center gap-2 text-foreground">
                        <Award class="w-5 h-5 text-primary" />
                        Core Skills
                      </h2>
                      <p class="text-sm text-muted-foreground">List your top technical and soft skills.</p>
                    </div>
                    <div class="lg:col-span-3">
                      <div class="space-y-3">
                        <Label for="skills-input" class="text-xs uppercase tracking-wider font-semibold text-muted-foreground ml-1">Professional Skills</Label>
                        
                        <!-- Integrated Tag Input -->
                        <div 
                          class="min-h-[120px] p-3 rounded-2xl border bg-background transition-all duration-200 focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary group cursor-text"
                          onclick={() => document.getElementById('skills-input')?.focus()}
                          role="presentation"
                        >
                          <div class="flex flex-wrap gap-2">
                            {#each profile.skills as skill}
                              <Badge 
                                variant="secondary" 
                                class="pl-3 pr-1.5 py-1.5 gap-1.5 text-sm bg-muted/50 hover:bg-muted border-transparent transition-all hover:scale-[1.02] active:scale-95"
                              >
                                {skill}
                                <button 
                                  onclick={(e) => { e.stopPropagation(); removeSkill(skill); }}
                                  class="hover:bg-destructive/10 rounded-full p-0.5 text-muted-foreground hover:text-destructive transition-colors"
                                  title="Remove {skill}"
                                >
                                  <X class="w-3.5 h-3.5" />
                                </button>
                              </Badge>
                            {/each}
                            
                            <input
                              id="skills-input"
                              bind:value={skillsText}
                              onkeydown={(e) => {
                                if (e.key === 'Backspace' && !skillsText && profile.skills.length > 0) {
                                  removeSkill(profile.skills[profile.skills.length - 1]);
                                } else {
                                  addSkill(e);
                                }
                              }}
                              placeholder={profile.skills.length === 0 ? "Add a skill (e.g. TypeScript, Project Management)..." : "Add more..."}
                              class="flex-1 bg-transparent border-none outline-none ring-0 min-w-[120px] py-1.5 text-base placeholder:text-muted-foreground/40"
                            />
                          </div>
                        </div>
                        <div class="flex items-center justify-between ml-1">
                          <p class="text-[11px] text-muted-foreground">Press <kbd class="px-1.5 py-0.5 rounded border bg-muted font-sans text-[10px]">Enter</kbd> or <kbd class="px-1.5 py-0.5 rounded border bg-muted font-sans text-[10px]">,</kbd> to add · or</p>
                          <Button type="button" variant="outline" size="sm" onclick={commitSkill} class="h-7 text-xs px-3">Add</Button>
                        </div>
                      </div>
                    </div>
                  </div>
                </section>
              {/if}

              {#if activeTab === 'experience'}
                <section id="experience" class="p-8">
                  <div class="grid lg:grid-cols-4 gap-12 text-left">
                    <div class="space-y-1">
                      <div class="flex items-center justify-between pr-4">
                        <h2 class="text-lg font-semibold flex items-center gap-2 text-foreground">
                          <Building2 class="w-5 h-5 text-primary" />
                          Experience
                        </h2>
                      </div>
                      <p class="text-sm text-muted-foreground">Your career milestones.</p>
                      <div class="pt-4">
                        <Button variant="outline" size="sm" onclick={addWork} class="h-9 shadow-sm w-full lg:w-auto">
                          <Plus class="w-4 h-4 mr-1" /> Add Role
                        </Button>
                      </div>
                    </div>
                    <div class="lg:col-span-3 space-y-6">
                      {#if profile.work_experience.length === 0}
                        <div class="text-center py-10 text-muted-foreground text-sm border-2 border-dashed rounded-xl bg-muted/20">
                          No work experience added yet.
                        </div>
                      {:else}
                        {#each profile.work_experience as work, i}
                          <div class="relative border rounded-xl p-5 space-y-6 bg-muted/10 group transition-all hover:bg-muted/20">
                            <div class="absolute right-4 top-4 opacity-0 group-hover:opacity-100 transition-opacity">
                              <Button variant="ghost" size="icon" class="h-8 w-8 text-destructive hover:bg-destructive/10" onclick={() => removeWork(i)}>
                                <Trash2 class="w-4 h-4" />
                              </Button>
                            </div>
                            <div class="grid gap-6 pr-10">
                              <div class="grid gap-4 sm:grid-cols-2">
                                <div class="space-y-2 text-left">
                                  <Label>Company</Label>
                                  <Input bind:value={work.company} placeholder="e.g. Google" class="bg-background h-11 text-base" />
                                </div>
                                <div class="space-y-2 text-left">
                                  <Label>Role</Label>
                                  <Input bind:value={work.role} placeholder="e.g. Senior Product Designer" class="bg-background h-11 text-base" />
                                </div>
                              </div>
                              <div class="grid gap-4 sm:grid-cols-2">
                                <div class="space-y-2 text-left">
                                  <Label>Start Date</Label>
                                  <Input bind:value={work.start_date} placeholder="e.g. Jan 2022" class="bg-background h-10" />
                                </div>
                                <div class="space-y-2 text-left">
                                  <Label>End Date</Label>
                                  <Input bind:value={work.end_date} placeholder="Present" class="bg-background h-10" />
                                </div>
                              </div>
                            </div>
                            <div class="space-y-2 text-left">
                              <Label>Accomplishments (One bullet per line)</Label>
                              <Textarea
                                value={workBulletsText(work)}
                                oninput={(e) => setWorkBullets(i, (e.target as HTMLTextAreaElement).value)}
                                placeholder="- Built X that improved Y by Z%"
                                rows={4}
                                class="bg-background resize-y p-4 text-sm sm:text-base"
                              />
                            </div>
                          </div>
                        {/each}
                      {/if}
                    </div>
                  </div>
                </section>
              {/if}

              {#if activeTab === 'education'}
                <section id="education" class="p-8">
                  <div class="grid lg:grid-cols-4 gap-12 text-left">
                    <div class="space-y-1">
                      <h2 class="text-lg font-semibold flex items-center gap-2 text-foreground">
                        <GraduationCap class="w-5 h-5 text-primary" />
                        Education
                      </h2>
                      <p class="text-sm text-muted-foreground">Your academic background.</p>
                      <div class="pt-4">
                        <Button variant="outline" size="sm" onclick={addEdu} class="h-9 shadow-sm w-full lg:w-auto">
                          <Plus class="w-4 h-4 mr-1" /> Add Degree
                        </Button>
                      </div>
                    </div>
                    <div class="lg:col-span-3 space-y-6 text-left">
                      {#if profile.education.length === 0}
                        <div class="text-center py-10 text-muted-foreground text-sm border-2 border-dashed rounded-xl bg-muted/20">
                          No education added yet.
                        </div>
                      {:else}
                        {#each profile.education as edu, i}
                          <div class="relative border rounded-xl p-5 space-y-6 bg-muted/10 group transition-all hover:bg-muted/20">
                            <div class="absolute right-4 top-4 opacity-0 group-hover:opacity-100 transition-opacity">
                              <Button variant="ghost" size="icon" class="h-8 w-8 text-destructive hover:bg-destructive/10" onclick={() => removeEdu(i)}>
                                <Trash2 class="w-4 h-4" />
                              </Button>
                            </div>
                            <div class="grid gap-6 pr-10">
                              <div class="space-y-2 text-left">
                                <Label>Institution</Label>
                                <Input bind:value={edu.institution} placeholder="e.g. Massachusetts Institute of Technology" class="bg-background h-11 text-base placeholder:text-muted-foreground/40" />
                              </div>
                              
                              <div class="grid gap-4 sm:grid-cols-3">
                                <div class="space-y-2 text-left">
                                  <Label>Degree</Label>
                                  <Input bind:value={edu.degree} placeholder="e.g. Master's" class="bg-background h-10" />
                                </div>
                                <div class="space-y-2 text-left">
                                  <Label>Start Date</Label>
                                  <Input bind:value={edu.start_date} placeholder="e.g. Sep 2018" class="bg-background h-10" />
                                </div>
                                <div class="space-y-2 text-left">
                                  <Label>End Date</Label>
                                  <Input bind:value={edu.end_date} placeholder="e.g. Jun 2022" class="bg-background h-10" />
                                </div>
                              </div>

                              <div class="space-y-2 text-left">
                                <Label>Field of Study</Label>
                                <Input bind:value={edu.field} placeholder="e.g. Computer Science & Engineering" class="bg-background h-11 text-base placeholder:text-muted-foreground/40" />
                              </div>
                            </div>
                          </div>
                        {/each}
                      {/if}
                    </div>
                  </div>
                </section>
              {/if}

              {#if activeTab === 'projects'}
                <section id="projects" class="p-8">
                  <div class="grid lg:grid-cols-4 gap-12 text-left">
                    <div class="space-y-1">
                      <h2 class="text-lg font-semibold flex items-center gap-2 text-foreground">
                        <FolderGit2 class="w-5 h-5 text-primary" />
                        Projects
                      </h2>
                      <p class="text-sm text-muted-foreground">Portfolio worthy work.</p>
                      <div class="pt-4">
                        <Button variant="outline" size="sm" onclick={addProject} class="h-9 shadow-sm w-full lg:w-auto">
                          <Plus class="w-4 h-4 mr-1" /> Add Project
                        </Button>
                      </div>
                    </div>
                    <div class="lg:col-span-3 space-y-6 text-left">
                      {#if profile.projects.length === 0}
                        <div class="text-center py-10 text-muted-foreground text-sm border-2 border-dashed rounded-xl bg-muted/20">
                          No projects added yet.
                        </div>
                      {:else}
                        {#each profile.projects as proj, i}
                          <div class="relative border rounded-xl p-5 space-y-6 bg-muted/10 group transition-all hover:bg-muted/20">
                            <div class="absolute right-4 top-4 opacity-0 group-hover:opacity-100 transition-opacity">
                              <Button variant="ghost" size="icon" class="h-8 w-8 text-destructive hover:bg-destructive/10" onclick={() => removeProject(i)}>
                                <Trash2 class="w-4 h-4" />
                              </Button>
                            </div>
                            <div class="grid gap-6 pr-10">
                              <div class="grid gap-4 sm:grid-cols-2">
                                <div class="space-y-2 text-left">
                                  <Label>Project Name</Label>
                                  <Input bind:value={proj.name} placeholder="e.g. AI Workflow Automator" class="bg-background h-11 text-base placeholder:text-muted-foreground/40" />
                                </div>
                                <div class="space-y-2 text-left">
                                  <Label>External Link</Label>
                                  <Input bind:value={proj.link} placeholder="https://github.com/..." class="bg-background h-11 text-base" />
                                </div>
                              </div>
                              <div class="space-y-2 text-left">
                                <Label>Description</Label>
                                <Textarea bind:value={proj.description} placeholder="Describe the core problem, your approach, and key technical challenges..." rows={3} class="bg-background resize-y p-4 text-sm sm:text-base" />
                              </div>
                              <div class="space-y-2 text-left">
                                <Label>Tech Stack</Label>
                                <Input
                                  value={projectTechText(proj)}
                                  oninput={(e) => setProjectTech(i, (e.target as HTMLInputElement).value)}
                                  placeholder="e.g. React, Svelte, Go, PostgreSQL"
                                  class="bg-background h-11 text-base"
                                />
                              </div>
                            </div>
                          </div>
                        {/each}
                      {/if}
                    </div>
                  </div>
                </section>
              {/if}

              {#if activeTab === 'certifications'}
                <section id="certifications" class="p-8">
                  <div class="grid lg:grid-cols-4 gap-12 text-left">
                    <div class="space-y-1">
                      <h2 class="text-lg font-semibold flex items-center gap-2 text-foreground">
                        <Award class="w-5 h-5 text-primary" />
                        Certifications
                      </h2>
                      <p class="text-sm text-muted-foreground">Validations of your skills.</p>
                      <div class="pt-4">
                        <Button variant="outline" size="sm" onclick={addCert} class="h-9 shadow-sm w-full lg:w-auto">
                          <Plus class="w-4 h-4 mr-1" /> Add Cert
                        </Button>
                      </div>
                    </div>
                    <div class="lg:col-span-3 space-y-6 text-left">
                      {#if profile.certifications.length === 0}
                        <div class="text-center py-10 text-muted-foreground text-sm border-2 border-dashed rounded-xl bg-muted/20">
                          No certifications added yet.
                        </div>
                      {:else}
                        {#each profile.certifications as cert, i}
                          <div class="relative border rounded-xl p-5 space-y-6 bg-muted/10 group transition-all hover:bg-muted/20">
                            <div class="absolute right-4 top-4 opacity-0 group-hover:opacity-100 transition-opacity">
                              <Button variant="ghost" size="icon" class="h-8 w-8 text-destructive hover:bg-destructive/10" onclick={() => removeCert(i)}>
                                <Trash2 class="w-4 h-4" />
                              </Button>
                            </div>
                            <div class="grid gap-6 pr-10">
                              <div class="grid gap-4 sm:grid-cols-2">
                                <div class="space-y-2 text-left">
                                  <Label>Certification Name</Label>
                                  <Input bind:value={cert.name} placeholder="e.g. AWS Certified Developer" class="bg-background h-11 text-base placeholder:text-muted-foreground/40" />
                                </div>
                                <div class="space-y-2 text-left">
                                  <Label>Issuer</Label>
                                  <Input bind:value={cert.issuer} placeholder="e.g. Amazon Web Services" class="bg-background h-11 text-base placeholder:text-muted-foreground/40" />
                                </div>
                              </div>
                              <div class="space-y-2 text-left max-w-[240px]">
                                <Label>Date</Label>
                                <Input bind:value={cert.date} placeholder="e.g. March 2024" class="bg-background h-10" />
                              </div>
                            </div>
                          </div>
                        {/each}
                      {/if}
                    </div>
                  </div>
                </section>
              {/if}
            </div>
          {/if}
        </CardContent>
      </Card>
    </div>
  </div>
</div>
