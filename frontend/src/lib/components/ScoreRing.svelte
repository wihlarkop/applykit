<script lang="ts">
	import { getScoreColor } from '$lib/utils';

	interface Props {
		score: number;
		size?: number;
		strokeWidth?: number;
		class?: string;
	}

	let { score, size = 80, strokeWidth = 7, class: className = '' }: Props = $props();

	const radius = $derived((size - strokeWidth) / 2);
	const circumference = $derived(2 * Math.PI * radius);
	const offset = $derived(circumference * (1 - score / 100));

	const color = $derived(getScoreColor(score).hex);

	const textColor = $derived(
		score >= 70 ? 'text-green-600 dark:text-green-400' :
		score >= 40 ? 'text-yellow-600 dark:text-yellow-400' :
		'text-red-600 dark:text-red-400'
	);
</script>

<div class="relative shrink-0 {className}" style="width:{size}px;height:{size}px">
  <svg width={size} height={size} viewBox="0 0 {size} {size}">
    <circle
      cx={size/2}
      cy={size/2}
      r={radius}
      fill="none"
      stroke="currentColor"
      stroke-width={strokeWidth}
      class="text-black/10 dark:text-white/10"
    />
    <circle
      cx={size/2}
      cy={size/2}
      r={radius}
      fill="none"
      stroke-width={strokeWidth}
      stroke-linecap="round"
      stroke-dasharray={circumference}
      stroke-dashoffset={offset}
      stroke={color}
      style="transform: rotate(-90deg); transform-origin: 50% 50%; transition: stroke-dashoffset 0.8s cubic-bezier(0.34,1.2,0.64,1);"
    />
  </svg>
  <div class="absolute inset-0 flex flex-col items-center justify-center">
    <span class="text-xl font-black leading-none {textColor}" style="font-variant-numeric: tabular-nums">{score}</span>
    <span class="text-[9px] font-bold {textColor} opacity-70">%</span>
  </div>
</div>
