import { describe, expect, test } from 'bun:test';

import { compareApplications } from './tracker-sort';
import type { ApplicationEntry } from './types';

function app(overrides: Partial<ApplicationEntry>): ApplicationEntry {
	return {
		id: 1,
		company_name: 'Acme',
		role_title: 'Engineer',
		status: 'applied',
		job_url: null,
		notes: null,
		applied_date: null,
		created_at: '2026-01-01T00:00:00Z',
		profile_id: null,
		profile_label: null,
		profile_color: null,
		profile_icon: null,
		match_score: null,
		linked_cover_letter_id: null,
		linked_cv_id: null,
		location: null,
		salary: null,
		job_description: null,
		...overrides
	};
}

describe('compareApplications', () => {
	test('sorts strings ascending and descending', () => {
		const a = app({ company_name: 'Beta' });
		const b = app({ company_name: 'Alpha' });
		expect(compareApplications(a, b, 'company_name', 'asc')).toBeGreaterThan(0);
		expect(compareApplications(a, b, 'company_name', 'desc')).toBeLessThan(0);
	});

	test('sorts numbers ascending and descending', () => {
		const a = app({ match_score: 90 });
		const b = app({ match_score: 40 });
		expect(compareApplications(a, b, 'match_score', 'asc')).toBeGreaterThan(0);
		expect(compareApplications(a, b, 'match_score', 'desc')).toBeLessThan(0);
	});

	test('nulls sort last regardless of direction', () => {
		const withDate = app({ applied_date: '2026-01-01' });
		const withoutDate = app({ applied_date: null });

		// Ascending: null should still come after the real value.
		expect(compareApplications(withoutDate, withDate, 'applied_date', 'asc')).toBeGreaterThan(0);
		expect(compareApplications(withDate, withoutDate, 'applied_date', 'asc')).toBeLessThan(0);

		// Descending: null must NOT jump to the front.
		expect(compareApplications(withoutDate, withDate, 'applied_date', 'desc')).toBeGreaterThan(0);
		expect(compareApplications(withDate, withoutDate, 'applied_date', 'desc')).toBeLessThan(0);
	});

	test('two nulls are equal', () => {
		const a = app({ applied_date: null });
		const b = app({ applied_date: null });
		expect(compareApplications(a, b, 'applied_date', 'asc')).toBe(0);
		expect(compareApplications(a, b, 'applied_date', 'desc')).toBe(0);
	});
});
