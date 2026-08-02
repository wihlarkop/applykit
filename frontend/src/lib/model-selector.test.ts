import { describe, expect, test } from 'bun:test';
import { nextModelIndex, selectedModelForKey } from '$lib/model-selector';

describe('inline model browser keyboard navigation', () => {
	test('moves within result boundaries', () => {
		expect(nextModelIndex(0, 3, 'ArrowDown')).toBe(1);
		expect(nextModelIndex(2, 3, 'ArrowDown')).toBe(2);
		expect(nextModelIndex(2, 3, 'ArrowUp')).toBe(1);
		expect(nextModelIndex(0, 3, 'ArrowUp')).toBe(0);
		expect(nextModelIndex(0, 0, 'ArrowDown')).toBe(0);
	});

	test('selects only on Enter with a valid active result', () => {
		const models = ['gemini/a', 'gemini/b'];

		expect(selectedModelForKey('Enter', 1, models)).toBe('gemini/b');
		expect(selectedModelForKey('Escape', 1, models)).toBeNull();
		expect(selectedModelForKey('Enter', 4, models)).toBeNull();
	});
});
