import { describe, expect, test } from 'bun:test';

import { formatApplicationSalary, formatExcitement, formatSalaryRange } from './utils';

describe('formatSalaryRange', () => {
	test('formats a min-max range', () => {
		expect(formatSalaryRange(120_000, 150_000)).toBe('$120K - $150K');
	});

	test('collapses an equal min and max to a single value', () => {
		expect(formatSalaryRange(120_000, 120_000)).toBe('$120K');
	});

	test('formats min-only as open-ended', () => {
		expect(formatSalaryRange(120_000, null)).toBe('$120K+');
	});

	test('formats max-only as an upper bound', () => {
		expect(formatSalaryRange(null, 150_000)).toBe('Up to $150K');
	});

	test('formats neither value as an em dash', () => {
		expect(formatSalaryRange(null, null)).toBe('—');
	});
});

describe('formatExcitement', () => {
	test('renders filled and empty stars', () => {
		expect(formatExcitement(3)).toBe('★★★☆☆');
	});

	test('renders an em dash when unrated', () => {
		expect(formatExcitement(null)).toBe('—');
	});
});

describe('formatApplicationSalary', () => {
	test('prefers the structured range when available', () => {
		expect(formatApplicationSalary(120_000, 150_000, 'Competitive')).toBe('$120K - $150K');
	});

	test('falls back to the original salary text when no range is available', () => {
		expect(formatApplicationSalary(null, null, ' Competitive ')).toBe('Competitive');
	});

	test('shows an em dash when neither salary value is available', () => {
		expect(formatApplicationSalary(null, null, null)).toBe('—');
	});
});
