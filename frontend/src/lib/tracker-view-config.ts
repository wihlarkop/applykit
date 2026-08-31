import type { ApplicationEntry } from './types';
import type { ApplicationSortColumn } from './tracker-sort';

export const ALL_COLUMNS: { key: ApplicationSortColumn; label: string }[] = [
	{ key: 'company_name', label: 'Company' },
	{ key: 'role_title', label: 'Role' },
	{ key: 'status', label: 'Status' },
	{ key: 'min_salary', label: 'Salary' },
	{ key: 'location', label: 'Location' },
	{ key: 'match_score', label: 'Match' },
	{ key: 'excitement', label: 'Excitement' },
	{ key: 'date_posted', label: 'Posted' },
	{ key: 'created_at', label: 'Saved' },
	{ key: 'applied_date', label: 'Applied' },
	{ key: 'deadline', label: 'Deadline' },
	{ key: 'follow_up', label: 'Follow up' },
];

export type GroupByOption = 'none' | 'status' | 'company_name' | 'location';

export const GROUP_BY_OPTIONS: { value: GroupByOption; label: string }[] = [
	{ value: 'none', label: 'None' },
	{ value: 'status', label: 'Status' },
	{ value: 'company_name', label: 'Company' },
	{ value: 'location', label: 'Location' },
];

export type CardFieldKey = 'date' | 'match_score' | 'documents';

export const ALL_CARD_FIELDS: { key: CardFieldKey; label: string }[] = [
	{ key: 'date', label: 'Applied Date' },
	{ key: 'match_score', label: 'Match Score' },
	{ key: 'documents', label: 'Linked Documents' },
];

export interface TrackerViewConfigState {
	columnOrder: ApplicationSortColumn[];
	hiddenColumns: ApplicationSortColumn[];
	groupBy: GroupByOption;
	hiddenCardFields: CardFieldKey[];
}

export function defaultTrackerViewConfigState(): TrackerViewConfigState {
	return {
		columnOrder: ALL_COLUMNS.map((c) => c.key),
		hiddenColumns: [],
		groupBy: 'none',
		hiddenCardFields: [],
	};
}

const STORAGE_KEY = 'applykit:tracker-view-config';

export function loadTrackerViewConfigState(): TrackerViewConfigState {
	const fallback = defaultTrackerViewConfigState();
	try {
		const raw = localStorage.getItem(STORAGE_KEY);
		if (!raw) return fallback;
		const parsed = JSON.parse(raw) as Partial<TrackerViewConfigState>;
		// Merge over defaults so a newly added column/field still shows up
		// for users with an existing saved config from before it existed.
		const knownColumns = new Set(ALL_COLUMNS.map((c) => c.key));
		const savedOrder = (parsed.columnOrder ?? []).filter((k) => knownColumns.has(k));
		const missingColumns = fallback.columnOrder.filter((k) => !savedOrder.includes(k));
		return {
			columnOrder: [...savedOrder, ...missingColumns],
			hiddenColumns: (parsed.hiddenColumns ?? []).filter((k) => knownColumns.has(k)),
			groupBy: parsed.groupBy ?? fallback.groupBy,
			hiddenCardFields: parsed.hiddenCardFields ?? fallback.hiddenCardFields,
		};
	} catch {
		return fallback;
	}
}

export function saveTrackerViewConfigState(config: TrackerViewConfigState): void {
	try {
		localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
	} catch {
		// Best-effort persistence; a private-browsing/blocked-storage failure
		// just means the preference doesn't survive a reload.
	}
}

export function visibleOrderedColumns(
	config: TrackerViewConfigState
): { key: ApplicationSortColumn; label: string }[] {
	const byKey = new Map(ALL_COLUMNS.map((c) => [c.key, c.label]));
	return config.columnOrder
		.filter((key) => !config.hiddenColumns.includes(key))
		.map((key) => ({ key, label: byKey.get(key) ?? key }));
}

export function groupApplications(
	apps: ApplicationEntry[],
	groupBy: GroupByOption
): { label: string; items: ApplicationEntry[] }[] {
	if (groupBy === 'none') return [{ label: '', items: apps }];

	const groups = new Map<string, ApplicationEntry[]>();
	for (const app of apps) {
		const raw = groupBy === 'status' ? app.status : app[groupBy];
		const label = raw || 'Unspecified';
		if (!groups.has(label)) groups.set(label, []);
		groups.get(label)!.push(app);
	}
	return [...groups.entries()]
		.sort(([a], [b]) => a.localeCompare(b))
		.map(([label, items]) => ({ label, items }));
}

const CSV_COLUMNS: { key: keyof ApplicationEntry; header: string }[] = [
	{ key: 'company_name', header: 'Company' },
	{ key: 'role_title', header: 'Role' },
	{ key: 'status', header: 'Status' },
	{ key: 'min_salary', header: 'Min Salary' },
	{ key: 'max_salary', header: 'Max Salary' },
	{ key: 'location', header: 'Location' },
	{ key: 'match_score', header: 'Match Score' },
	{ key: 'excitement', header: 'Excitement' },
	{ key: 'date_posted', header: 'Date Posted' },
	{ key: 'created_at', header: 'Date Saved' },
	{ key: 'applied_date', header: 'Date Applied' },
	{ key: 'deadline', header: 'Deadline' },
	{ key: 'follow_up', header: 'Follow Up' },
	{ key: 'job_url', header: 'Job URL' },
	{ key: 'notes', header: 'Notes' },
];

function csvEscape(value: unknown): string {
	if (value === null || value === undefined) return '';
	let s = String(value);
	// Neutralize formula injection: some fields (company/role) can come from a
	// scraped job posting, not just direct user input, and a leading =/+/-/@
	// would run as a formula if the export is opened in Excel/Sheets.
	if (/^[=+\-@]/.test(s)) s = `'${s}`;
	return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function applicationsToCsv(apps: ApplicationEntry[]): string {
	const header = CSV_COLUMNS.map((c) => csvEscape(c.header)).join(',');
	const rows = apps.map((app) =>
		CSV_COLUMNS.map((c) => csvEscape(app[c.key])).join(',')
	);
	return [header, ...rows].join('\n');
}
