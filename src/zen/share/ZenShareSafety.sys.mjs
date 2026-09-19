// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at http://mozilla.org/MPL/2.0/.

function invalidShare() {
  const error = new Error("Shared tabs must contain absolute HTTP or HTTPS addresses only.");
  error.code = "invalid-document";
  return error;
}

export function isSafeShareWebURL(value) {
  if (typeof value !== "string" || !/^https?:\/\//i.test(value) ||
      /[\x00-\x20\x7f\\]/u.test(value)) return false;
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) && Boolean(url.hostname);
  } catch (_) {
    return false;
  }
}

export function assertSafeShareWebURL(value) {
  if (!isSafeShareWebURL(value)) throw invalidShare();
}

/** Validate the whole tree before any import creates a workspace or tab.
 * Returns the number of web tabs, so an empty export cannot create a share.
 * Structural details still go through the upstream JSON schema validator.
 */
export function assertSafeShareDocument(doc) {
  const pending = [doc?.shared];
  const seen = new Set();
  let tabs = 0;
  while (pending.length) {
    const item = pending.pop();
    if (!item || typeof item !== "object" || seen.has(item)) throw invalidShare();
    seen.add(item);
    if (item.type === "tab") {
      assertSafeShareWebURL(item.url);
      tabs++;
    } else {
      const children = item.type === "splitView" ? item.tabs
        : ["space", "folder"].includes(item.type) ? item.items : null;
      if (!Array.isArray(children)) throw invalidShare();
      for (const child of children) pending.push(child);
    }
  }
  return tabs;
}
