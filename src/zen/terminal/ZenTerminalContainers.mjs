/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

const TERMINAL_CONTAINERS_PREF = "zen.terminal.containers";
const DEFAULT_TERMINAL_CONTAINER = {
  id: "default-terminal",
  name: "Default Terminal",
};

function readTerminalContainers() {
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

function writeTerminalContainers(containers) {
  Services.prefs.setStringPref(
    TERMINAL_CONTAINERS_PREF,
    JSON.stringify(containers),
  );
}

function renderContainers() {
  const list = document.getElementById("terminal-containers-list");
  list.textContent = "";

  for (const container of readTerminalContainers()) {
    const row = document.createElement("article");
    row.className = "container-row";

    const name = document.createElement("strong");
    name.textContent = container.name;

    const meta = document.createElement("span");
    meta.textContent =
      container.id === DEFAULT_TERMINAL_CONTAINER.id
        ? "Built in"
        : "Custom terminal container";

    row.append(name, meta);

    if (container.id !== DEFAULT_TERMINAL_CONTAINER.id) {
      const removeButton = document.createElement("button");
      removeButton.type = "button";
      removeButton.textContent = "Remove";
      removeButton.addEventListener("click", () => {
        writeTerminalContainers(
          readTerminalContainers().filter(item => item.id !== container.id),
        );
        renderContainers();
      });
      row.append(removeButton);
    }

    list.append(row);
  }
}

function addTerminalContainer(name) {
  const cleanName = name.trim();
  if (!cleanName) {
    return;
  }

  const containers = readTerminalContainers().filter(
    container => container.id !== DEFAULT_TERMINAL_CONTAINER.id,
  );
  containers.push({
    id: `terminal-${Date.now()}`,
    name: cleanName,
  });
  writeTerminalContainers(containers);
}

window.addEventListener("DOMContentLoaded", () => {
  document
    .getElementById("add-terminal-container-form")
    .addEventListener("submit", event => {
      event.preventDefault();
      const input = document.getElementById("terminal-container-name");
      addTerminalContainer(input.value);
      input.value = "";
      renderContainers();
    });

  renderContainers();
});
