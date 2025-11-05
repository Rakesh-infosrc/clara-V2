import type { AppConfig } from './lib/types';

export const APP_CONFIG_DEFAULTS: AppConfig = {
  companyName: 'InfoServices',
  pageTitle: 'Clara - virtual Receptionist',
  pageDescription: 'Hello, my name is clara, the receptionist at an Info Services',

  supportsChatInput: true,
  supportsVideoInput: true,
  supportsScreenShare: true,
  isPreConnectBufferEnabled: true,

  logo: 'InfoServices-Logo.svg',
  accent: '#002cf2',
  logoDark: 'InfoServices-Logo.svg',
  accentDark: '#1fd5f9',
  startButtonText: 'Talk To Clara',

  agentName: 'clara-receptionist',
};
