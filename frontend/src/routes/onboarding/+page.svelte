<script lang="ts">
  import { goto, invalidateAll } from '$app/navigation';
  import CvImporter from '$lib/components/CvImporter.svelte';
  import { Button } from '$lib/components/ui/button';
  import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '$lib/components/ui/card';
  import { toastState } from '$lib/toast.svelte';
  import { ArrowRight, CheckCircle2, Sparkles, User } from '@lucide/svelte';
  import confetti from 'canvas-confetti';

  let step = $state<'intro' | 'import' | 'done'>('intro');

  async function handleOnboarded() {
    toastState.success('Profile setup complete! Welcome aboard.');
    // Force layout to re-check onboarding status
    await invalidateAll();
    step = 'done';

    // Celebrate!
    confetti({
      particleCount: 150,
      spread: 70,
      origin: { y: 0.6 },
      colors: ['#3b82f6', '#8b5cf6', '#10b981']
    });
  }

  function startManual() {
    goto('/profile');
  }
</script>

<div class="min-h-[80vh] flex items-center justify-center py-10">
  <div class="w-full max-w-4xl space-y-8 px-4">

    {#if step === 'intro'}
      <div class="text-center space-y-4 mb-12 animate-in fade-in slide-in-from-top-4 duration-700">
        <div class="inline-flex items-center rounded-full border bg-primary/10 px-3 py-1 text-sm font-medium text-primary mb-2">
          <Sparkles class="mr-2 h-4 w-4" />
          Welcome to ApplyKit
        </div>
        <h1 class="text-4xl sm:text-5xl font-extrabold tracking-tight">Let's set up your <span class="text-primary">Profile</span></h1>
        <p class="text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed">
          Your profile is the core of ApplyKit. It helps us generate tailored CVs and cover letters just for you.
        </p>
      </div>

      <div class="grid gap-8 sm:grid-cols-2 animate-in fade-in slide-in-from-bottom-8 duration-700 delay-200">
        <!-- AI Path -->
        <Card class="relative overflow-hidden group hover:shadow-2xl hover:border-primary transition-all duration-300 border-2 bg-card">
          <div class="absolute -right-10 -top-10 w-40 h-40 bg-primary/5 rounded-full pointer-events-none group-hover:scale-150 transition-transform duration-700"></div>
          <CardHeader class="pb-6">
            <div class="w-14 h-14 bg-primary text-primary-foreground rounded-2xl flex items-center justify-center mb-4 shadow-lg group-hover:scale-110 transition-transform">
              <Sparkles class="w-8 h-8" />
            </div>
            <CardTitle class="text-2xl">Use AI Assistant</CardTitle>
            <CardDescription class="text-base">Upload your existing CV or paste your LinkedIn bio. Our AI will extract your experience, education, and skills in seconds.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onclick={() => step = 'import'} class="w-full h-12 text-lg rounded-xl shadow-md">
              Start with AI
              <ArrowRight class="ml-2 w-5 h-5" />
            </Button>
            <p class="text-center text-xs text-muted-foreground mt-4 font-medium flex items-center justify-center gap-1">
              <CheckCircle2 class="w-3 h-3 text-green-500" /> RECOMMENDED
            </p>
          </CardContent>
        </Card>

        <!-- Manual Path -->
        <Card class="relative overflow-hidden group hover:shadow-xl hover:border-border transition-all duration-300 border-2 bg-card">
          <CardHeader class="pb-6">
            <div class="w-14 h-14 bg-muted text-muted-foreground rounded-2xl flex items-center justify-center mb-4 border shadow-sm group-hover:bg-primary/10 group-hover:text-primary transition-colors">
              <User class="w-8 h-8" />
            </div>
            <CardTitle class="text-2xl">Manual Setup</CardTitle>
            <CardDescription class="text-base">Prefer doing it yourself? Enter your information manually step-by-step. You can always change it later.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onclick={startManual} variant="outline" class="w-full h-12 text-lg rounded-xl">
              I'll type it myself
            </Button>
          </CardContent>
        </Card>
      </div>

    {:else if step === 'import'}
      <div class="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
        <div class="flex items-center gap-4 border-b border-border pb-6">
          <Button onclick={() => step = 'intro'} variant="ghost" size="sm" class="rounded-full">
            ← Back
          </Button>
          <div>
            <h2 class="text-2xl font-bold">Import from Existing CV</h2>
            <p class="text-muted-foreground text-sm">Paste text or upload a PDF to populate your profile automatically.</p>
          </div>
        </div>

        <CvImporter onSaveSuccess={handleOnboarded} />
      </div>

    {:else if step === 'done'}
      <div class="text-center space-y-8 py-10 animate-in zoom-in-95 fade-in duration-500">
        <div class="w-24 h-24 bg-green-500 text-white rounded-full flex items-center justify-center mx-auto shadow-xl">
          <CheckCircle2 class="w-12 h-12" />
        </div>
        <div class="space-y-3">
          <h2 class="text-4xl font-extrabold tracking-tight">You're all set!</h2>
          <p class="text-xl text-muted-foreground max-w-md mx-auto">
            Your profile is ready. You can now start generating high-impact CVs and cover letters.
          </p>
        </div>

        <div class="pt-4">
          <Button href="/" size="lg" class="rounded-full px-12 h-12 shadow-md">
            Go to Dashboard
            <ArrowRight class="ml-2 w-5 h-5" />
          </Button>
        </div>
      </div>
    {/if}

  </div>
</div>
