import { i18n } from "./i18n";

const defaultLocale = i18n.defaultLanguage;

export function switchLocale(
  pathname: string,
  currentLocale: string,
  targetLocale: string,
): string {
  const segments = pathname.split("/").filter((v) => v.length > 0);

  if (currentLocale === defaultLocale) {
    segments.unshift(targetLocale);
  } else if (targetLocale === defaultLocale) {
    if (segments[0] === currentLocale) segments.shift();
  } else {
    if (segments[0] === currentLocale) segments[0] = targetLocale;
    else segments.unshift(targetLocale);
  }

  return `/${segments.join("/")}`;
}
