/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * Zen Terminal Tabs
 *
 * The rule for this feature:
 * - Zen remains Zen: same shell, same workspaces, same folders, same menus.
 * - Only the selected tab's content type changes from Firefox page to terminal session.
 */

export const ZEN_TERMINAL_TAB_ATTRIBUTE = "zen-terminal-tab";
export const ZEN_TERMINAL_TAB_URL =
  "chrome://browser/content/zen-terminal/terminal.xhtml";

export class ZenTerminalTabs {
  isTerminalTab(tab) {
    return Boolean(tab?.hasAttribute?.(ZEN_TERMINAL_TAB_ATTRIBUTE));
  }

  markTerminalTab(tab) {
    if (!tab) {
      return;
    }
    tab.setAttribute(ZEN_TERMINAL_TAB_ATTRIBUTE, "true");
    tab.setAttribute("zen-show-sublabel", "true");
    tab.setAttribute("label", tab.getAttribute("label") || "Terminal");
  }

  unmarkTerminalTab(tab) {
    if (!tab) {
      return;
    }
    tab.removeAttribute(ZEN_TERMINAL_TAB_ATTRIBUTE);
  }

  openTerminalTab() {
    const tab = gBrowser.addTab(ZEN_TERMINAL_TAB_URL, {
      triggeringPrincipal: Services.scriptSecurityManager.getSystemPrincipal(),
    });
    this.markTerminalTab(tab);
    gBrowser.selectedTab = tab;
    return tab;
  }
}

export const gZenTerminalTabs = new ZenTerminalTabs();
