import { createContext, useContext, useEffect, useMemo, useState, type PropsWithChildren } from "react";

import {
  DEFAULT_LOCALE,
  getSupportedLocales,
  isLocaleCode,
  LOCALE_STORAGE_KEY,
  setActiveLocale,
  type LocaleCode,
} from "./runtime";

type LocaleContextValue = {
  locale: LocaleCode;
  locales: readonly LocaleCode[];
  setLocale: (next: LocaleCode) => void;
};

const LocaleContext = createContext<LocaleContextValue | null>(null);

function readInitialLocale(): LocaleCode {
  if (typeof window === "undefined") {
    return DEFAULT_LOCALE;
  }

  const storedLocale = window.localStorage.getItem(LOCALE_STORAGE_KEY);
  return isLocaleCode(storedLocale) ? storedLocale : DEFAULT_LOCALE;
}

export function LocaleProvider({ children }: PropsWithChildren) {
  const [locale, setLocale] = useState<LocaleCode>(() => readInitialLocale());

  // Keep the lightweight text layer in sync before children render.
  setActiveLocale(locale);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    window.localStorage.setItem(LOCALE_STORAGE_KEY, locale);
  }, [locale]);

  const value = useMemo<LocaleContextValue>(
    () => ({
      locale,
      locales: getSupportedLocales(),
      setLocale,
    }),
    [locale],
  );

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale(): LocaleContextValue {
  const context = useContext(LocaleContext);

  if (!context) {
    throw new Error("useLocale must be used within LocaleProvider.");
  }

  return context;
}
