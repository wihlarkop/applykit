import { sanitizeReturnTo } from './auth-utils';

export type LoginSuccessDestination =
    | { kind: 'navigate'; path: string }
    | { kind: 'reauth-complete' };

export function loginSuccessDestination(url: URL): LoginSuccessDestination {
    if (url.searchParams.get('reauth') === '1') {
        return { kind: 'reauth-complete' };
    }
    return {
        kind: 'navigate',
        path: sanitizeReturnTo(url.searchParams.get('returnTo')),
    };
}
