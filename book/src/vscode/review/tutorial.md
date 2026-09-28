# Tutorial: Reviewing Aligned Files

**Status:** Current
**Last updated:** 2026-03-30 13:40 EDT

This tutorial walks through reviewing a CHAT file that was aligned by
`batchalign align --bullet-repair`. It takes about 5 minutes to review
a typical file.

## Prerequisites

- VS Code Insiders with the TalkBank CHAT extension installed
- A CHAT file aligned with `--bullet-repair --review-level=low-confidence`
- The corresponding audio file accessible to the extension

## Step 1: Open the aligned file

Open the `.cha` file in VS Code. You should see:

- Yellow left borders on lines with `%xrev: [?]` — these need review
- The `%xalign` tiers above them explaining what happened

If you don't see any yellow lines, the file had no low-confidence decisions.
Nothing to review!

## Step 2: Start Review Mode

Open the Command Palette (`Cmd+Shift+P` on macOS, `Ctrl+Shift+P` elsewhere)
and type **"Start Review Mode"**.

The extension will:
1. Parse all `%xrev` tiers in the file
2. Show a status bar item: **"Review: 0/7"** (0 of 7 rated)
3. Jump to the first unreviewed utterance
4. If the waveform panel is open, highlight the bullet segment

## Step 3: Listen and rate

For each flagged utterance:

1. **Read the `%xalign` tier** — it tells you what happened. For example,
   `boundary_averaged overlap=155ms` means two adjacent utterances overlapped
   and align split the difference.

2. **Play the audio** — click the bullet (`•12095_12335•`) or use
   `Cmd+Shift+Enter` to play from the current line.

3. **Listen** — does the audio match the text? Does speech start at the
   bullet's timestamp?

4. **Rate with a single key:**
   - `1` = Good (timing is correct)
   - `2` = Early (audio starts before the speech)
   - `3` = Late (audio starts after the speech)
   - `4` = Wrong (completely wrong location)
   - `5` = Skip (can't tell)

5. The extension **auto-advances** to the next unreviewed utterance.

## Step 4: Add notes (optional)

If you want to explain your rating, edit the `%xrev` line directly.
Add text after the rating marker:

```text
%xrev:	[early] starts about 200ms before the actual speech
```

Or:

```text
%xrev:	[wrong] this is a different speaker's audio entirely
```

Notes are especially valuable when they describe **patterns** rather than
individual utterances:

```text
%xrev:	[early] all backchannels from INV seem to be early by ~200ms
```

## Step 5: Save and done

When the status bar shows all items rated (e.g., "Review: 7/7"), save the
file with `Cmd+S`. The ratings are stored in the `%xrev` tiers — they're
part of the CHAT file now.

If you use `tb-deploy` to push changes, the ratings travel with the file.

## Step 6: Stop Review Mode

Open the Command Palette and type **"Stop Review Mode"**, or just close
the file. The status bar indicator disappears.

## Keyboard shortcut reference

These shortcuts are only active during Review Mode:

| Shortcut | Action |
|----------|--------|
| `Alt+]` | Next unreviewed utterance |
| `Alt+[` | Previous unreviewed utterance |
| `1` | Rate Good |
| `2` | Rate Early |
| `3` | Rate Late |
| `4` | Rate Wrong |
| `5` | Skip |

The number keys only work when the editor is **not** focused for text input
(i.e., when you're in the command area or the cursor is on a read-only line).
If you need to type in the editor, the number keys behave normally.

## Tips

- **You don't need to review every file.** Even 5-10 files gives us useful
  data for tuning the algorithm.

- **Focus on the `[?]` markers.** Utterances without `%xrev` were
  high-confidence — the algorithm is pretty sure they're right.

- **Pattern notes are gold.** "All short backchannels are early" is more
  useful than rating 50 individual backchannels.

- **If unsure, skip.** Press `5` to move on. A skipped utterance is better
  than a wrong rating.

- **Review Mode + Walker Mode** work well together. Start Review Mode, then
  use `Alt+Down`/`Alt+Up` (Walker) to step through utterances with automatic
  playback. When you land on a flagged utterance, rate it with `1`-`5`.

## What happens with your reviews

The experiment maintainer collects the ratings using a harvesting
script and uses them to:

- **Evaluate `--bullet-repair`** — is it better than CLAN FIXBULLETS?
- **Tune thresholds** — how much overlap should be averaged? When should
  timing be stripped?
- **Identify systematic problems** — if all backchannels are wrong, the
  algorithm needs a backchannel-specific fix
- **Build ground truth** — corrected bullets become training data for
  improving the alignment algorithm

Your free-form notes are especially valuable — they capture observations
that ratings alone can't express.
