import { passwordFormEligible } from './auth-utils';

export function changePasswordEligible(
    currentPassword: string,
    newPassword: string,
    confirmation: string,
): boolean {
    return currentPassword.trim().length > 0
        && passwordFormEligible(newPassword, confirmation);
}

export function otherSessionsLabel(count: number): string {
    if (count <= 0) return 'No other active sessions';
    if (count === 1) return '1 other active session';
    return `${count} other active sessions`;
}
