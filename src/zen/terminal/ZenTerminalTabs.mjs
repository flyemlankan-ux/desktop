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
  #terminalUrl(options = {}) {
    const params = new URLSearchParams();
    if (options.terminalContainerId) {
      params.set("container", options.terminalContainerId);
    }
    if (options.terminalContainerName) {
      params.set("name", options.terminalContainerName);
    }
    const query = params.toString();
    return query ? `${ZEN_TERMINAL_TAB_URL}?${query}` : ZEN_TERMINAL_TAB_URL;
  }

  isTerminalTab(tab) {
    return Boolean(tab?.hasAttribute?.(ZEN_TERMINAL_TAB_ATTRIBUTE));
  }

  markTerminalTab(tab, options = {}) {
    if (!tab) {
      return;
    }
    tab.setAttribute(ZEN_TERMINAL_TAB_ATTRIBUTE, "true");
    tab.setAttribute("zen-show-sublabel", "true");
    if (options.terminalContainerId) {
      tab.setAttribute(
        "zen-terminal-container-id",
        options.terminalContainerId,
      );
    }
    const label =
      options.terminalContainerName || tab.getAttribute("label") || "Terminal";
    tab.setAttribute("label", label);
  }

  unmarkTerminalTab(tab) {
    if (!tab) {
      return;
    }
    tab.removeAttribute(ZEN_TERMINAL_TAB_ATTRIBUTE);
  }

  openTerminalTab(options = {}) {
    const tab = gBrowser.addTab(this.#terminalUrl(options), {
      triggeringPrincipal: Services.scriptSecurityManager.getSystemPrincipal(),
    });
    this.markTerminalTab(tab, options);
    gBrowser.selectedTab = tab;
    return tab;
  }
}

window.gZenTerminalTabs = new ZenTerminalTabs();
