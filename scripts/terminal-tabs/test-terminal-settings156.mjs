#!/usr/bin/env node
/* MPL-2.0: Synthetic tests for the patched Firefox 156 native container editor. */
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { cpSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { execFileSync } from "node:child_process";
import vm from "node:vm";
import * as store from "../../src/zen/terminal/ZenTerminalContainerStore.mjs";
import { compileTerminalRecipeSteps, validateTerminalStartingDirectory } from "../../src/zen/terminal/ZenTerminalRecipeRunner.mjs";

const root = path.resolve(import.meta.dirname, "../..");
const fixture = path.join(import.meta.dirname, "fixtures/firefox156-settings");
const receipt = JSON.parse(readFileSync(path.join(fixture, "receipt.json")));
const temporary = mkdtempSync(path.join(tmpdir(), "zen-settings156-proof-"));
const patched = new Map();
const patchFailures = [];
try {
  for (const file of receipt.files) {
    const original = readFileSync(path.join(fixture, file.path));
    assert.equal(
      createHash("sha256").update(original).digest("hex"),
      file.sha256,
    );
    assert.equal(
      createHash("sha1").update(Buffer.concat([
        Buffer.from(`blob ${original.length}\0`), original,
      ])).digest("hex"), file.git_blob_sha,
    );
    cpSync(path.join(fixture, file.path), path.join(temporary, file.path), {
      recursive: true,
    });
    const patchPath = path.join(
      root,
      "src",
      path.dirname(file.path),
      path.basename(file.path).replaceAll(".", "-") + ".patch",
    );
    try {
      execFileSync("patch", ["--dry-run", "--batch", "--fuzz=0", "-p1", "-i", patchPath], {
        cwd: temporary,
      });
    } catch (error) {
      patchFailures.push(`${file.path}: ${error.stdout?.toString() || error.message}`);
      continue;
    }
    execFileSync("patch", ["--batch", "--fuzz=0", "-p1", "-i", patchPath], { cwd: temporary });
    patched.set(
      path.basename(file.path),
      readFileSync(path.join(temporary, file.path), "utf8"),
    );
  }
} finally {
  rmSync(temporary, { recursive: true, force: true });
}
assert.deepEqual(patchFailures, [], "Firefox 156 strict patch blockers (no fuzzy application allowed)");
console.log(
  "✓ five production patches apply to hash-verified pristine Firefox 156.0 sources",
);

class FakeEvent {
  constructor(type, options = {}) {
    this.type = type;
    Object.assign(this, options);
    this.defaultPrevented = false;
  }
  preventDefault() {
    this.defaultPrevented = true;
  }
}
class Element {
  constructor(tag, document) {
    this.tagName = tag;
    this.isConnected = true;
    this.ownerDocument = document;
    this.children = [];
    this.listeners = new Map();
    this.attrs = {};
    this.style = {};
    this.value = "";
    this.hidden = false;
    const classes = new Set();
    this.classList = {
      add: (name) => classes.add(name),
      remove: (name) => classes.delete(name),
      contains: (name) => classes.has(name),
    };
  }
  setAttribute(name, value) {
    this.attrs[name] = String(value);
  }
  append(...elements) {
    for (const element of elements) {
      element.parentElement = this;
      this.children.push(element);
    }
  }
  prepend(element) {
    element.parentElement = this;
    this.children.unshift(element);
  }
  replaceChildren(...elements) {
    this.children = [];
    this.append(...elements);
  }
  addEventListener(type, listener) {
    const list = this.listeners.get(type) || [];
    list.push(listener);
    this.listeners.set(type, list);
  }
  removeEventListener(type, listener) {
    this.listeners.set(
      type,
      (this.listeners.get(type) || []).filter((item) => item !== listener),
    );
  }
  dispatchEvent(event) {
    for (const listener of this.listeners.get(event.type) || [])
      listener(event);
    if (event.bubbles && this.parentElement)
      this.parentElement.dispatchEvent(event);
    return !event.defaultPrevented;
  }
  focus() {
    this.focused = true;
  }
}
function descendants(element) {
  return [element, ...element.children.flatMap(descendants)];
}
function documentFixture() {
  const doc = new Element("document");
  const win = new Element("window", doc);
  Object.assign(win, {
    document: doc,
    Event: FakeEvent,
    MozXULElement: { insertFTLIfNeeded() {} },
    requestAnimationFrame: (fn) => fn(),
    resizeDialog() {},
  });
  Object.assign(doc, {
    defaultView: win,
    documentURIObject: { spec: "about:preferences#containers" },
    l10n: {
      setAttributes() {},
      async formatValues() {
        return ["title", "message", "ok", "cancel"];
      },
    },
    createElementNS: (_namespace, tag) => new Element(tag, doc),
    getElementById: (id) => descendants(doc).find((node) => node.id === id),
  });
  const host = new Element("div", doc);
  host.id = "containerEditorHost";
  doc.append(host);
  return { doc, win, host };
}
let confirmation = true,
  tabsConfirmation = 0,
  count = 0,
  nextId = 7;
const calls = [];
const prefs = new Map();
globalThis.Services = {
  prefs: {
    getStringPref: (key, fallback) => prefs.get(key) ?? fallback,
    getBoolPref: (key, fallback) => prefs.get(key) ?? fallback,
    setStringPref: (key, value) => prefs.set(key, value),
  },
  prompt: {
    confirm: () => {
      calls.push("confirm");
      return confirmation;
    },
    confirmEx: () => tabsConfirmation,
  },
};
const identities = {
  containerIcons: ["briefcase"],
  containerColors: ["purple"],
  getContainerColorLabel: (value) => value,
  getContainerIconLabel: (value) => value,
  getContainerColorCode: (value) => value === "purple",
  getContainerIconURL: (value) => value === "briefcase",
  create(name) {
    calls.push(`create:${name}`);
    return { userContextId: nextId++ };
  },
  update(id) {
    calls.push(`update:${id}`);
  },
  remove(id) {
    calls.push(`remove:${id}`);
  },
  countContainerTabs: () => count,
  async closeContainerTabs(id) {
    calls.push(`close-tabs:${id}`);
  },
};
let pickerResult = 0, pickerPath = "/synthetic/space 雪 ' $(literal) ", pickerThrows = false;
const validFolders = new Set([pickerPath]);
const Ci = { nsIFile: {}, nsIFilePicker: { modeGetFolder: 2, returnOK: 0 } };
const Cc = {
  "@mozilla.org/file/local;1": { createInstance() {
    return { initWithPath(value) { this.path = value; }, exists() { return validFolders.has(this.path); }, isDirectory() { return validFolders.has(this.path); }, isReadable() { return validFolders.has(this.path); } };
  } },
  "@mozilla.org/filepicker;1": { createInstance() {
    if (pickerThrows) throw new Error("picker unavailable");
    return { init(_context, _title, mode) { assert.equal(mode, 2); }, file: { path: pickerPath }, open(callback) { callback(pickerResult); } };
  } },
};
Object.assign(globalThis, { Cc, Ci });
const telemetry = [];
const globals = {
  Glean: { containers: { addContainerClicked: { record: value => telemetry.push(value) }, manageContainersOpened: { record: value => telemetry.push(value) } } },
  Cc, Ci,
  ...store,
  compileTerminalRecipeSteps,
  validateTerminalStartingDirectory,
  Services,
  destroyTerminalSessionsForUserContextId: (id) => {
    calls.push(`destroy:${id}`);
    return Promise.resolve([]);
  },
  ChromeUtils: {
    defineLazyGetter(object, key, getter) {
      Object.defineProperty(object, key, { configurable: true, get() {
        const value = getter(); Object.defineProperty(object, key, { value }); return value;
      } });
    },
    defineESModuleGetters(object, modules) {
      for (const key of Object.keys(modules)) object[key] = identities;
    },
  },
  FormData: class {
    constructor(form) {
      this.form = form;
    }
    get(name) {
      return descendants(this.form).find(
        (element) => element.attrs.name === name,
      )?.value;
    }
  },
};
const stripImports = (source) =>
  source.replace(/^import[\s\S]*?from "[^"]+";\n/gm, "");
const editorContext = vm.createContext(globals);
vm.runInContext(
  stripImports(patched.get("ContainerEditor.mjs")).replace(
    "export class ContainerEditor",
    "globalThis.ContainerEditor = class ContainerEditor",
  ),
  editorContext,
);
function editor(options = {}) {
  const { host } = documentFixture();
  const result = new editorContext.ContainerEditor(host, options);
  result.render();
  return result;
}
const tests = [];
const test = (name, run) => tests.push([name, run]);

test("native creation requires kind and name and saves one terminal identity", () => {
  const item = editor();
  assert.equal(item.isValid, false);
  item._name.value = "Terminal work";
  assert.equal(item.commit(), false);
  item._terminalButton.dispatchEvent(new FakeEvent("click"));
  assert.equal(item.isValid, true);
  assert.equal(item._terminalFields.hidden, false);
  assert.equal(item.commit(), true);
  assert.equal(item.userContextId, 7);
  assert.equal(store.getTerminalContainerRecipe(7).kind, "terminal");
  assert.deepEqual(calls, ["create:Terminal work"]);
});

test("add/edit/reorder/remove keeps commands and saves a validated SSH recipe", () => {
  const item = editor();
  item._name.value = "Remote";
  item.chooseKind("terminal");
  item.addTerminalRecipeStep();
  item._lastStepInput.value = "ssh host";
  item._lastStepInput.dispatchEvent(new FakeEvent("input", { bubbles: true }));
  item.addTerminalRecipeStep();
  item._lastStepInput.value = "claude";
  item._lastStepInput.dispatchEvent(new FakeEvent("input", { bubbles: true }));
  item.addTerminalRecipeStep();
  item._lastStepInput.value = "unused";
  item._lastStepInput.dispatchEvent(new FakeEvent("input"));
  const first = item.terminalRecipeSteps[0].id,
    last = item.terminalRecipeSteps[2].id;
  item.moveTerminalRecipeStep(first, 1);
  assert.deepEqual(
    Array.from(item.getTerminalRecipeSteps(), (row) => row.command),
    ["claude", "ssh host", "unused"],
  );
  item.moveTerminalRecipeStep(first, -1);
  item.removeTerminalRecipeStep(last);
  assert.equal(item.commit(), true);
  assert.deepEqual(
    store.getTerminalContainerRecipe(7).recipe.steps.map((row) => row.command),
    ["ssh host", "claude"],
  );
  assert.match(
    compileTerminalRecipeSteps(
      store.getTerminalContainerRecipe(7).recipe.steps,
    ),
    /'ssh' '-tt'/,
  );
});

test("invalid SSH recipe cannot create or update an identity", () => {
  const item = editor();
  item._name.value = "Invalid";
  item.chooseKind("terminal");
  item.terminalRecipeSteps = [
    { id: "a", command: "ssh -vN host" },
    { id: "b", command: "claude" },
  ];
  assert.equal(item.commit(), false);
  assert.equal(item._recipeError.hidden, false);
  assert.match(item._recipeError.textContent, /cannot be used/);
  assert.deepEqual(calls, []);
  assert.equal(store.getTerminalContainerRecipe(7), null);
});

test("legacy one-command recipe opens unchanged", () => {
  prefs.set(
    store.ZEN_TERMINAL_CONTAINER_RECIPES_PREF,
    JSON.stringify({ 7: { kind: "terminal", recipe: "cd ~/work && claude" } }),
  );
  const item = editor({
    userContextId: 7,
    identity: { name: "Legacy", color: "purple", icon: "briefcase" },
  });
  assert.equal(item.containerKind, "terminal");
  assert.equal(item.getTerminalRecipeSteps()[0].command, "cd ~/work && claude");
  assert.equal(item.commit(), true);
  assert.equal(
    store.getTerminalContainerRecipe(7).recipe.steps[0].command,
    "cd ~/work && claude",
  );
});

test("Terminal to Web cancellation preserves running work and its recipe", () => {
  store.setTerminalContainerRecipe(7, { recipe: { steps: ["claude"] } });
  const item = editor({
    userContextId: 7,
    identity: { name: "Work", color: "purple", icon: "briefcase" },
  });
  item.chooseKind("web");
  confirmation = false;
  assert.equal(item.commit(), false);
  assert.deepEqual(calls, ["confirm"]);
  assert.ok(store.getTerminalContainerRecipe(7));
  confirmation = true;
  assert.equal(item.commit(), true);
  assert.deepEqual(calls, ["confirm", "confirm", "update:7", "destroy:7"]);
  assert.equal(store.getTerminalContainerRecipe(7), null);
});

const configDocument = documentFixture();
const configContext = vm.createContext({
  ...globals,
  window: configDocument.win,
  document: configDocument.doc,
  Ci: {
    nsIPrompt: { BUTTON_TITLE_IS_STRING: 1, BUTTON_POS_0: 1, BUTTON_POS_1: 1 },
  },
  history: { state: null },
  URL: { fromURI: uri => new URL(uri.spec) },
  containerOptions: () => [],
  Preferences: { AsyncSetting: class {}, addSetting() {}, addAll() {} },
  SettingGroupManager: { registerGroups() {} },
});
vm.runInContext(stripImports(patched.get("containers.mjs")), configContext);
test("deletion warns even with no visible tabs and preserves cancelled work", async () => {
  store.setTerminalContainerRecipe(7);
  confirmation = false;
  await configContext.removeContainer(7);
  assert.deepEqual(calls, ["confirm"]);
  assert.ok(store.getTerminalContainerRecipe(7));
  confirmation = true;
  await configContext.removeContainer(7);
  assert.deepEqual(calls, ["confirm", "confirm", "destroy:7", "remove:7"]);
  assert.equal(store.getTerminalContainerRecipe(7), null);
});
test("native open-tab cancellation happens before any session teardown", async () => {
  store.setTerminalContainerRecipe(7);
  count = 2;
  tabsConfirmation = 1;
  await configContext.removeContainer(7);
  assert.deepEqual(calls, ["confirm"]);
  assert.ok(store.getTerminalContainerRecipe(7));
  tabsConfirmation = 0;
  await configContext.removeContainer(7);
  assert.deepEqual(calls, [
    "confirm",
    "confirm",
    "close-tabs:7",
    "destroy:7",
    "remove:7",
  ]);
});

test("dialog accept is cancelled when shared editor validation fails", () => {
  const { doc, win } = documentFixture();
  win.arguments = [{}];
  doc.documentElement = new Element("window", doc);
  doc.querySelector = () => ({ getButton: () => ({ disabled: false }) });
  let succeeds = false;
  const context = vm.createContext({
    document: doc,
    window: win,
    AdjustableTitle: { hide() {} },
    ChromeUtils: {
      importESModule: () => ({
        ContainerEditor: class {
          constructor() {
            this.form = new Element("form", doc);
            this.isValid = true;
          }
          render() {}
          commit() {
            return succeeds;
          }
        },
      }),
    },
  });
  vm.runInContext(patched.get("containers.js"), context);
  win.dispatchEvent(new FakeEvent("DOMContentLoaded"));
  const failed = new FakeEvent("dialogaccept");
  doc.dispatchEvent(failed);
  assert.equal(failed.defaultPrevented, true);
  succeeds = true;
  const valid = new FakeEvent("dialogaccept");
  doc.dispatchEvent(valid);
  assert.equal(valid.defaultPrevented, false);
});

test("native creation panel remains open on invalid recipes", async () => {
  const { doc, win } = documentFixture();
  win.top = win;
  win.gBrowser = {};
  win.gZenUIManager = { panelUIPosition: () => "after_start" };
  for (const id of [
    "containerCreation-panel",
    "containerCreation-panel-body",
    "containerCreation-create-button",
    "containerCreation-cancel-button",
    "navigator-toolbox",
  ]) {
    const element = new Element("div", doc);
    element.id = id;
    doc.append(element);
  }
  let hidden = 0,
    succeeds = false;
  const panel = doc.getElementById("containerCreation-panel");
  panel.hidePopup = () => hidden++;
  panel.openPopup = () => {};
  const context = vm.createContext({
    ...globals,
    ContainerEditor: class {
      constructor() {
        this.form = new Element("form", doc);
        this.isValid = true;
      }
      render() {}
      focus() {}
      commit() {
        return succeeds;
      }
    },
  });
  vm.runInContext(
    stripImports(patched.get("ContainerCreationPanel.mjs")).replace(
      "export const ContainerCreationPanel",
      "globalThis.ContainerCreationPanel",
    ),
    context,
  );
  await context.ContainerCreationPanel.open(win, "terminal-proof");
  assert.equal(telemetry[0].source, "terminal-proof");
  doc
    .getElementById("containerCreation-create-button")
    .dispatchEvent(new FakeEvent("click"));
  assert.equal(hidden, 0);
  succeeds = true;
  doc
    .getElementById("containerCreation-create-button")
    .dispatchEvent(new FakeEvent("click"));
  assert.equal(hidden, 1);
});

test("folder picker save and reopen preserves literal path; cancel does not save", () => {
  const item = editor(); item._name.value = "Project"; item.chooseKind("terminal");
  item.chooseTerminalStartingDirectory();
  assert.equal(item._startingDirectory.value, pickerPath);
  assert.equal(prefs.size, 0);
  assert.equal(item.commit(), true);
  assert.equal(store.getTerminalContainerRecipe(7).recipe.startingDirectory, pickerPath);
  const reopened = editor({ userContextId: 7 });
  assert.equal(reopened._startingDirectory.value, pickerPath);
  pickerResult = 1;
  reopened._startingDirectory.value = "/typed/unchanged";
  reopened.chooseTerminalStartingDirectory();
  assert.equal(reopened._startingDirectory.value, "/typed/unchanged");
  assert.equal(store.getTerminalContainerRecipe(7).recipe.startingDirectory, pickerPath);
});
test("missing or relative folder cannot create an identity or modify saved setup", () => {
  const item = editor(); item._name.value = "Project"; item.chooseKind("terminal");
  for (const folder of ["relative", "~", "/missing"]) {
    item._startingDirectory.value = folder;
    assert.equal(item.commit(), false);
    assert.equal(item._recipeError.hidden, false);
    assert.equal(prefs.size, 0); assert.deepEqual(calls, []);
  }
});
test("picker failure leaves editable input and never saves", () => {
  const item = editor(); item.chooseKind("terminal"); pickerThrows = true;
  item.chooseTerminalStartingDirectory();
  assert.equal(item._folderButton.disabled, false);
  assert.equal(item._recipeError.hidden, false);
  assert.match(item._recipeError.textContent, /type the full folder path/);
  assert.equal(prefs.size, 0);
});

for (const [name, run] of tests) {
  prefs.clear();
  pickerResult = 0; pickerThrows = false;
  calls.length = 0;
  telemetry.length = 0;
  confirmation = true;
  tabsConfirmation = 0;
  count = 0;
  nextId = 7;
  await run();
  console.log(`✓ ${name}`);
}
console.log(
  `\n${tests.length} Firefox 156 Settings behavior tests passed; source receipt and five patches verified.`,
);
