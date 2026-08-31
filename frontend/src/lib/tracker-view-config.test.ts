import { beforeEach, describe, expect, test } from 'bun:test';

// bun's test runtime has no global localStorage; provide a minimal in-memory
// stand-in so loadTrackerViewConfigState/saveTrackerViewConfigState can be exercised
// for real instead of only checking source text (this repo's usual pattern
// for anything touching localStorage).
class MemoryStorage {
	private store = new Map<string, string>();
	getItem(key: string) {
		return this.store.has(key) ? this.store.get(key)! : null;
	}
	setItem(key: string, value: string) {
		this.store.set(key, value);
	}
	clear() {
		this.store.clear();
	}
}
(globalThis as unknown as { localStorage: MemoryStorage }).localStorage = new MemoryStorage();

import {
	applicationsToCsv,
	defaultTrackerViewConfigState,
	groupApplications,
	loadTrackerViewConfigState,
	saveTrackerViewConfigState,
	visibleOrderedColumns,
} from './tracker-view-config';
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
		min_salary: null,
		max_salary: null,
		excitement: null,
		date_posted: null,
		deadline: null,
		follow_up: null,
		job_description: null,
		...overrides
	};
}

beforeEach(() => {
	(globalThis.localStorage as unknown as MemoryStorage).clear();
});

describe('visibleOrderedColumns', () => {
	test('respects saved order and hides hidden columns', () => {
		const config = defaultTrackerViewConfigState();
		config.columnOrder = ['status', 'company_name', 'role_title', ...config.columnOrder.filter(
			(k) => !['status', 'company_name', 'role_title'].includes(k)
		)];
		config.hiddenColumns = ['role_title'];

		const result = visibleOrderedColumns(config);
		expect(result.map((c) => c.key)).toEqual([
			'status',
			'company_name',
			'min_salary',
			'location',
			'match_score',
			'excitement',
			'date_posted',
			'created_at',
			'applied_date',
			'deadline',
			'follow_up',
		]);
	});
});

describe('groupApplications', () => {
	test('groupBy none returns a single unlabeled group with all apps', () => {
		const apps = [app({ id: 1 }), app({ id: 2 })];
		const groups = groupApplications(apps, 'none');
		expect(groups).toHaveLength(1);
		expect(groups[0].items).toHaveLength(2);
	});

	test('groups by status and sorts group labels alphabetically', () => {
		const apps = [
			app({ id: 1, status: 'rejected' }),
			app({ id: 2, status: 'applied' }),
			app({ id: 3, status: 'applied' }),
		];
		const groups = groupApplications(apps, 'status');
		expect(groups.map((g) => g.label)).toEqual(['applied', 'rejected']);
		expect(groups[0].items).toHaveLength(2);
		expect(groups[1].items).toHaveLength(1);
	});

	test('groups falsy values under "Unspecified"', () => {
		const apps = [app({ id: 1, location: null }), app({ id: 2, location: '' })];
		const groups = groupApplications(apps, 'location');
		expect(groups).toHaveLength(1);
		expect(groups[0].label).toBe('Unspecified');
		expect(groups[0].items).toHaveLength(2);
	});
});

describe('applicationsToCsv', () => {
	test('emits a header row and one row per application', () => {
		const csv = applicationsToCsv([app({ company_name: 'Acme', role_title: 'Engineer' })]);
		const lines = csv.split('\n');
		expect(lines[0]).toContain('Company');
		expect(lines[1]).toContain('Acme');
		expect(lines[1]).toContain('Engineer');
	});

	test('escapes commas, quotes, and newlines', () => {
		const csv = applicationsToCsv([
			app({ notes: 'Line one,\nwith a "quote"' })
		]);
		expect(csv).toContain('"Line one,\nwith a ""quote"""');
	});

	test('renders null fields as empty', () => {
		const csv = applicationsToCsv([app({ location: null })]);
		const [header, row] = csv.split('\n');
		const locationIndex = header.split(',').indexOf('Location');
		expect(row.split(',')[locationIndex]).toBe('');
	});

	test('neutralizes leading formula characters to prevent CSV injection', () => {
		for (const dangerous of ['=cmd', '+1+1', '-2+3', '@SUM(A1)']) {
			const csv = applicationsToCsv([app({ company_name: dangerous })]);
			const row = csv.split('\n')[1];
			expect(row.startsWith(`'${dangerous}`)).toBe(true);
		}
	});
});

describe('loadTrackerViewConfigState / saveTrackerViewConfigState', () => {
	test('round-trips a saved config', () => {
		const config = defaultTrackerViewConfigState();
		config.groupBy = 'status';
		config.hiddenColumns = ['excitement'];
		saveTrackerViewConfigState(config);

		const loaded = loadTrackerViewConfigState();
		expect(loaded.groupBy).toBe('status');
		expect(loaded.hiddenColumns).toEqual(['excitement']);
	});

	test('falls back to defaults when nothing is saved', () => {
		const loaded = loadTrackerViewConfigState();
		expect(loaded).toEqual(defaultTrackerViewConfigState());
	});

	test('merges in columns missing from an older saved config', () => {
		saveTrackerViewConfigState({
			columnOrder: ['company_name', 'role_title'],
			hiddenColumns: [],
			groupBy: 'none',
			hiddenCardFields: [],
		});

		const loaded = loadTrackerViewConfigState();
		// The two saved columns keep their position; everything else is appended.
		expect(loaded.columnOrder.slice(0, 2)).toEqual(['company_name', 'role_title']);
		expect(loaded.columnOrder).toHaveLength(defaultTrackerViewConfigState().columnOrder.length);
	});
});
