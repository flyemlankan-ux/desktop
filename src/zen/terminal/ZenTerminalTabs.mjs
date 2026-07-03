/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * Zen Terminal Tabs
 *
 * Slice 1 keeps the old terminal fallback menu, but adds the new path:
 * real Firefox containers whose Zen metadata says kind = terminal open
 * terminal tabs instead of blank browser tabs.
 */

import {
  getTerminalContainerRecipe,
  isTerminalContainerId,
} from "chrome://browser/content/zen-terminal/ZenTerminalContainerStore.mjs";

const { ContextualIdentityService } = ChromeUtils.importESModule(
  "resource://gre/modules/ContextualIdentityService.sys.mjs",
);

export const ZEN_TERMINAL_TAB_ATTRIBUTE = "zen-terminal-tab";
export const ZEN_TERMINAL_TAB_URL =
  "chrome://browser/content/zen-terminal/terminal.xhtml";
const ZEN_TERMINAL_CONTAINERS_URL =
  "chrome://browser/content/zen-terminal/containers.xhtml";

const TERMINAL_CONTAINERS_PREF = "zen.terminal.containers";
const TERMINAL_MENU_MARKER = "data-zen-terminal-menu";
const DEFAULT_TERMINAL_CONTAINER = {
  id: "default-terminal",
  name: "Default Terminal",
};

export class ZenTerminalTabs {
  constructor() {
    this.#installNewTabContainerMenuBridge();
    this.#installNativeTerminalContainerRouter();
    this.#patchFirefoxContainerMenuBuilder();
    this.#markRestoredTerminalTabsSoon();
  }

  #terminalUrl(options = {}) {
    const params = new URLSearchParams();
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

  #readTerminalContainers() {
    let containers = [];
    try {
      containers = JSON.parse(
        Services.prefs.getStringPref(TERMINAL_CONTAINERS_PREF, "[]"),
      );
    } catch (_) {
      containers = [];
    }

    if (!Array.isArray(containers) || !containers.length) {
      return [DEFAULT_TERMINAL_CONTAINER];
    }

    return containers
      .filter(container => container?.id && container?.name)
      .map(container => ({
        id: String(container.id),
        name: String(container.name),
      }));
  }

  #writeTerminalContainers(containers) {
    Services.prefs.setStringPref(
      TERMINAL_CONTAINERS_PREF,
      JSON.stringify(containers),
    );
  }

  #createXULElement(tagName) {
    if (document.createXULElement) {
      return document.createXULElement(tagName);
    }
    return document.createElementNS(
      "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul",
      tagName,
    );
  }

  #menuLabel(node) {
    return (
      node.getAttribute?.("label") ||
      node.getAttribute?.("aria-label") ||
      node.textContent ||
      ""
    ).trim();
  }

  #isBrowserContainerNewTabPopup(popup) {
    if (!popup || popup.localName !== "menupopup") {
      return false;
    }

    if (popup.id === "zenCreateNewPopup") {
      return true;
    }

    const children = Array.from(popup.children || []);
    const labels = children.map(child => this.#menuLabel(child)).join(" | ");
    const hasBrowserContainerRows = children.some(child => {
      const attrs = child.getAttributeNames?.() || [];
      return attrs.some(attr => attr.toLowerCase().includes("usercontext"));
    });

    return (
      hasBrowserContainerRows ||
      labels.includes("No Container") ||
      labels.includes("Manage containers") ||
      labels.includes("Personal") ||
      labels.includes("Banking") ||
      labels.includes("Shopping")
    );
  }

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
      const patchedCreateContainerTabMenu = event => {
        const result = originalCreateContainerTabMenu.call(window, event);
        this.#routeNativeTerminalContainerRows(event.target);
        this.#injectTerminalChoices(event.target);
        window.setTimeout(() => {
          this.#routeNativeTerminalContainerRows(event.target);
          this.#injectTerminalChoices(event.target);
        }, 0);
        return result;
      };
      patchedCreateContainerTabMenu.__zenTerminalPatched = true;
      window.CreateContainerTabMenu = patchedCreateContainerTabMenu;
    };

    install();
  }

  #installNewTabContainerMenuBridge() {
    document.addEventListener(
      "popupshowing",
      event => {
        const popup = event.target;
        window.setTimeout(() => {
          this.#routeNativeTerminalContainerRows(popup);
          this.#injectTerminalChoices(popup);
        }, 0);
      },
      true,
    );
  }

  #installNativeTerminalContainerRouter() {
    document.addEventListener(
      "popupshowing",
      event => {
        const popup = event.target;
        window.setTimeout(
          () => this.#routeNativeTerminalContainerRows(popup),
          0,
        );
      },
      true,
    );
  }

  #routeNativeTerminalContainerRows(popup) {
    if (!this.#isBrowserContainerNewTabPopup(popup)) {
      return;
    }

    for (const item of popup.querySelectorAll?.("[data-usercontextid]") || []) {
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
        event => {
          event.preventDefault();
          event.stopPropagation();
          event.stopImmediatePropagation();
          this.openTerminalContainerTab(userContextId);
        },
        true,
      );
    }
  }

  #injectTerminalChoices(popup) {
    if (!this.#isBrowserContainerNewTabPopup(popup)) {
      return;
    }

    if (popup.querySelector?.(`[${TERMINAL_MENU_MARKER}="true"]`)) {
      return;
    }

    const terminalRows = [
      this.#makeSeparator(),
      this.#makeTerminalTabItem(),
      this.#makeTerminalContainerMenu(),
      this.#makeManageTerminalContainersItem(),
    ];

    const manageBrowserContainersItem = Array.from(popup.children || []).find(
      child => this.#menuLabel(child).includes("Manage containers"),
    );

    for (const row of terminalRows) {
      row.setAttribute(TERMINAL_MENU_MARKER, "true");
      popup.insertBefore(row, manageBrowserContainersItem || null);
    }
  }

  #makeSeparator() {
    return this.#createXULElement("menuseparator");
  }

  #makeTerminalTabItem() {
    const item = this.#createXULElement("menuitem");
    item.setAttribute("label", "New Terminal Tab");
    item.setAttribute("class", "menuitem-iconic");
    item.addEventListener("command", () => this.openTerminalTab());
    return item;
  }

  #makeTerminalContainerMenu() {
    const menu = this.#createXULElement("menu");
    menu.setAttribute("label", "New Terminal Container Tab");
    menu.setAttribute("class", "menu-iconic");

    const popup = this.#createXULElement("menupopup");
    for (const container of this.#readTerminalContainers()) {
      const item = this.#createXULElement("menuitem");
      item.setAttribute("label", container.name);
      item.addEventListener("command", () =>
        this.openTerminalTab({
          terminalContainerId: container.id,
          terminalContainerName: container.name,
        }),
      );
      popup.appendChild(item);
    }

    menu.appendChild(popup);
    return menu;
  }

  #makeManageTerminalContainersItem() {
    const item = this.#createXULElement("menuitem");
    item.setAttribute("label", "Manage Terminal Containers…");
    item.addEventListener("command", () => this.openTerminalContainersPage());
    return item;
  }

  promptForNewTerminalContainer() {
    const input = { value: "" };
    const ok = Services.prompt.prompt(
      window,
      "New Terminal Container",
      "Name this terminal container:",
      input,
      null,
      {},
    );

    const name = input.value.trim();
    if (!ok || !name) {
      return null;
    }

    const containers = this.#readTerminalContainers().filter(
      container => container.id !== DEFAULT_TERMINAL_CONTAINER.id,
    );
    const id = `terminal-${Date.now()}`;
    const container = { id, name };
    containers.push(container);
    this.#writeTerminalContainers(containers);
    return container;
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
    if (options.userContextId) {
      tab.setAttribute("usercontextid", String(options.userContextId));
      tab.setAttribute(
        "zen-terminal-user-context-id",
        String(options.userContextId),
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

  openTerminalContainersPage() {
    const tab = gBrowser.addTab(ZEN_TERMINAL_CONTAINERS_URL, {
      triggeringPrincipal: Services.scriptSecurityManager.getSystemPrincipal(),
    });
    gBrowser.selectedTab = tab;
    return tab;
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
        terminalContainerId: params.get("container"),
        terminalContainerName: params.get("name") || "Terminal",
        userContextId: params.get("userContextId"),
      });
    }
  }

  openTerminalTab(options = {}) {
    const addTabOptions = {
      triggeringPrincipal: Services.scriptSecurityManager.getSystemPrincipal(),
    };
    if (options.userContextId) {
      addTabOptions.userContextId = Number(options.userContextId);
    }

    const tab = gBrowser.addTab(this.#terminalUrl(options), addTabOptions);
    this.markTerminalTab(tab, options);
    gBrowser.selectedTab = tab;
    return tab;
  }
}

window.gZenTerminalTabs = new ZenTerminalTabs();
