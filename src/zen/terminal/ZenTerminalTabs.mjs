/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * Zen Terminal Tabs
 *
 * The rule for this feature:
 * - Zen remains Zen: same shell, same workspaces, same folders, same menus.
 * - Browser containers and terminal containers are separate things.
 * - The normal New Tab/container picker must offer both browser tabs and
 *   terminal tabs, without adding a separate permanent terminal button.
 */

export const ZEN_TERMINAL_TAB_ATTRIBUTE = "zen-terminal-tab";
export const ZEN_TERMINAL_TAB_URL =
  "chrome://browser/content/zen-terminal/terminal.xhtml";

const TERMINAL_CONTAINERS_PREF = "zen.terminal.containers";
const TERMINAL_MENU_MARKER = "data-zen-terminal-menu";
const DEFAULT_TERMINAL_CONTAINER = {
  id: "default-terminal",
  name: "Default Terminal",
};

export class ZenTerminalTabs {
  constructor() {
    this.#installNewTabContainerMenuBridge();
  }

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

  #installNewTabContainerMenuBridge() {
    document.addEventListener(
      "popupshowing",
      event => {
        const popup = event.target;
        window.setTimeout(() => this.#injectTerminalChoices(popup), 0);
      },
      true,
    );
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
    item.addEventListener("command", () => this.promptForNewTerminalContainer());
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
