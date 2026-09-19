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
  setTerminalContainerRecipe,
} from "chrome://browser/content/zen-terminal/ZenTerminalContainerStore.mjs";
import {
  destroyTerminalSession,
  normalizeTerminalSessionId,
  retryPendingTerminalSessionDeletes,
} from "chrome://browser/content/zen-terminal/ZenTerminalSessionManager.mjs";

const { ContextualIdentityService } = ChromeUtils.importESModule(
  "moz-src:///toolkit/components/contextualidentity/ContextualIdentityService.sys.mjs",
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
  #terminalMenuPopups = new WeakSet();

  #isPrivateWindow() {
    return ChromeUtils.importESModule(
      "resource://gre/modules/PrivateBrowsingUtils.sys.mjs",
    ).PrivateBrowsingUtils.isWindowPrivate(window);
  }

  #allowTerminalLaunch() {
    if (!this.#isPrivateWindow()) return true;
    Services.prompt.alert(
      window,
      "Terminal unavailable in private windows",
      "Terminals can save shell history and files outside the browser. Open a normal window to use a terminal.",
    );
    return false;
  }

  constructor() {
    this.#ensureDefaultTerminalContainer();
    this.#patchFirefoxContainerMenuBuilder();
    this.#installTerminalSessionCloseHandler();
    this.#markRestoredTerminalTabsSoon();
    // Restore can finish long after startup, including background tabs and Undo Close.
    for (const eventName of ["SSTabRestored", "TabSelect"]) {
      window.addEventListener(eventName, (event) =>
        this.#markRestoredTerminalTab(event.target), true
      );
    }
    // Native location changes can clear a page's icon after restore/selection.
    // Repair the ordinary icon slot from the native notification, not a timer.
    window.addEventListener("TabAttrModified", (event) => {
      const tab = event.target;
      if (
        !event.detail?.changed?.includes("image") ||
        !tab?.hasAttribute?.(ZEN_TERMINAL_TAB_ATTRIBUTE) ||
        tab.zenStaticIcon || tab.closing
      ) return;
      const spec = tab.linkedBrowser?.currentURI?.spec || "";
      if (spec.split(/[?#]/u)[0] !== ZEN_TERMINAL_TAB_URL && !tab.hasAttribute("pending")) return;
      const icon = "chrome://browser/skin/zen-icons/selectable/terminal.svg";
      // setIcon emits the same event; checking the final attribute avoids recursion.
      if (tab.getAttribute("image") !== icon) gBrowser.setIcon(tab, icon);
    }, true);
    void retryPendingTerminalSessionDeletes();
  }

  #ensureDefaultTerminalContainer() {
    const pref = "zen.terminal.defaultContainerCreated";
    if (Services.prefs.getBoolPref(pref, false)) return;
    try {
      const identities = ContextualIdentityService.getPublicIdentities();
      if (
        !identities.some((identity) =>
          isTerminalContainerId(identity.userContextId),
        )
      ) {
        const identity = ContextualIdentityService.create(
          "Terminal",
          "briefcase",
          "purple",
        );
        setTerminalContainerRecipe(identity.userContextId, {
          recipe: { steps: [] },
        });
      }
      // Do not recreate a default the user deliberately deletes later.
      Services.prefs.setBoolPref(pref, true);
    } catch (error) {
      console.error("Could not prepare the default terminal container", error);
    }
  }

  /**
   * Populates Zen's one container menu with Firefox's real Web and Terminal
   * containers. The normal browser-tab row already exists beside this menu, so
   * Firefox's extra "No Container" row is deliberately omitted.
   */
  populateUnifiedContainerMenu(event) {
    this.#terminalMenuPopups.add(event.target);
    let result;
    try {
      result = window.createUserContextMenu(event, {
        isContextMenu: true,
        showDefaultTab: false,
      });
    } finally {
      this.#terminalMenuPopups.delete(event.target);
    }
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

      // Existing link, tab-reopen and workspace menus mean website identity,
      // not "run a saved command". Keep terminal choices only at explicit New Tab.
      const originalUserContextMenu = window.createUserContextMenu;
      window.createUserContextMenu = (event, options) => {
        const result = originalUserContextMenu.call(window, event, options);
        if (!this.#terminalMenuPopups.has(event.target) || this.#isPrivateWindow()) {
          for (const item of event.target.querySelectorAll("[data-usercontextid]")) {
            if (isTerminalContainerId(item.getAttribute("data-usercontextid"))) {
              item.remove();
            }
          }
        }
        return result;
      };
      const originalCreateContainerTabMenu = window.CreateContainerTabMenu;
      const patchedCreateContainerTabMenu = (event) => {
        this.#terminalMenuPopups.add(event.target);
        let result;
        try {
          result = originalCreateContainerTabMenu.call(window, event);
        } finally {
          this.#terminalMenuPopups.delete(event.target);
        }
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

  markTerminalTab(tab, options = {}) {
    if (!tab) {
      return;
    }
    tab.setAttribute(ZEN_TERMINAL_TAB_ATTRIBUTE, "true");
    // Use Zen's real icon slot and keep any icon the user deliberately chose.
    gBrowser.setIcon(
      tab,
      tab.zenStaticIcon || "chrome://browser/skin/zen-icons/selectable/terminal.svg",
    );
    // Marking a terminal must never undo native folders, pins or Essentials.
    // Only website URL-reset decoration is inappropriate for a terminal.
    tab.removeAttribute("zen-show-sublabel");
    tab.removeAttribute("zen-pinned-changed");
    tab.removeAttribute("had-zen-pinned-changed");
    tab.style.removeProperty("--zen-original-tab-icon");

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
    for (const tab of gBrowser?.tabs || []) this.#markRestoredTerminalTab(tab);
  }

  #markRestoredTerminalTab(tab) {
    if (!tab?.linkedBrowser || tab.closing) return;
    let spec = tab.linkedBrowser.currentURI?.spec || "";
    if (!spec.startsWith(ZEN_TERMINAL_TAB_URL) && tab.hasAttribute("pending")) {
      try {
        const state = JSON.parse(SessionStore.getTabState(tab));
        spec = state.entries?.[(state.index || 1) - 1]?.url || spec;
      } catch (_) {}
    }
    if (!spec.startsWith(ZEN_TERMINAL_TAB_URL)) return;
    try {
      const params = new URL(spec).searchParams;
      this.markTerminalTab(tab, {
        terminalSessionId: params.get("session"),
        terminalContainerId: params.get("container"),
        terminalContainerName: params.get("name") || "Terminal",
        userContextId: params.get("userContextId"),
        preserveExistingLabel: true,
      });
    } catch (_) {}
  }

  openTerminalTab(options = {}) {
    if (!this.#allowTerminalLaunch()) return null;
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
