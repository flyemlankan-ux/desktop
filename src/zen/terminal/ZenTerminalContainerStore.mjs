/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * Stores Zen's extra data for real Firefox containers.
 *
 * Firefox owns the real container: name, colour, icon, and userContextId.
 * Zen only stores whether that container opens a terminal, plus one optional
 * ordered startup recipe.
 */

export const ZEN_TERMINAL_CONTAINER_RECIPES_PREF =
  "zen.terminal.containerRecipes";

export const ZEN_TERMINAL_RECIPE_VERSION = 3;

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

function normalizeTerminalStep(step, index, usedIds) {
  const command =
    typeof step === "string"
      ? step.trim()
      : step && typeof step === "object"
        ? String(step.command || "").trim()
        : "";
  if (!command) {
    return null;
  }

  const requestedId =
    step && typeof step === "object" ? String(step.id || "").trim() : "";
  const baseId = requestedId || `step-${index + 1}`;
  let id = baseId;
  let suffix = 2;
  while (usedIds.has(id)) {
    id = `${baseId}-${suffix++}`;
  }
  usedIds.add(id);

  return { id, command };
}

export function normalizeTerminalRecipe(recipe) {
  const legacyCommand =
    typeof recipe === "string"
      ? recipe.trim()
      : recipe && typeof recipe === "object"
        ? String(recipe.command || "").trim()
        : "";
  const rawSteps =
    recipe && typeof recipe === "object" && Array.isArray(recipe.steps)
      ? recipe.steps
      : [];
  const usedIds = new Set();
  let steps = rawSteps
    .map((step, index) => normalizeTerminalStep(step, index, usedIds))
    .filter(Boolean);

  // Version 2 stored one command and reserved an empty steps array. Reading it
  // as one step upgrades the data without changing the preference immediately.
  if (!steps.length && legacyCommand) {
    steps = [
      normalizeTerminalStep(
        { id: "step-1", command: legacyCommand },
        0,
        usedIds,
      ),
    ];
  }

  return {
    type: "ordered-steps",
    // Keep the old field readable until the terminal page moves to the v3
    // runner. New multi-step recipes intentionally have no misleading legacy
    // command.
    command: steps.length === 1 ? steps[0].command : "",
    steps,
  };
}

export function normalizeTerminalContainerRecord(record) {
  if (!record || record.kind !== "terminal") {
    return null;
  }

  return {
    version: ZEN_TERMINAL_RECIPE_VERSION,
    kind: "terminal",
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
