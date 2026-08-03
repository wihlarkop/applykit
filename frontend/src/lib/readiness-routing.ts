import type { ReadinessResponse } from './readiness-types';

const SETUP_ROUTES = ['/login', '/setup', '/settings', '/onboarding', '/profile', '/profiles', '/import'];

function isSetupRoute(pathname: string): boolean {
  return SETUP_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`),
  );
}

export function resolveReadinessDestination(
  readiness: ReadinessResponse,
  pathname: string,
): string | null {
  if (!readiness.onboarding.should_redirect || isSetupRoute(pathname)) return null;
  return '/onboarding';
}
