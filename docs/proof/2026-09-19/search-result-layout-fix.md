# First-search-result layout fix

The native Firefox text-input test found a real issue: the query was `SEARCH雪`
and the result said “Match found,” but xterm's selection was gone. Diagnostic
resize events showed the terminal dropping from 30 to 29 rows when the first
result appeared. The stylesheet hid an empty result line entirely; populating
that line grew the search toolbar after the addon selected its match.

The fix only changes CSS. The result line reserves `min-height: 1.25em` from the
moment search opens, and the empty-line hiding rule is removed. Terminal-page
logic, shell input, composition processing and search matching are unchanged.
This is a first-result layout fix, not a broader policy for external window
resizes while searching.

## Focused proof

`test-terminal-search-layout.mjs`: **7 passed** using actual vendored xterm,
search addon, fit addon, production markup, stylesheet and extracted production
search function in headless Chromium. Wide and narrow layouts retain terminal
height, row count and the first Unicode match selection. No-match and cleared
query messages keep that geometry too.

The negative control reinstates only the old `:empty { display:none }` rule.
Actual toolbar height then grows from 40 to 60 pixels, xterm rows fall from 33 to
31, and the real selection becomes null. No mocked terminal resize, selection
clearing, shell output or composition event creates that failure.

The existing focused search suite passed. This agent did not launch native Zen.
Parent owns the rebuilt native Gecko text-input rerun; rendered Chromium proof
alone does not establish macOS IME acceptance.

## Native follow-up and bounded edge-case review

The parent rebuilt the Firefox156 overlay and ran
`test-terminal-text-input-macos.py --label input156-v3` successfully: **5 native
checks passed**, with the OS-specific input-source/candidate UI, dead-key and
VoiceOver cases explicitly **not run**. Evidence:

- `input156-v3-results.json`: no failure; real Unicode composition commit/cancel,
  Option-b terminal bytes, composing Enter isolation and search text selection.
- `.terminal-test/input156-v3.log`: before and during `SEARCH雪` composition,
  xterm remains at **29 rows / 127 columns**. The active search composition has
  a real match selection from `(0,1)` to `(8,1)`; no new resize event appears
  when the result text is first populated.

This proves native Gecko composition integration and the real PTY path on that
rebuilt test overlay. It does not claim macOS input-method candidate UI coverage
or final distributable acceptance.

The focused rendered suite now adds a **240-pixel narrow viewport** and re-entering
the Unicode query after no-match and clear transitions. It passes **13 cases**;
all three widths retain geometry and regain a real selected match after clearing.
The old-rule negative control still produces the real resize and lost selection.

Additional focused checks rerun successfully: source search behavior; **18**
rendered reduced-motion cases; terminal polish/input-feedback lifecycle; native
polish source checks. No further production change was needed.

Boundary retained: opening/closing the entire search toolbar and actual external
window resizing legitimately change terminal dimensions. This small fix does
not promise to preserve a selected search match through every such resize or
through arbitrary application redraws. The native test intentionally waits for
search-opening layout to settle before composition; typing during that opening
transition is not separately accepted here. Current fixed English result labels
fit the tested widths; future longer translations or changed font sizing should
repeat the geometry test rather than assuming one reserved line is sufficient.

The parent then repeated the actual native journey as `input156-v4` and
`input156-v5`. Both result files also record **5 passed, 1 explicit not-run, no
failure**, and the parent reports exit 0. Together v3/v4/v5 are **three consecutive
native passes** of the same scoped Gecko/PTY journey—not three different levels
of OS input-method acceptance.
