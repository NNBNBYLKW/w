import { en } from "../../locales/en";
import { zhCN } from "../../locales/zh-CN";
import type { NestedLeafKey } from "./types";

type TextDictionary = typeof en;
export type TextKey = NestedLeafKey<TextDictionary>;
export type TextParams = Record<string, string | number | boolean | null | undefined>;
export type LocaleCode = "en" | "zh-CN";

export const DEFAULT_LOCALE: LocaleCode = "en";
export const LOCALE_STORAGE_KEY = "WORKBENCH_LOCALE";

const dictionaries = {
  en,
  "zh-CN": zhCN,
} as const satisfies Record<LocaleCode, TextDictionary>;

let activeLocale: LocaleCode = DEFAULT_LOCALE;
let activeDictionary: TextDictionary = dictionaries[DEFAULT_LOCALE];

export function isLocaleCode(value: string | null | undefined): value is LocaleCode {
  return value === "en" || value === "zh-CN";
}

export function getSupportedLocales(): readonly LocaleCode[] {
  return ["en", "zh-CN"] as const;
}

export function getActiveLocale(): LocaleCode {
  return activeLocale;
}

export function setActiveLocale(locale: LocaleCode): void {
  activeLocale = locale;
  activeDictionary = dictionaries[locale];
}

function getTextByKey(key: string): string | undefined {
  const segments = key.split(".");
  let current: unknown = activeDictionary;

  for (const segment of segments) {
    if (typeof current !== "object" || current === null || !(segment in current)) {
      return undefined;
    }
    current = (current as Record<string, unknown>)[segment];
  }

  return typeof current === "string" ? current : undefined;
}

function interpolateText(template: string, params?: TextParams): string {
  if (!params) {
    return template;
  }

  return template.replace(/\{(\w+)\}/g, (_match, token: string) => {
    const value = params[token];
    return value === undefined || value === null ? "" : String(value);
  });
}

export function t(key: TextKey, params?: TextParams): string {
  const template = getTextByKey(key);
  return interpolateText(template ?? key, params);
}
