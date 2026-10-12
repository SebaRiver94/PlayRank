import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { AppState } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { normalizeTheme, ThemeId, themes } from './themes';
const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL;
type ThemeContextValue = { themeId: ThemeId; theme: typeof themes.neo; setTheme: (id: ThemeId) => Promise<void>; busy: boolean };
const ThemeContext = createContext<ThemeContextValue | null>(null);
const cacheKey = (id: string) => `playrank.theme.${id}`;
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const { user, token, refreshUser, updateUser } = useAuth();
  const [themeId, setThemeId] = useState<ThemeId>('neo');
  const [busy, setBusy] = useState(false);
  const account = user?.id;
  const identity = useRef(account);
  identity.current = account;
  useEffect(() => {
    let active = true;
    setThemeId(normalizeTheme(user?.theme));
    if (!account) return () => { active = false; };
    AsyncStorage.getItem(cacheKey(account)).then(v => {
      if (active && identity.current === account && v && !user?.theme) setThemeId(normalizeTheme(v));
    }).catch(() => {});
    return () => { active = false; };
  }, [account, user?.theme]);
  const sync = useCallback(async () => {
    if (!account || !token || busy) return;
    try { await refreshUser(); } catch { /* offline: retain last confirmed preference */ }
  }, [account, token, busy, refreshUser]);
  useEffect(() => {
    if (!account) return;
    void sync();
    const sub = AppState.addEventListener('change', state => { if (state === 'active') void sync(); });
    return () => sub.remove();
  }, [account, sync]);
  const setTheme = useCallback(async (id: ThemeId) => {
    if (busy) return;
    if (!account || !token) { setThemeId(id); return; }
    const owner = account;
    const previous = themeId;
    setBusy(true);
    setThemeId(id);
    try {
      const response = await axios.put(`${API_URL}/api/users/profile`, { theme: id, theme_base_version: user?.theme_version ?? 0 });
      if (identity.current !== owner) return;
      const updated = response.data;
      updateUser({ theme: normalizeTheme(updated.theme), theme_version: updated.theme_version });
      await AsyncStorage.setItem(cacheKey(owner), normalizeTheme(updated.theme));
    } catch (error: any) {
      if (identity.current === owner) {
        const detail = error?.response?.data?.detail;
        if (error?.response?.status === 409 && detail?.code === 'theme_conflict') {
          updateUser({ theme: normalizeTheme(detail.theme), theme_version: detail.theme_version });
          setThemeId(normalizeTheme(detail.theme));
        } else setThemeId(previous);
      }
      throw error;
    } finally { setBusy(false); }
  }, [account, token, themeId, user?.theme_version, busy, updateUser]);
  return <ThemeContext.Provider value={{ themeId, theme: themes[themeId], setTheme, busy }}>{children}</ThemeContext.Provider>;
}
export function useTheme() { const ctx = useContext(ThemeContext); if (!ctx) throw new Error('useTheme requires ThemeProvider'); return ctx; }
