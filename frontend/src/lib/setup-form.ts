import { passwordFormEligible } from './auth-utils';

export function setupFormEligible(
    setupToken: string,
    password: string,
    confirmation: string,
): boolean {
    return passwordFormEligible(password, confirmation, setupToken);
}
