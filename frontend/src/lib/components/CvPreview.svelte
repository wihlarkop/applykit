<script lang="ts">
  import type { ProfileData } from '$lib/types';

  let { profile }: { profile: ProfileData } = $props();

  function toHref(url: string): string {
    if (!url) return '#';
    if (url.startsWith('http://') || url.startsWith('https://')) return url;
    return 'https://' + url;
  }
</script>

<div class="cv-preview font-sans text-[13px] leading-snug text-foreground dark:text-zinc-100 print:text-black max-w-200 mx-auto p-8 bg-transparent">
  <!-- Header -->
  <div class="text-center mb-4">
    <h1 class="text-2xl font-bold uppercase tracking-wide text-foreground dark:text-white print:text-black">{profile.name}</h1>
    <div class="flex flex-wrap justify-center gap-x-3 gap-y-0.5 mt-1 text-xs text-muted-foreground dark:text-zinc-400 print:text-gray-600">
      {#if profile.email}<a href="mailto:{profile.email}" target="_blank" rel="noopener noreferrer" class="hover:text-primary transition-colors print:text-blue-600">{profile.email}</a>{/if}
      {#if profile.phone}<a href="tel:{profile.phone}" class="hover:text-primary transition-colors print:text-blue-600">{profile.phone}</a>{/if}
      {#if profile.location}<span>{profile.location}</span>{/if}
      {#if profile.linkedin}<a href={toHref(profile.linkedin)} target="_blank" rel="noopener noreferrer" class="hover:text-primary transition-colors print:text-blue-600">{profile.linkedin}</a>{/if}
      {#if profile.github}<a href={toHref(profile.github)} target="_blank" rel="noopener noreferrer" class="hover:text-primary transition-colors print:text-blue-600">{profile.github}</a>{/if}
      {#if profile.portfolio}<a href={toHref(profile.portfolio)} target="_blank" rel="noopener noreferrer" class="hover:text-primary transition-colors print:text-blue-600">{profile.portfolio}</a>{/if}
    </div>
  </div>

  {#if profile.summary}
    <section class="mb-4">
      <h2 class="text-xs font-bold uppercase tracking-widest border-b border-border dark:border-zinc-700 print:border-black pb-0.5 mb-2 text-foreground dark:text-zinc-200">Summary</h2>
      <p class="text-muted-foreground dark:text-zinc-300 print:text-black">{profile.summary}</p>
    </section>
  {/if}

  {#if profile.work_experience.length}
    <section class="mb-4">
      <h2 class="text-xs font-bold uppercase tracking-widest border-b border-border dark:border-zinc-700 print:border-black pb-0.5 mb-2 text-foreground dark:text-zinc-200">Experience</h2>
      {#each profile.work_experience as w}
        <div class="mb-3">
          <div class="flex justify-between items-baseline">
            <span class="font-semibold text-foreground dark:text-zinc-200">{w.role}</span>
            <span class="text-xs text-muted-foreground dark:text-zinc-500 print:text-gray-500">{w.start_date} – {w.end_date ?? 'Present'}</span>
          </div>
          <div class="text-xs text-muted-foreground dark:text-zinc-400 print:text-gray-600 mb-1">{w.company}</div>
          {#if w.bullets.length}
            <ul class="list-disc list-inside space-y-0.5">
              {#each w.bullets as b}<li>{b}</li>{/each}
            </ul>
          {/if}
        </div>
      {/each}
    </section>
  {/if}

  {#if profile.education.length}
    <section class="mb-4">
      <h2 class="text-xs font-bold uppercase tracking-widest border-b border-border dark:border-zinc-700 print:border-black pb-0.5 mb-2 text-foreground dark:text-zinc-200">Education</h2>
      {#each profile.education as e}
        <div class="mb-2">
          <div class="flex justify-between items-baseline">
            <span class="font-semibold text-foreground dark:text-zinc-200">{e.degree} in {e.field}</span>
            <span class="text-xs text-muted-foreground dark:text-zinc-500 print:text-gray-500">{e.start_date} – {e.end_date ?? 'Present'}</span>
          </div>
          <div class="text-xs text-muted-foreground dark:text-zinc-400 print:text-gray-600">{e.institution}</div>
        </div>
      {/each}
    </section>
  {/if}

  {#if profile.skills.length}
    <section class="mb-4">
      <h2 class="text-xs font-bold uppercase tracking-widest border-b border-border dark:border-zinc-700 print:border-black pb-0.5 mb-2 text-foreground dark:text-zinc-200">Skills</h2>
      <p class="text-muted-foreground dark:text-zinc-300 print:text-black">{profile.skills.join(' · ')}</p>
    </section>
  {/if}

  {#if profile.projects.length}
    <section class="mb-4">
      <h2 class="text-xs font-bold uppercase tracking-widest border-b border-border dark:border-zinc-700 print:border-black pb-0.5 mb-2 text-foreground dark:text-zinc-200">Projects</h2>
      {#each profile.projects as p}
        <div class="mb-2">
          <div class="flex justify-between items-baseline">
            <span class="font-semibold text-foreground dark:text-zinc-200">{p.name}</span>
            {#if p.link}<a href={toHref(p.link)} target="_blank" rel="noopener noreferrer" class="text-xs text-primary dark:text-blue-400 print:text-blue-600 hover:underline">{p.link}</a>{/if}
          </div>
          <p class="text-muted-foreground dark:text-zinc-300 print:text-black">{p.description}</p>
          {#if p.tech_stack.length}
            <p class="text-xs text-muted-foreground dark:text-zinc-500 print:text-gray-500 mt-0.5">{p.tech_stack.join(', ')}</p>
          {/if}
        </div>
      {/each}
    </section>
  {/if}

  {#if profile.certifications.length}
    <section class="mb-4">
      <h2 class="text-xs font-bold uppercase tracking-widest border-b border-border dark:border-zinc-700 print:border-black pb-0.5 mb-2 text-foreground dark:text-zinc-200">Certifications</h2>
      {#each profile.certifications as c}
        <div class="flex justify-between text-sm mb-1">
          <span class="text-foreground dark:text-zinc-200">{c.name} — <span class="text-muted-foreground dark:text-zinc-400 print:text-gray-600">{c.issuer}</span></span>
          <span class="text-xs text-muted-foreground dark:text-zinc-500 print:text-gray-500">{c.date}</span>
        </div>
      {/each}
    </section>
  {/if}
</div>
