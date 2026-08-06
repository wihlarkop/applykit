import { describe, expect, test } from 'bun:test';
import { NAVIGATION_ITEMS, isNavigationItemActive } from './navigation';

describe('navigation compatibility', () => {
  test('treats /generate as the Resume destination', () => {
    const resume = NAVIGATION_ITEMS.find((item) => item.id === 'resume');
    expect(resume).toBeDefined();
    expect(isNavigationItemActive('/generate', resume!)).toBe(true);
    expect(isNavigationItemActive('/resume', resume!)).toBe(true);
    expect(isNavigationItemActive('/resume/42', resume!)).toBe(true);
  });

  test('treats legacy History and Tracker paths as canonical destinations', () => {
    const documents = NAVIGATION_ITEMS.find((item) => item.id === 'documents')!;
    const applications = NAVIGATION_ITEMS.find((item) => item.id === 'applications')!;

    expect(isNavigationItemActive('/history', documents)).toBe(true);
    expect(isNavigationItemActive('/documents', documents)).toBe(true);
    expect(isNavigationItemActive('/tracker', applications)).toBe(true);
    expect(isNavigationItemActive('/applications', applications)).toBe(true);
  });

  test('does not mark Dashboard active for nested routes', () => {
    const dashboard = NAVIGATION_ITEMS.find((item) => item.id === 'dashboard')!;
    expect(isNavigationItemActive('/', dashboard)).toBe(true);
    expect(isNavigationItemActive('/resume', dashboard)).toBe(false);
  });
});
