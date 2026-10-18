// ISO 639-3 names from pycountry 26.2.16, the pinned CLI dependency.
// languageCodes.json contains alpha_3/name from its databases/iso639-3.json.
// Keep this catalog in sync when upgrading pycountry (python/requirements.lock.txt).
import codes from "./languageCodes.json";

const names: Record<string, string> = codes;
export function languageCode(raw: string): string {
  const code = raw.trim().toLowerCase();
  return Object.prototype.hasOwnProperty.call(names, code) ? code : "";
}

const COMMON = ["eng", "zho", "yue", "spa", "fra", "deu", "jpn", "kor", "por", "ara"];
const SEARCH_NAMES: Record<string, string> = { zho: "mandarin", yue: "cantonese" };
export function languageSuggestions(raw: string): Array<[string, string]> {
  const query = raw.trim().toLowerCase();
  if (!query) return COMMON.map(code => [code, names[code]]);
  const exact = languageCode(query);
  if (exact) return [[exact, names[exact]]];
  return Object.entries(names)
    .filter(([code, name]) => code.startsWith(query) || name.toLowerCase().includes(query)
      || SEARCH_NAMES[code]?.includes(query))
    .sort(([a, an], [b, bn]) => Number(b === query) - Number(a === query)
      || Number(b.startsWith(query)) - Number(a.startsWith(query))
      || Number(SEARCH_NAMES[b] === query) - Number(SEARCH_NAMES[a] === query)
      || an.localeCompare(bn))
    .slice(0, 12);
}
