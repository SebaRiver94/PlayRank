export const THEME_IDS = ['neo', 'sakura', 'core'] as const;
export type ThemeId = typeof THEME_IDS[number];
export type ThemeColors = { background: string; surface: string; border: string; primary: string; accent: string; text: string; textMuted: string; onPrimary: string; danger: string; gold: string };
export const themes: Record<ThemeId, { label: string; description: string; colors: ThemeColors }> = {
  neo: { label: 'Neo', description: 'Gaming Premium', colors: { background:'#0c0c0c',surface:'#1a1a1a',border:'#2a2a2a',primary:'#00D9FF',accent:'#A78BFA',text:'#ffffff',textMuted:'#999999',onPrimary:'#000000',danger:'#FF6B6B',gold:'#FFD700' } },
  sakura: { label: 'Sakura', description: 'Anime Soft', colors: { background:'#191425',surface:'#292138',border:'#51405f',primary:'#F3A7D5',accent:'#C4B5FD',text:'#FFF6FE',textMuted:'#D2BFD9',onPrimary:'#27182D',danger:'#FF8C9C',gold:'#F6D68B' } },
  core: { label: 'Core', description: 'Premium Neutral', colors: { background:'#101619',surface:'#202B2E',border:'#3A4B50',primary:'#6CE2D1',accent:'#A1C8CE',text:'#F4F8F8',textMuted:'#B0C0C4',onPrimary:'#0C2525',danger:'#FF8A85',gold:'#EBD18B' } },
};
export function normalizeTheme(value: unknown): ThemeId { return typeof value === 'string' && (THEME_IDS as readonly string[]).includes(value) ? value as ThemeId : 'neo'; }
