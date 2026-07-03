/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * Stores Zen's extra data for real Firefox containers.
 *
 * Firefox already owns the container itself: name, colour, icon, and
 * userContextId. Zen only stores the extra terminal-only fields here.
 */

export const ZEN_TERMINAL_CONTAINER_RECIPES_PREF =
  "zen.terminal.containerRecipes";

export const ZEN_TERMINAL_RECIPE_VERSION = 1;

export function readTerminalContainerRecipes() {
  try {
    const parsed = JSON.parse(
      Services.prefs.getStringPref(ZEN_TERMINAL_CONTAINER_RECIPES_PREF, "{}"),
    );
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed;
    }
  } catch (_) {
    // Bad user prefs should not break the browser. Treat them as empty.
  }
  return {};
}

export function writeTerminalContainerRecipes(recipes) {
  Services.prefs.setStringPref(
    ZEN_TERMINAL_CONTAINER_RECIPES_PREF,
    JSON.stringify(recipes || {}),
  );
}

export function normalizeTerminalRecipe(recipe) {
  if (typeof recipe === "string") {
    return {
      type: "single-command",
      command: recipe,
      steps: [],
    };
  }

  if (recipe && typeof recipe === "object") {
    return {
      type: String(recipe.type || "single-command"),
      command: String(recipe.command || ""),
      steps: Array.isArray(recipe.steps) ? recipe.steps : [],
    };
  }

  return {
    type: "single-command",
    command: "",
    steps: [],
  };
}

export function normalizeTerminalContainerRecord(record) {
  if (!record || record.kind !== "terminal") {
    return null;
  }

  return {
    version: Number(record.version || ZEN_TERMINAL_RECIPE_VERSION),
    kind: "terminal",
    folder: typeof record.folder === "string" ? record.folder : "",
    recipe: normalizeTerminalRecipe(record.recipe),
  };
}

export function getTerminalContainerRecipe(userContextId) {
  const key = String(userContextId || "");
  if (!key) {
    return null;
  }

  const recipes = readTerminalContainerRecipes();
  return normalizeTerminalContainerRecord(recipes[key]);
}

export function isTerminalContainerId(userContextId) {
  return Boolean(getTerminalContainerRecipe(userContextId));
}

export function setTerminalContainerRecipe(userContextId, record = {}) {
  const key = String(userContextId || "");
  if (!key) {
    return;
  }

  const recipes = readTerminalContainerRecipes();
  recipes[key] = {
    version: ZEN_TERMINAL_RECIPE_VERSION,
    kind: "terminal",
    folder: typeof record.folder === "string" ? record.folder : "",
    recipe: normalizeTerminalRecipe(record.recipe),
  };
  writeTerminalContainerRecipes(recipes);
}

export function removeTerminalContainerRecipe(userContextId) {
  const key = String(userContextId || "");
  if (!key) {
    return;
  }

  const recipes = readTerminalContainerRecipes();
  if (Object.hasOwn(recipes, key)) {
    delete recipes[key];
    writeTerminalContainerRecipes(recipes);
  }
}
