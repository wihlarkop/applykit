import type { ApplicationEntry } from './types';

export type ApplicationSortColumn =
	| 'company_name'
	| 'role_title'
	| 'status'
	| 'salary'
	| 'location'
	| 'match_score'
	| 'applied_date';

export type SortDirection = 'asc' | 'desc';

export function compareApplications(
	a: ApplicationEntry,
	b: ApplicationEntry,
	column: ApplicationSortColumn,
	direction: SortDirection
): number {
	const av = a[column];
	const bv = b[column];
	const aNull = av === null || av === undefined;
	const bNull = bv === null || bv === undefined;
	// Nulls always sort last, regardless of direction.
	if (aNull || bNull) return aNull && bNull ? 0 : aNull ? 1 : -1;

	const result =
		typeof av === 'number' && typeof bv === 'number' ? av - bv : String(av).localeCompare(String(bv));
	return direction === 'asc' ? result : -result;
}
