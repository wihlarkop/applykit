<script lang="ts">
  let { text }: { text: string } = $props();
</script>

<div class="cover-letter-preview mx-auto max-w-[48rem] whitespace-pre-wrap bg-transparent p-8 font-sans text-[15px] leading-7 text-foreground dark:text-zinc-100 sm:p-10 lg:p-12 print:p-0 print:text-black">
  {text}
</div>
