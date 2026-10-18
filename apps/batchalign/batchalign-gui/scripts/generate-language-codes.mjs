// Regenerate from the pinned pycountry wheel's databases/iso639-3.json:
// node scripts/generate-language-codes.mjs /path/to/pycountry/databases/iso639-3.json
import { readFileSync, writeFileSync } from 'node:fs';

if (!process.argv[2]) throw new Error('Provide the pinned pycountry iso639-3.json path');
const records = JSON.parse(readFileSync(process.argv[2], 'utf8'))['639-3'];
const catalog = Object.fromEntries(records
  .map(({ alpha_3, name }) => [alpha_3, name])
  .sort(([a], [b]) => a.localeCompare(b)));
writeFileSync(new URL('../src/languageCodes.json', import.meta.url), `${JSON.stringify(catalog, null, 2)}\n`);
