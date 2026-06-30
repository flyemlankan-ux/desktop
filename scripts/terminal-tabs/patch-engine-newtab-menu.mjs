#!/usr/bin/env node
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import { readFileSync, writeFileSync } from "node:fs";

const browserJsPath = "engine/browser/base/content/browser.js";
const browserJs = readFileSync(browserJsPath, "utf8");

const oldFunction = `function CreateContainerTabMenu(event) {
  // Do not open context menus within menus.
  // Note that triggerNode is null if we're opened by long press.
  if (event.target.triggerNode?.closest("menupopup")) {
    event.preventDefault();
    return;
  }
  createUserContextMenu(event, {
    useAccessKeys: false,
    showDefaultTab: true,
  });
}
`;

const newFunction = `function CreateContainerTabMenu(event) {
  // Do not open context menus within menus.
  // Note that triggerNode is null if we're opened by long press.
  if (event.target.triggerNode?.closest("menupopup")) {
    event.preventDefault();
    return;
  }
  createUserContextMenu(event, {
    useAccessKeys: false,
    showDefaultTab: true,
  });

  const popup = event.target;
  if (popup.querySelector?.('[data-zen-terminal-menu="true"]')) {
    return;
  }

  const make = tag => {
    if (document.createXULElement) {
      return document.createXULElement(tag);
    }
    return document.createElementNS(
      "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul",
      tag
    );
  };

  const openTerminalTab = options => {
    const params = new URLSearchParams();
    if (options?.terminalContainerId) {
      params.set("container", options.terminalContainerId);
    }
    if (options?.terminalContainerName) {
      params.set("name", options.terminalContainerName);
    }
    const suffix = params.toString() ? "?" + params.toString() : "";
    const tab = gBrowser.addTab(
      "chrome://browser/content/zen-terminal/terminal.xhtml" + suffix,
      { triggeringPrincipal: Services.scriptSecurityManager.getSystemPrincipal() }
    );
    tab.setAttribute("zen-terminal-tab", "true");
    tab.setAttribute("zen-show-sublabel", "true");
    if (options?.terminalContainerId) {
      tab.setAttribute("zen-terminal-container-id", options.terminalContainerId);
    }
    tab.setAttribute("label", options?.terminalContainerName || "Terminal");
    gBrowser.selectedTab = tab;
  };

  const openTerminalContainersPage = () => {
    gBrowser.selectedTab = gBrowser.addTab(
      "chrome://browser/content/zen-terminal/containers.xhtml",
      { triggeringPrincipal: Services.scriptSecurityManager.getSystemPrincipal() }
    );
  };

  const readTerminalContainers = () => {
    let containers = [];
    try {
      containers = JSON.parse(
        Services.prefs.getStringPref("zen.terminal.containers", "[]")
      );
    } catch (_) {
      containers = [];
    }
    if (!Array.isArray(containers) || !containers.length) {
      return [{ id: "default-terminal", name: "Default Terminal" }];
    }
    return containers.filter(container => container?.id && container?.name);
  };

  const mark = node => {
    node.setAttribute("data-zen-terminal-menu", "true");
    return node;
  };

  const separator = mark(make("menuseparator"));

  const terminalTab = mark(make("menuitem"));
  terminalTab.setAttribute("label", "New Terminal Tab");
  terminalTab.addEventListener("command", () => openTerminalTab());

  const terminalContainerMenu = mark(make("menu"));
  terminalContainerMenu.setAttribute("label", "New Terminal Container Tab");
  const terminalContainerPopup = make("menupopup");
  for (const container of readTerminalContainers()) {
    const item = make("menuitem");
    item.setAttribute("label", container.name);
    item.addEventListener("command", () =>
      openTerminalTab({
        terminalContainerId: container.id,
        terminalContainerName: container.name,
      })
    );
    terminalContainerPopup.appendChild(item);
  }
  terminalContainerMenu.appendChild(terminalContainerPopup);

  const manageTerminalContainers = mark(make("menuitem"));
  manageTerminalContainers.setAttribute("label", "Manage Terminal Containers…");
  manageTerminalContainers.addEventListener("command", openTerminalContainersPage);

  const manageBrowserContainers = Array.from(popup.children || []).find(child =>
    (child.getAttribute?.("label") || child.textContent || "").includes("Manage containers")
  );

  for (const row of [separator, terminalTab, terminalContainerMenu, manageTerminalContainers]) {
    popup.insertBefore(row, manageBrowserContainers || null);
  }
}
`;

if (browserJs.includes("New Terminal Container Tab")) {
  console.log("browser.js already has terminal New Tab menu patch.");
  process.exit(0);
}

if (!browserJs.includes(oldFunction)) {
  throw new Error("Could not find exact CreateContainerTabMenu function to patch.");
}

writeFileSync(browserJsPath, browserJs.replace(oldFunction, newFunction));
console.log("Patched Firefox New Tab container menu with terminal choices.");
