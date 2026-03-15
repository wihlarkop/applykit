import { redirect } from '@sveltejs/kit';
import { getOnboardingStatus, getProfile } from '$lib/api';

export const ssr = false;

export const load = async ({ url }) => {
  let isOnboarded = true; // Default to true if check fails to not hard-block
  let profile = null;

  try {
    const status = await getOnboardingStatus();
    isOnboarded = status.is_onboarded;
    
    if (isOnboarded) {
      try {
        const profileRes = await getProfile();
        profile = profileRes.profile;
      } catch (e) {
        console.warn("Could not fetch profile", e);
      }
    }

    // Always allow access to onboarding
    if (url.pathname.startsWith('/onboarding')) {
      return { isOnboarded, profile };
    }

    if (!isOnboarded) {
      // Allow manual profile setup but nothing else
      if (url.pathname.startsWith('/profile')) {
        return { isOnboarded, profile };
      }
      throw redirect(307, '/onboarding');
    }
  } catch (err: any) {
    // Re-throw SvelteKit redirects
    if (err && err.status === 307) {
      throw err;
    }
    
    // If the API hasn't been implemented yet (404), or backend is down, log it but don't hard block.
    console.warn("Could not check onboarding status. Allowing navigation.", err);
  }

  return { isOnboarded, profile };
};
