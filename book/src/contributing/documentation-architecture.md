# Write and maintain documentation

Use [Diátaxis](https://diataxis.fr/) throughout this book. Choose one reader need
for each page before writing it:

| Form | Reader need | What belongs on the page |
|---|---|---|
| Tutorial | Learn through a successful first experience | A guided task, prerequisites, concrete steps, visible checkpoints |
| How-to guide | Complete a task the reader already wants to do | Goal-focused steps, relevant choices, verification |
| Reference | Look up a fact or contract | Accurate options, defaults, types, formats, limits, source ownership |
| Explanation | Understand a mechanism or decision | Context, relationships, reasoning, tradeoffs |

## Update a page

1. State its reader and purpose. For a first-time clinician, explain where to
   enter a command and what success looks like. Keep architecture and tuning
   details in linked explanations.
2. Check every command against its current entrypoint, every default against
   implementation, and every source path against the checkout. Distinguish model
   availability from measured quality. Do not infer current behavior from an old
   design proposal or a comment copied from a previous runtime.
3. Keep one canonical treatment of a topic. Link to it from other forms instead
   of repeating tables or architectures. Split a mixed page when its tutorial,
   reference, and explanation serve different needs.
4. Use `SUMMARY.md` to place it in the appropriate Diátaxis section. File paths
   may remain stable for existing links; the directory name does not determine
   the documentation form.
5. When retiring obsolete instructions, keep a short pointer at an established
   URL if it is linked elsewhere. Link historical studies to a fixed repository
   revision and identify their date/version scope. Do not label them current.
6. Run `just docs build` and inspect the rendered page. It includes the configured
   link checker. Verify changed command examples through `just batchalign cli`
   when they describe Batchalign integration behavior.

Keep tutorials focused on completing their exercise; keep how-to guides free of
architecture tours; keep reference factual; keep explanations separate from
copy-and-paste operational instructions. A landing page routes readers by need
instead of repeating the repository README.

The [Batchalign documentation audit](../batchalign/reference/documentation-audit.md)
records the architecture cleanup and replacement pages.
