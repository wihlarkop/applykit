export type NavigationGroup = 'primary' | 'secondary' | 'system';

export interface NavigationItem {
  id: string;
  label: string;
  href: string;
  legacyHrefs: string[];
  group: NavigationGroup;
}

export const NAVIGATION_ITEMS: NavigationItem[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    href: '/',
    legacyHrefs: [],
    group: 'primary',
  },
  {
    id: 'prepare',
    label: 'Prepare Application',
    href: '/smart-apply',
    legacyHrefs: [],
    group: 'primary',
  },
  {
    id: 'resume',
    label: 'Resume',
    href: '/resume',
    legacyHrefs: ['/generate'],
    group: 'primary',
  },
  {
    id: 'cover-letter',
    label: 'Cover Letter',
    href: '/cover-letter',
    legacyHrefs: [],
    group: 'primary',
  },
  {
    id: 'documents',
    label: 'Documents',
    href: '/documents',
    legacyHrefs: ['/history'],
    group: 'secondary',
  },
  {
    id: 'applications',
    label: 'Applications',
    href: '/applications',
    legacyHrefs: ['/tracker'],
    group: 'secondary',
  },
];

function matchesPath(pathname: string, href: string): boolean {
  if (href === '/') return pathname === '/';
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function isNavigationItemActive(
  pathname: string,
  item: NavigationItem,
): boolean {
  return [item.href, ...item.legacyHrefs].some((href) =>
    matchesPath(pathname, href),
  );
}
