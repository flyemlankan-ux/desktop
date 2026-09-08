# Recovered app startup: independent source audit

Audit date: 2026-09-08. Read-only diagnosis; no browser launched by this reviewer.

## What failed

The recovered source build is a loose development app, not the output of Firefox's
packaging step. The browser crashed while preparing a content process. The local
crash report `zen-terminal-2026-09-08-110037.ips` identifies
`ContentParent::BeginSubprocessLaunch +3564`. Register x0 contains `0x80520012`
(file not found); x9 contains2395. No personal profile data was inspected.

Pinned Firefox155.0.1 `ContentParent.cpp` line2395 is
`MOZ_CRASH("Failed to get path to repo dir")`. The recovered main app's developer
metadata points to the cloud runner's unavailable source directory. This source
branch and the crash register strongly support the missing development-directory
diagnosis. It is not a claim that a corrected app has already passed native tests.

## Exact source chain

1. `xpcom/build/Omnijar.h` lines171–178: `IsPackagedBuild()` returns
   `Omnijar::HasOmnijar(mozilla::Omnijar::GRE)`. It tests for the GRE resource
   archive, **not** developer keys in Info.plist and not the browser-only archive.
2. `dom/ipc/ContentParent.cpp` lines2390–2410: an unpackaged build reads its
   development source and object directories for sandbox read access. Failure
   reading either directory deliberately crashes. Line2395 is the first failure.
3. `xpcom/base/nsMacUtilsImpl.cpp` lines319–350: directory lookup reads the
   main bundle's `MozillaDeveloperRepoPath`, creates an nsIFile, normalizes the
   path, and checks that it is a directory. A nonexistent runner path fails.
4. `toolkit/mozapps/installer/packager.py` lines38–47: the normal packager removes
   **both** `MozillaDeveloperObjPath` and `MozillaDeveloperRepoPath` from every
   file named Info.plist, including nested app bundles.

Removing those keys alone does **not** repair a loose app. Without a real GRE
omni.ja it still follows the development branch, then fails reading the missing
key. Disabling sandbox checks, adding dummy archives, or inventing development
paths is not the recommended fix.

## Bounded recovery method

Use Firefox's own pinned Python packaging classes on a fresh output directory:
`FileFinder`, `FileCopier`, `SimplePackager`, and `OmniJarFormatter`.
`SimplePackager` discovers independent GRE/browser manifest roots and rewrites
registrations; `OmniJarFormatter` uses Firefox's resource classification to build
real archives. Apply the original Info.plist normalization to every plist.

Use `find_executables=False` to avoid stripping or rewriting the already compiled
native binaries. This skips optional binary size processing, not resource packing
or sandboxing. Keep input recovery unchanged. Verify both actual resource archives,
source asset equality, executable hashes/modes and absence of developer metadata.
Sign the completed app afterward. Then test normal native browser startup and all
terminal behavior. These are required proofs, not results of this source audit.

Imports for the exact classes were confirmed possible with the pinned mozpack
files plus `mozbuild/{__init__,util,preprocessor,makeutil,dirutils}.py`; no compiler
or browser rebuild is needed for that operation. Parent owns the fetched-file
receipt at `.terminal-test/mozpack155/receipt.json`. The packaging worker owns
implementation and actual conversion proof.

## Source receipt

Repository: `mozilla-firefox/firefox`; ref: `FIREFOX_155_0_1_RELEASE`.
Retrieved read-only through GitHub's contents endpoint. Git blob SHA1 values:

| Source | Git blob SHA1 |
| --- | --- |
| dom/ipc/ContentParent.cpp | 21a9c93a1325d8934ad651db097238538f0f0548 |
| xpcom/build/Omnijar.h | 61a38b145c7d837ab8a54262a87174d77f21074f |
| xpcom/base/nsMacUtilsImpl.cpp | c4af87dc4e49aaa5d1c39f66660f3286b62c69fb |
| toolkit/mozapps/installer/packager.py | 77024f044b9dab7f1b5e67f6c177c67577c8078a |
| toolkit/mozapps/installer/packager.mk | 2eec02dbd356f0477cb8c828e9c12352a8ecd3f1 |
| python/mozbuild/mozpack/packager/__init__.py | 147e471f7bd5ec7917e658f6df49799c64f0c112 |
| python/mozbuild/mozpack/packager/formats.py | b8c5ab0257d76f6a66cfb5fc50b9633bd9fc99cd |

Local source inspection copies are under `.terminal-test/startup155/` and contain
public upstream code only. No crash-report contents or private profile files are
copied into this document.

## Scope and next proof

This corrects the saved compiled app's packaging. It changes no browser feature,
profile migration rule, or security setting. Recommended next reasoning: high;
proof: independently inspect resource conversion and signatures, then run actual
Mac startup/terminal acceptance with synthetic profiles only.
