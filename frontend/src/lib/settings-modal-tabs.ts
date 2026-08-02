export type ProviderSettingsTab = 'model' | 'credentials' | 'routing';

export function defaultSettingsTab(input: {
  isExistingProvider: boolean;
  requiresCredential: boolean;
}): ProviderSettingsTab {
  return input.isExistingProvider && input.requiresCredential ? 'credentials' : 'model';
}

export function footerActionForTab(tab: ProviderSettingsTab): string {
  if (tab === 'credentials') return 'Done';
  if (tab === 'routing') return 'Save routing settings';
  return 'Save model changes';
}
