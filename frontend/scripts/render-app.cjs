// Server-render the real dashboard (src/App.tsx) against a given API state, without a browser or network.
// Data hooks are replaced; everything else (components, labels, formatting) is the shipping code.
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const root = process.cwd();
const ts = require(path.join(root, "node_modules/typescript"));
const React = require(path.join(root, "node_modules/react"));
const { renderToStaticMarkup } = require(path.join(root, "node_modules/react-dom/server"));
const HOOKS = path.join(root, "src/hooks.ts");
const APP = path.join(root, "src/App.tsx");

/**
 * @param {object} opts
 * @param {object|null} opts.state     /api/state response (null = still loading)
 * @param {string|null} [opts.error]   backend error banner text
 * @param {object|null} [opts.detail]  /api/incidents/{id} response for the inspector
 * @param {number|null} [opts.selectedId] incident the user clicked (default: the app's own choice)
 */
function renderApp({ state, error = null, detail = null, selectedId = null }) {
  const cache = {};
  function load(file) {
    if (cache[file]) return cache[file];
    const code = ts.transpileModule(fs.readFileSync(file, "utf8"), {
      compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
    }).outputText;
    const exports = {};
    cache[file] = exports;
    function req(name) {
      if (name === "./api" || name === "../api" || name === "../../api") return { API_MODE: "live" };
      if (name === "react" && file === APP) {
        // The selection state starts null; inject the clicked incident, keep every other useState real.
        return { ...React, useState: (initial) => (initial === null ? [selectedId, () => {}] : React.useState(initial)) };
      }
      if (!name.startsWith(".")) return require(path.join(root, "node_modules", name));
      let target = path.resolve(path.dirname(file), name);
      if (!path.extname(target)) target += fs.existsSync(target + ".tsx") ? ".tsx" : ".ts";
      if (target.endsWith(".json")) return JSON.parse(fs.readFileSync(target, "utf8"));
      if (target === HOOKS) {
        const real = load(HOOKS);
        return {
          ...real,
          useHandoffState: () => ({ state, error, refresh: () => {} }),
          useIncidentDetail: (id) => ({ detail: detail && detail.id === id ? detail : null, reload: () => {} }),
          useCallMode: () => null,
        };
      }
      return load(target);
    }
    vm.runInNewContext(code, { exports, require: req, console, setInterval, clearInterval, setTimeout, clearTimeout });
    return exports;
  }
  return renderToStaticMarkup(React.createElement(load(APP).default));
}

module.exports = { renderApp };
