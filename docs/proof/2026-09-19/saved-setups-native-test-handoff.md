# Native saved-setup journey test handoff

New file: `scripts/terminal-tabs/test-terminal-saved-setups-macos.py`.
Run only by the parent, which owns UI execution:

```
/Users/ar/zen-terminal-research/desktop/.terminal-test/venv/bin/python3 -B \
  scripts/terminal-tabs/test-terminal-saved-setups-macos.py \
  --app '/path/to/disposable/Zen Terminal.app' --label saved-setups
```

Syntax and `--help` checked. **Not launched; no native passing claims.**

## Designed checks

- New synthetic HOME/profile/app-data; launched PID and actual profile asserted. Inherited profile override variables removed.
- Actual native Settings Add and Edit controls, name/kind and starting-folder input.
- Missing folder blocks save before identity creation.
- Literal Unicode, quotes, shell punctuation and trailing-space folder survives Save.
- Native form has no horizontal overflow; screenshot saved for inspection (not automatic visual approval).
- Real tmux shell and configured startup command both begin in chosen folder.
- Opening the same saved setup twice produces distinct live shells, each startup once.
- Editing then Cancel preserves prior folder; editing then Save affects a newly opened shell, not existing shell/PID/cwd.
- Reopened native editor shows saved folder.
- Cleanup stops only the app PID and tmux socket derived from the newly created disposable profile. Output explicitly labels synthetic data and `native_picker_tested: false`.

## Honest pending checks

The macOS file-picker sheet itself is **not tested by this script**. It needs real OS-sheet acceptance/cancellation interaction. The existing synthetic Settings tests cover callback success/cancel/failure, but cannot replace that proof. Browser restart persistence and complete setup deletion remain covered only by other existing tests or still pending expanded native journeys.

## Source-only usability review

- Positive: native form retains one Save/Cancel flow; folder label is connected to input; clear home/default and new-session-only wording; browse button and text entry both present; long values can scroll inside the input rather than the whole form.
- Pending visual issue: folder row adds three prose paragraphs plus a heading to an already tall dialog. Inspect short-window height and scrolling, not just width. Existing max-height belongs only to command list, not the full terminal fieldset.
- Pending localization: the custom terminal strings remain English; do not claim multilingual completion.
- Pending keyboard issue: step reordering rebuilds rows and may lose focused control; next keyboard/a11y review should test focus after move/remove, not just tab order.
- Pending error usability: one shared alert below startup rows reports folder errors. When the list is long, confirm users can see it and get focus guidance; source alone does not establish this.
- UI styling still uses inline sizing consistent with the previous editor implementation. This slice does not establish complete native aesthetic parity.

No existing test or production file changed in this follow-up. No UI launched or personal data touched. Recommended handoff: high reasoning, focused native proof plus inspected screenshot; not broad unrelated regressions.
