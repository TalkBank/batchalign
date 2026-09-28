# Review Mode

**Status:** Current
**Last updated:** 2026-03-30 13:40 EDT

Review Mode helps you evaluate and correct alignment quality in CHAT files
produced by `batchalign align`. When align is uncertain about a timing
decision, it marks the utterance with a `%xrev` tier. Review Mode lets you
step through these flagged utterances, listen to the audio, and rate or
correct the timing — all without leaving VS Code.

## When to use it

After running `batchalign align --bullet-repair`:

- **Every utterance where align made a repair decision** gets a `%xalign`
  tier documenting what happened (e.g., "boundary averaged 155ms overlap")
- **Low-confidence utterances** also get a `%xrev: [?]` tier — these are
  the ones that need your attention

Review Mode navigates directly to the `[?]` utterances, plays their audio,
and lets you rate them with a single keystroke.

## What you're rating

Each flagged utterance has a timing bullet (e.g., `•12095_12335•`) that
should correspond to where the words are in the audio. Your job is to
listen and answer: **does this bullet point to the right place?**

| Rating | Key | When to use |
|--------|-----|-------------|
| Good | `1` | Audio matches the text at this timestamp |
| Early | `2` | Bullet plays audio before the words start |
| Late | `3` | Bullet plays audio after the words start |
| Wrong | `4` | Hearing completely different content |
| Skip | `5` | Can't tell, or don't want to rate this one |

## What the tiers mean

**`%xalign`** is machine-generated metadata. It records what the alignment
pipeline did and why. **Never edit this tier** — it's the algorithm's log.

```text
%xalign:	boundary_averaged overlap=155ms machine=12095_12335 adjacent=UEL:3
```

**`%xrev`** is your review. It starts as `[?]` (unreviewed). You change it
to your rating. You can also add notes after the rating.

```text
%xrev:	[?]           ← before review
%xrev:	[ok]          ← after review (sounds right)
%xrev:	[early] about 200ms before speech starts  ← with a note
```

## Visual indicators

Even without activating Review Mode, `%xrev` lines are color-coded in the
editor:

- **Yellow left border** — `[?]` unreviewed (needs attention)
- **Green left border** — `[ok]`, `[corrected]`, or `[stamped]` (confirmed)
- **Red left border** — `[wrong]`, `[early]`, or `[late]` (problem found)

These decorations appear on any CHAT file with `%xrev` tiers, automatically.
