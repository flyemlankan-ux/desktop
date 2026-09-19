# Pinned Firefox 156 restoration and tab-management source

Pristine `SessionStore.sys.mjs` and `Tabbrowser.sys.mjs` from the official Mozilla
Firefox repository, `FIREFOX_156_0_RELEASE`. `receipt.json` records Git blob IDs
and SHA-256 hashes. Decoded contents were checked against the Git blob IDs.

Complete production Zen patches must apply with zero fuzz. The disposable app
builder also applies original Zen 1.22.2b patches and requires exact equality
with the official application's registered engine resources before substituting
our versions. Both resources live in the engine `omni.ja`, not the browser archive.
This fixture is source evidence, not native UI acceptance.
