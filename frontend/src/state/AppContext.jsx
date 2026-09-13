import React, {
  createContext, useCallback, useContext, useEffect, useMemo, useState,
} from 'react';
import { api, getToken, setToken } from '../services/api';

const AppContext = createContext(null);

const THEME_KEY = 'ecoforge.theme';
const FACTORY_KEY = 'ecoforge.factory';

function readLocal(key, fallback = '') {
  try { return localStorage.getItem(key) || fallback; } catch { return fallback; }
}
function writeLocal(key, value) {
  try {
    if (value) localStorage.setItem(key, value);
    else localStorage.removeItem(key);
  } catch { /* private mode */ }
}

export function AppProvider({ children }) {
  const [theme, setThemeState] = useState(() => readLocal(THEME_KEY, 'light'));
  const [authed, setAuthed] = useState(() => Boolean(getToken()));
  const [factories, setFactories] = useState([]);
  const [factoryId, setFactoryIdState] = useState(() => readLocal(FACTORY_KEY));
  const [loadingFactories, setLoadingFactories] = useState(false);
  const [factoriesError, setFactoriesError] = useState(null);
  const [view, setView] = useState('operational');
  const [toast, setToast] = useState(null);

  /* ---------------------------------------------------------------- theme */
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    writeLocal(THEME_KEY, theme);
  }, [theme]);

  const toggleTheme = useCallback(
    () => setThemeState((t) => (t === 'dark' ? 'light' : 'dark')), [],
  );

  /* ------------------------------------------------------------- factories */
  const refreshFactories = useCallback(async () => {
    if (!getToken()) return;
    setLoadingFactories(true);
    setFactoriesError(null);
    try {
      const list = await api.listFactories();
      setFactories(list || []);
      setFactoryIdState((current) => {
        if (current && list?.some((f) => f.id === current)) return current;
        const demo = list?.find((f) => f.demo);
        const next = demo?.id || list?.[0]?.id || '';
        writeLocal(FACTORY_KEY, next);
        return next;
      });
    } catch (err) {
      setFactoriesError(err);
    } finally {
      setLoadingFactories(false);
    }
  }, []);

  useEffect(() => { if (authed) refreshFactories(); }, [authed, refreshFactories]);

  const setFactoryId = useCallback((id) => {
    setFactoryIdState(id);
    writeLocal(FACTORY_KEY, id);
  }, []);

  /* ------------------------------------------------------------------ auth */
  const signIn = useCallback(async (payload) => {
    const res = await api.login(payload);
    setToken(res.token);
    setAuthed(true);
    return res;
  }, []);

  const signUp = useCallback(async (payload) => {
    const res = await api.register(payload);
    setToken(res.token);
    setAuthed(true);
    return res;
  }, []);

  const signOut = useCallback(() => {
    setToken('');
    setAuthed(false);
    setFactories([]);
    setFactoryIdState('');
    writeLocal(FACTORY_KEY, '');
  }, []);

  /* ---------------------------------------------------------------- toast */
  const notify = useCallback((message, tone = 'info') => {
    setToast({ message, tone, id: Date.now() });
    window.setTimeout(() => setToast(null), 4500);
  }, []);

  const factory = useMemo(
    () => factories.find((f) => f.id === factoryId) || null,
    [factories, factoryId],
  );

  const value = useMemo(() => ({
    theme, toggleTheme,
    authed, signIn, signUp, signOut,
    factories, factory, factoryId, setFactoryId, refreshFactories,
    loadingFactories, factoriesError,
    view, setView,
    toast, notify,
  }), [theme, toggleTheme, authed, signIn, signUp, signOut, factories, factory,
       factoryId, setFactoryId, refreshFactories, loadingFactories, factoriesError,
       view, toast, notify]);

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used inside <AppProvider>');
  return ctx;
}
