/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * Opens real Firefox containers marked as terminal containers inside ordinary
 * Zen tabs. Firefox still owns the one shared container list and its Manage
 * entry; this class only changes what happens when a terminal row is chosen.
 */

import {
  getTerminalContainerRecipe,
  isTerminalContainerId,
} from "chrome://browser/content/zen-terminal/ZenTerminalContainerStore.mjs";
import {
  destroyTerminalSession,
  normalizeTerminalSessionId,
  retryPendingTerminalSessionDeletes,
} from "chrome://browser/content/zen-terminal/ZenTerminalSessionManager.mjs";

const { ContextualIdentityService } = ChromeUtils.importESModule(
  "resource://gre/modules/ContextualIdentityService.sys.mjs",
);
const { BrowserWindowTracker } = ChromeUtils.importESModule(
  "resource:///modules/BrowserWindowTracker.sys.mjs",
);
const { RunState } = ChromeUtils.importESModule(
  "resource:///modules/sessionstore/RunState.sys.mjs",
);

export const ZEN_TERMINAL_TAB_ATTRIBUTE = "zen-terminal-tab";
export const ZEN_TERMINAL_TAB_URL =
  "chrome://browser/content/zen-terminal/terminal.xhtml";

function terminalSessionIdForTab(tab) {
  let sessionId = normalizeTerminalSessionId(
    tab?.getAttribute?.("zen-terminal-session-id"),
  );
  if (sessionId) {
    return sessionId;
  }

  try {
    sessionId = normalizeTerminalSessionId(
      SessionStore.getCustomTabValue(tab, "zenTerminalSessionId"),
    );
  } catch (_) {
    // Older restored tabs may only have the id in their URL.
  }
  if (sessionId) {
    return sessionId;
  }

  const spec = tab?.linkedBrowser?.currentURI?.spec || "";
  if (!spec.startsWith(ZEN_TERMINAL_TAB_URL)) {
    return "";
  }
  try {
    return normalizeTerminalSessionId(
      new URL(spec).searchParams.get("session"),
    );
  } catch (_) {
    return "";
  }
}

export class ZenTerminalTabs {
  constructor() {
    this.#patchFirefoxContainerMenuBuilder();
    this.#installTerminalSessionCloseHandler();
    this.#markRestoredTerminalTabsSoon();
    void retryPendingTerminalSessionDeletes();
  }

  /**
   * Populates Zen's one container menu with Firefox's real Web and Terminal
   * containers. The normal browser-tab row already exists beside this menu, so
   * Firefox's extra "No Container" row is deliberately omitted.
   */
  populateUnifiedContainerMenu(event) {
    const result = window.createUserContextMenu(event, {
      isContextMenu: true,
      showDefaultTab: false,
    });
    this.#routeNativeTerminalContainerRows(event.target);
    window.setTimeout(
      () => this.#routeNativeTerminalContainerRows(event.target),
      0,
    );
    return result;
  }

  /**
   * Firefox also opens a container menu from a long press on its New Tab
   * button. Keep that native doorway, but route terminal rows through the same
   * terminal-tab opener. No extra rows are injected.
   */
  #patchFirefoxContainerMenuBuilder() {
    const install = () => {
      if (typeof window.CreateContainerTabMenu !== "function") {
        window.setTimeout(install, 50);
        return;
      }
      if (window.CreateContainerTabMenu.__zenTerminalPatched) {
        return;
      }

      const originalCreateContainerTabMenu = window.CreateContainerTabMenu;
      const patchedCreateContainerTabMenu = (event) => {
        const result = originalCreateContainerTabMenu.call(window, event);
        this.#routeNativeTerminalContainerRows(event.target);
        window.setTimeout(
          () => this.#routeNativeTerminalContainerRows(event.target),
          0,
        );
        return result;
      };
      patchedCreateContainerTabMenu.__zenTerminalPatched = true;
      window.CreateContainerTabMenu = patchedCreateContainerTabMenu;
    };

    install();
  }

  #routeNativeTerminalContainerRows(popup) {
    for (const item of popup?.querySelectorAll?.("[data-usercontextid]") ||
      []) {
      const userContextId = item.getAttribute("data-usercontextid");
      if (!userContextId || !isTerminalContainerId(userContextId)) {
        continue;
      }

      item.setAttribute("zen-terminal-native-container", "true");
      item.removeAttribute("command");
      item.removeAttribute("oncommand");
      if (item.__zenTerminalNativeContainerRouted) {
        continue;
      }

      item.__zenTerminalNativeContainerRouted = true;
      item.addEventListener(
        "command",
        (event) => {
          event.preventDefault();
          event.stopPropagation();
          event.stopImmediatePropagation();
          this.openTerminalContainerTab(userContextId);
        },
        true,
      );
    }
  }

  #terminalUrl(options = {}) {
    const params = new URLSearchParams();
    if (options.terminalSessionId) {
      params.set("session", options.terminalSessionId);
    }
    // Keep the old URL value readable for already-restored tabs. New tabs use
    // only the real Firefox userContextId.
    if (options.terminalContainerId) {
      params.set("container", options.terminalContainerId);
    }
    if (options.terminalContainerName) {
      params.set("name", options.terminalContainerName);
    }
    if (options.userContextId) {
      params.set("userContextId", options.userContextId);
    }
    const query = params.toString();
    return query ? `${ZEN_TERMINAL_TAB_URL}?${query}` : ZEN_TERMINAL_TAB_URL;
  }

  isTerminalTab(tab) {
    return Boolean(tab?.hasAttribute?.(ZEN_TERMINAL_TAB_ATTRIBUTE));
  }

  #forceNormalZenTab(tab) {
    if (!tab) {
      return;
    }

    tab.removeAttribute("zen-essential");
    tab.removeAttribute("zenDefaultUserContextId");
    tab.removeAttribute("zen-pinned-changed");
    delete tab._zenPinnedInitialState;
    if (tab.pinned) {
      gBrowser.unpinTab(tab);
    }
  }

  #forceNormalZenTabSoon(tab) {
    for (const delay of [0, 100, 500, 1500]) {
      window.setTimeout(() => this.#forceNormalZenTab(tab), delay);
    }
  }

  markTerminalTab(tab, options = {}) {
    if (!tab) {
      return;
    }
    this.#forceNormalZenTab(tab);
    this.#forceNormalZenTabSoon(tab);
    tab.setAttribute(ZEN_TERMINAL_TAB_ATTRIBUTE, "true");
    tab.removeAttribute("zen-show-sublabel");

    if (options.terminalSessionId) {
      const sessionId = normalizeTerminalSessionId(options.terminalSessionId);
      if (sessionId) {
        tab.setAttribute("zen-terminal-session-id", sessionId);
        try {
          SessionStore.setCustomTabValue(
            tab,
            "zenTerminalSessionId",
            sessionId,
          );
        } catch (_) {
          // The URL also carries the id and remains the restore source of truth.
        }
      }
    }
    if (options.userContextId) {
      tab.setAttribute("usercontextid", String(options.userContextId));
      tab.setAttribute(
        "zen-terminal-user-context-id",
        String(options.userContextId),
      );
    }

    const existingLabel = tab.getAttribute("label");
    const label =
      options.preserveExistingLabel && existingLabel
        ? existingLabel
        : options.terminalContainerName || existingLabel || "Terminal";
    tab.zenStaticLabel = label;
    tab._zenChangeLabelFlag = true;
    gBrowser._setTabLabel(tab, label, { _zenChangeLabelFlag: true });
    delete tab._zenChangeLabelFlag;
  }

  unmarkTerminalTab(tab) {
    if (tab) {
      tab.removeAttribute(ZEN_TERMINAL_TAB_ATTRIBUTE);
    }
  }

  #getNativeContainerName(userContextId) {
    try {
      return ContextualIdentityService.getUserContextLabel(userContextId);
    } catch (_) {
      return "Terminal";
    }
  }

  openTerminalContainerTab(userContextId) {
    const recipe = getTerminalContainerRecipe(userContextId);
    if (!recipe) {
      return null;
    }

    return this.openTerminalTab({
      userContextId,
      terminalContainerName: this.#getNativeContainerName(userContextId),
    });
  }

  #markRestoredTerminalTabsSoon() {
    window.setTimeout(() => this.#markRestoredTerminalTabs(), 0);
    window.setTimeout(() => this.#markRestoredTerminalTabs(), 1000);
  }

  #markRestoredTerminalTabs() {
    for (const tab of gBrowser?.tabs || []) {
      const spec = tab.linkedBrowser?.currentURI?.spec || "";
      if (!spec.startsWith(ZEN_TERMINAL_TAB_URL)) {
        continue;
      }

      const params = new URL(spec).searchParams;
      this.markTerminalTab(tab, {
        terminalSessionId: params.get("session"),
        terminalContainerId: params.get("container"),
        terminalContainerName: params.get("name") || "Terminal",
        userContextId: params.get("userContextId"),
        preserveExistingLabel: true,
      });
    }
  }

  openTerminalTab(options = {}) {
    const terminalSessionId =
      normalizeTerminalSessionId(options.terminalSessionId) ||
      Services.uuid.generateUUID().toString().slice(1, -1).toLowerCase();
    const terminalOptions = { ...options, terminalSessionId };
    const addTabOptions = {
      triggeringPrincipal: Services.scriptSecurityManager.getSystemPrincipal(),
    };
    if (terminalOptions.userContextId) {
      addTabOptions.userContextId = Number(terminalOptions.userContextId);
    }

    const tab = gBrowser.addTab(
      this.#terminalUrl(terminalOptions),
      addTabOptions,
    );
    this.#forceNormalZenTab(tab);
    this.markTerminalTab(tab, terminalOptions);
    gBrowser.selectedTab = tab;
    return tab;
  }

  #installTerminalSessionCloseHandler() {
    window.addEventListener(
      "TabClose",
      (event) => this.#onTerminalTabClose(event),
      true,
    );
  }

  #hasAnotherOpenTerminalTab(sessionId, closingTab) {
    for (const browserWindow of BrowserWindowTracker.orderedWindows) {
      if (!browserWindow?.gBrowser || browserWindow.closed) {
        continue;
      }
      for (const tab of browserWindow.gBrowser.tabs) {
        if (
          tab !== closingTab &&
          !tab.closing &&
          terminalSessionIdForTab(tab) === sessionId
        ) {
          return true;
        }
      }
    }
    return false;
  }

  #onTerminalTabClose(event) {
    const tab = event.target;
    const sessionId = terminalSessionIdForTab(tab);
    if (!sessionId) {
      return;
    }
    if (
      event.detail?.adoptedBy ||
      RunState.isQuitting ||
      window._zenClosingWindow ||
      window.closing
    ) {
      return;
    }

    // Zen may close synchronized copies of one tab in quick succession. Wait
    // until that work finishes, then destroy only when no copy remains.
    window.setTimeout(() => {
      if (!this.#hasAnotherOpenTerminalTab(sessionId, tab)) {
        void destroyTerminalSession(sessionId);
      }
    }, 0);
  }
}

window.gZenTerminalTabs = new ZenTerminalTabs();
