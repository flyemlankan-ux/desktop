# Firefox156 fresh-build CI readiness

Changed `.github/workflows/terminal-macos-dev-build.yml` and
`scripts/terminal-tabs/check-terminal-tabs.mjs` only in this slice.

- Build display version derives from surfer.json, checked156.0.
- Receipt identifies Zen1.22.2b, pinned upstream commit and actual Rust toolchain.
- Uses156 Settings suite plus organization, entrypoint, All Tabs, ownership and
  native visual source checks before expensive compilation.
- Architecture-specific runner matches official upstream Intel/ARM choice; GNUtar
  prefix uses brew rather than assumed Intel installation directory.
- Bootstrap failures no longer silently ignored.
- Final DMG lookup requires exactly one candidate in exact target object folder;
  never chooses first matching output from unrelated nested app/object directory.
- Wiring asserts root helper staging, installer manifest, and actual native
  PinManager/SpaceManager loader/build registration paths.

Tests: YAML syntax (Ruby YAML parser), wiring/module syntax, existing terminal polish,
12 settings156 cases,3 direct package command tests,4 helper assembler tests pass.
Polish needed no156 code changes. Helper remains standalone Program with DIST_SUBDIR
empty, MacOS-files inclusion, and installer manifest inclusion.

IMPORTANT: the4 assembler tests still load Firefox155 fixtures. They prove our
existing packaging rule, NOT independent156 compatibility. Refresh fixture sources
and embedded inherited-target snippets before promoting them as156 proof.

## Fresh-build prerequisites and evidence boundary
- Complete current source/editor/security changes; obtain an immutable source commit
  only after owners release files. Final output must correspond to that commit.
- Re-run updated156 settings and strict target packaging fixtures.
- Use clean Firefox156 source download/import and incoming Rust1.95.0 configuration.
  No mixing155 compiled executables with156 app resources.
- Standard workflow then compile -> saved raw recovery (clearly NOT installer) ->
  helper staging check -> mach package + package-multi-locale -> development seal ->
  exact source/identity/no-private-data/signature inspection -> published DMG receipt.
- Any bootstrap/import/compile/package/inspection failure stops delivery. The raw
  recovery upload exists for diagnosis, not a shortcut to claiming fresh package.
- Run actual final packaged and installed native workflows after artifact download;
  local official-app overlays do not establish clean-source build acceptance.
- Ad-hoc signing remains private-development signing, NOT Apple notarization.
  No signing identity was assumed; original Zen/profile not touched.

No cloud build launched, no UI, no commits in this slice. Parent owns final build
choice and exact-module asset mapping. Recommended reasoning high; proof focused
source checks plus fresh actual packaged native regression suite.
