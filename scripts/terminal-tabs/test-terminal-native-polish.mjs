#!/usr/bin/env node
// Focused source/behavior checks only. Real Mac screenshots remain required.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";
const root = new URL("../../", import.meta.url);
const read = name => readFileSync(new URL(name, root), "utf8");
const tabs = read("src/zen/terminal/ZenTerminalTabs.mjs");
const css = read("src/zen/terminal/zen-terminal-tabs.css");
const pageCss = read("src/zen/terminal/zen-terminal-page.css");
const icon = "chrome://browser/skin/zen-icons/selectable/terminal.svg";
const method = tabs.slice(tabs.indexOf("  markTerminalTab("), tabs.indexOf("  unmarkTerminalTab("));
const icons = [];
const context = vm.createContext({
  ZEN_TERMINAL_TAB_ATTRIBUTE: "zen-terminal-tab",
  gBrowser: { setIcon(tab, value) { icons.push(value); }, _setTabLabel() {} },
});
vm.runInContext(`globalThis.mark = function ${method.trim()}`, context);
for (const chosen of [undefined, "data:image/svg+xml,user-chosen-icon"]) {
  const attrs = new Map([["label", "Work"]]);
  const tab = { zenStaticIcon: chosen, setAttribute: (name, value) => attrs.set(name, value), getAttribute: name => attrs.get(name), removeAttribute: name => attrs.delete(name), style: { removeProperty() {} } };
  context.mark(tab);
  assert.equal(icons.at(-1), chosen || icon);
  assert.equal(tab.zenStaticIcon, chosen, "Default must not become a user-picked icon");
}
assert(!css.includes("::before"), "No duplicate pseudo-element icon");
assert(!css.includes(".tab-icon-overlay"), "Do not suppress native overlays");
assert(!css.includes("list-style-image: none"), "Do not hide native icon slot");
assert(read("src/browser/themes/shared/zen-icons/jar.inc.mn").includes("skin/classic/browser/zen-icons/selectable/terminal.svg"));
assert.match(read("prefs/zen/updates.yaml"), /name: zen\.updates\.show-update-notification\s+value: false/);
assert.match(pageCss, /font-family: system-ui/);
assert.match(pageCss, /#zen-terminal-status \{[^}]*font-size: 11px/s);
assert.match(pageCss, /#zen-terminal-status-text \{[^}]*overflow-wrap: anywhere/s);
assert.match(pageCss, /#zen-terminal-reconnect:focus-visible/);
assert(!pageCss.includes("radial-gradient"));
assert.match(read("src/zen/terminal/terminal.xhtml"), /role="status" aria-live="polite"/);
console.log("Native polish checks pass: ordinary icon slot, custom icon preserved, no overlay suppression, packaged icon, honest update default, compact accessible status.");
