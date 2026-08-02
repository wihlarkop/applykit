export function nextModelIndex(currentIndex: number, itemCount: number, key: string): number {
	if (itemCount <= 0) return 0;
	if (key === 'ArrowDown') return Math.min(currentIndex + 1, itemCount - 1);
	if (key === 'ArrowUp') return Math.max(currentIndex - 1, 0);

	return Math.min(Math.max(currentIndex, 0), itemCount - 1);
}

export function selectedModelForKey(
	key: string,
	activeIndex: number,
	modelValues: string[],
): string | null {
	if (key !== 'Enter') return null;

	return modelValues[activeIndex] ?? null;
}
