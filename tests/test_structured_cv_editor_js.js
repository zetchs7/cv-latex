"use strict";

/*
 * Tests ejecutables del editor estructurado de CV.
 *
 * Modo unitario (sin navegador):
 *   node tests/test_structured_cv_editor_js.js
 *
 * Modo navegador (prueba real de browser, requiere la app corriendo):
 *   node tests/test_structured_cv_editor_js.js --browser http://127.0.0.1:8123
 *   Variables opcionales: CHROME_PATH (binario chromium), CDP_PORT.
 *
 * El modo navegador usa CDP (Chrome DevTools Protocol) directamente sobre el
 * binario chromium disponible, sin dependencias externas.
 */

const assert = require("node:assert");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const editor = require("../app/static/js/structured_editor.js");

const DEFAULT_CHROME_PATH = path.join(
  process.env.HOME || "",
  ".cache",
  "ms-playwright",
  "chromium-1243",
  "chrome-linux64",
  "chrome",
);

const results = { passed: 0, failed: 0, failures: [] };

function record(name, error) {
  if (error) {
    results.failed += 1;
    results.failures.push({ name, error });
    console.log(`FAIL ${name}`);
    console.log(`     ${error && error.message ? error.message.split("\n")[0] : error}`);
  } else {
    results.passed += 1;
    console.log(`PASS ${name}`);
  }
}

async function runTest(name, fn) {
  try {
    await fn();
    record(name, null);
  } catch (error) {
    record(name, error);
  }
}

/* ------------------------------------------------------------------ */
/* Unit tests (funciones puras del modulo del editor)                  */
/* ------------------------------------------------------------------ */

const unitTests = [
  function buildEmptyPayloadHasFullShape() {
    const payload = editor.buildEmptyPayload();
    assert.strictEqual(payload.schema_version, 2);
    for (const section of [
      "personal",
      "contact",
      "summary",
      "skills",
      "experience",
      "education",
      "certifications",
      "languages",
      "projects",
      "links",
      "additional_info",
      "metadata",
    ]) {
      assert.ok(section in payload, `falta seccion ${section}`);
    }
    assert.deepStrictEqual(payload.experience, []);
    assert.deepStrictEqual(payload.contact.links, []);
  },

  function parseBootstrapRejectsInvalidJson() {
    const parsed = editor.parseBootstrapPayload("{not json");
    assert.ok(parsed.error);
    const parsed2 = editor.parseBootstrapPayload('["array"]');
    assert.ok(parsed2.error);
    const parsed3 = editor.parseBootstrapPayload('{"schema_version":2}');
    assert.ok(!parsed3.error);
    assert.strictEqual(parsed3.payload.schema_version, 2);
  },

  function normalizeFillsMissingSectionsPreservingUnknowns() {
    const normalized = editor.normalizeBootstrapPayload({
      schema_version: 2,
      personal: { full_name: "Ana" },
      unknown_section: { keep: true },
    });
    assert.strictEqual(normalized.personal.full_name, "Ana");
    assert.deepStrictEqual(normalized.experience, []);
    assert.deepStrictEqual(normalized.skills, []);
    assert.deepStrictEqual(normalized.metadata, {});
    assert.deepStrictEqual(normalized.unknown_section, { keep: true });
  },

  function moveItemHandlesBoundariesAndRenumbers() {
    const items = [
      { label: "A", order: 1 },
      { label: "B", order: 2 },
      { label: "C", order: 3 },
    ];
    const movedUp = editor.moveItem(items, 2, -1);
    assert.deepStrictEqual(
      movedUp.map((item) => item.label),
      ["A", "C", "B"],
    );
    assert.deepStrictEqual(
      movedUp.map((item) => item.order),
      [1, 2, 3],
    );
    const boundary = editor.moveItem(items, 0, -1);
    assert.deepStrictEqual(
      boundary.map((item) => item.label),
      ["A", "B", "C"],
    );
    const boundaryEnd = editor.moveItem(items, 2, 1);
    assert.deepStrictEqual(
      boundaryEnd.map((item) => item.label),
      ["A", "B", "C"],
    );
  },

  function removeAndAppendRenumberOrders() {
    const items = [
      { label: "A", order: 1, custom: 1 },
      { label: "B", order: 2 },
      { label: "C", order: 3 },
    ];
    const removed = editor.removeItem(items, 0);
    assert.deepStrictEqual(
      removed.map((item) => item.label),
      ["B", "C"],
    );
    assert.deepStrictEqual(
      removed.map((item) => item.order),
      [1, 2],
    );
    const appended = editor.appendItem(removed, { label: "D" });
    assert.strictEqual(appended.length, 3);
    assert.strictEqual(appended[2].label, "D");
    assert.strictEqual(appended[2].order, 3);
    assert.strictEqual(items[0].custom, 1, "no debe mutar el array original");
  },

  function listTextRoundtrip() {
    const lines = editor.textToLines(" Python \n\nFastAPI\nSQL ");
    assert.deepStrictEqual(lines, ["Python", "FastAPI", "SQL"]);
    assert.strictEqual(editor.linesToText(["Python", "FastAPI"]), "Python\nFastAPI");
    assert.strictEqual(editor.linesToText([]), "");
  },

  function buildSubmitPayloadMergesAndPreservesUnknownKeys() {
    const base = {
      schema_version: 2,
      personal: { full_name: "Ana", unknown_personal: "x" },
      contact: { email: "old@example.com", links: ["https://old"] },
      summary: "viejo",
      experience: [
        { company: "Globex", role: "Dev", custom_note: "interno", order: 1 },
      ],
      skills: [{ label: "Python", internal_weight: 7, order: 1 }],
      unknown_section: { keep: true },
      metadata: { source: "structured_test" },
    };
    const payload = editor.buildSubmitPayload({
      basePayload: base,
      scalars: {
        personal: { full_name: "Ana Perez", headline: "Tech Lead", location: "" },
        contact: { email: "ana@example.com", phone: "", links: ["https://ana.example.com"] },
        summary: "nuevo resumen",
      },
      sectionItems: {
        experience: [{ company: "Globex", role: "Dev", custom_note: "interno", order: 1 }],
        skills: [
          { label: "Python", internal_weight: 7, order: 1 },
          { label: "SQL", order: 2 },
        ],
      },
    });
    assert.strictEqual(payload.schema_version, 2);
    assert.strictEqual(payload.personal.full_name, "Ana Perez");
    assert.strictEqual(payload.personal.headline, "Tech Lead");
    assert.strictEqual(payload.personal.unknown_personal, "x");
    assert.strictEqual(payload.contact.email, "ana@example.com");
    assert.deepStrictEqual(payload.contact.links, ["https://ana.example.com"]);
    assert.strictEqual(payload.summary, "nuevo resumen");
    assert.strictEqual(payload.experience[0].custom_note, "interno");
    assert.strictEqual(payload.experience[0].order, 1);
    assert.strictEqual(payload.skills[0].internal_weight, 7);
    assert.strictEqual(payload.skills[1].order, 2);
    assert.deepStrictEqual(payload.unknown_section, { keep: true });
    assert.deepStrictEqual(payload.metadata, { source: "structured_test" });
  },

  function sectionSpecsCoverAllSectionsWithSpanishLabels() {
    const specSections = Object.keys(editor.SECTION_SPECS);
    for (const section of [
      "experience",
      "education",
      "skills",
      "certifications",
      "languages",
      "projects",
      "links",
      "additional_info",
    ]) {
      assert.ok(specSections.includes(section), `falta spec de ${section}`);
      const spec = editor.SECTION_SPECS[section];
      assert.ok(spec.title && spec.title.length > 3, `falta titulo espanol para ${section}`);
      assert.ok(spec.addLabel && spec.addLabel.length > 3, `falta label de agregar para ${section}`);
      assert.ok(spec.maxItems > 0, `falta maximo de items para ${section}`);
      assert.ok(spec.fields.length > 0, `faltan campos para ${section}`);
    }
    assert.strictEqual(editor.SECTION_SPECS.experience.fields.length, 9);
    assert.ok(
      editor.SECTION_SPECS.experience.fields.some((field) => field.name === "current" && field.type === "boolean"),
    );
    assert.ok(
      editor.SECTION_SPECS.experience.fields.some((field) => field.name === "highlights" && field.type === "lines"),
    );
  },
];

/* ------------------------------------------------------------------ */
/* Browser tests (CDP sobre chromium real)                             */
/* ------------------------------------------------------------------ */

class SimpleCdp {
  constructor(wsUrl) {
    this.wsUrl = wsUrl;
    this.ws = null;
    this.nextId = 1;
    this.pending = new Map();
    this.eventHandlers = new Map();
  }

  connect() {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.wsUrl);
      this.ws.onopen = () => resolve();
      this.ws.onerror = () => reject(new Error("No se pudo conectar al WebSocket de CDP"));
      this.ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.id && this.pending.has(message.id)) {
          const pending = this.pending.get(message.id);
          this.pending.delete(message.id);
          if (message.error) {
            pending.reject(new Error(message.error.message));
          } else {
            pending.resolve(message.result);
          }
        } else if (message.method) {
          const handlers = this.eventHandlers.get(message.method) || [];
          for (const handler of [...handlers]) handler(message.params);
        }
      };
    });
  }

  send(method, params) {
    const id = this.nextId;
    this.nextId += 1;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params: params || {} }));
    });
  }

  onceEvent(method, timeoutMs) {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        reject(new Error(`Timeout esperando el evento CDP ${method}`));
      }, timeoutMs || 20000);
      const handler = (params) => {
        clearTimeout(timer);
        const handlers = this.eventHandlers.get(method) || [];
        const index = handlers.indexOf(handler);
        if (index >= 0) handlers.splice(index, 1);
        resolve(params);
      };
      if (!this.eventHandlers.has(method)) this.eventHandlers.set(method, []);
      this.eventHandlers.get(method).push(handler);
    });
  }

  async evaluate(expression) {
    const result = await this.send("Runtime.evaluate", {
      expression,
      returnByValue: true,
      awaitPromise: true,
    });
    if (result.exceptionDetails) {
      throw new Error(
        `Runtime.evaluate fallo: ${JSON.stringify(result.exceptionDetails.exception)}`,
      );
    }
    return result.result.value;
  }

  async navigate(url) {
    await this.send("Page.enable");
    const load = this.onceEvent("Page.loadEventFired", 30000);
    await this.send("Page.navigate", { url });
    await load;
  }

  close() {
    if (this.ws) {
      try {
        this.ws.close();
      } catch (error) {
        /* ignorar */
      }
    }
  }
}

async function waitForHttp(url, timeoutMs) {
  const deadline = Date.now() + (timeoutMs || 15000);
  let lastError = null;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok) return response;
      lastError = new Error(`HTTP ${response.status}`);
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw lastError || new Error(`Timeout esperando ${url}`);
}

async function openPageTarget(port) {
  const base = `http://127.0.0.1:${port}`;
  let newResponse = await fetch(`${base}/json/new?about:blank`, { method: "PUT" });
  if (!newResponse.ok) {
    newResponse = await fetch(`${base}/json/new?about:blank`);
  }
  if (!newResponse.ok) {
    throw new Error(`No se pudo crear un target de CDP: HTTP ${newResponse.status}`);
  }
  const target = await newResponse.json();
  const cdp = new SimpleCdp(target.webSocketDebuggerUrl);
  await cdp.connect();
  return cdp;
}

async function setInputValue(cdp, selector, value) {
  await cdp.evaluate(
    `(function () {
       const el = document.querySelector(${JSON.stringify(selector)});
       if (!el) throw new Error("No existe " + ${JSON.stringify(selector)});
       el.value = ${JSON.stringify(value)};
       el.dispatchEvent(new Event("input", { bubbles: true }));
       el.dispatchEvent(new Event("change", { bubbles: true }));
       return true;
     })();`,
  );
}

async function waitForEditorReady(cdp) {
  const deadline = Date.now() + 10000;
  while (Date.now() < deadline) {
    const ready = await cdp.evaluate(
      `document.querySelector("#structured-editor-root") && document.querySelector("#structured-editor-root").dataset.structuredEditorReady === "true"`,
    );
    if (ready) return;
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error("El editor estructurado no termino de inicializar en el navegador");
}

async function currentPagePath(cdp) {
  return cdp.evaluate("window.location.pathname + window.location.search");
}

async function browserCreateLegacyCv(baseUrl) {
  const body = new URLSearchParams({
    title: "CV Legacy Browser",
    full_name: "Persona Legacy",
    email: "legacy-browser@example.com",
    phone: "",
    professional_summary: "Perfil legacy",
    experience_summary: "Experiencia legacy",
    education_summary: "Educacion legacy",
    skills: "Python",
  });
  const response = await fetch(`${baseUrl}/cvs/`, {
    method: "POST",
    body,
    redirect: "manual",
  });
  assert.strictEqual(response.status, 303, "la creacion legacy via HTTP debe redirigir");
  const location = response.headers.get("location");
  return parseInt(location.split("?")[0].split("/").pop(), 10);
}

const browserTests = [
  {
    name: "browser: editor nuevo renderiza secciones y flujo completo persiste orden",
    async fn(cdp, baseUrl) {
      await cdp.navigate(`${baseUrl}/cvs/new/structured`);
      await waitForEditorReady(cdp);

      const sectionCount = await cdp.evaluate(
        'document.querySelectorAll("[data-structured-section]").length',
      );
      assert.strictEqual(sectionCount, 8, "deben existir 8 secciones de items");
      const headings = await cdp.evaluate(
        'Array.from(document.querySelectorAll("[data-structured-section-title]")).map(el => el.textContent)',
      );
      for (const expected of [
        "Experiencia laboral",
        "Educacion",
        "Skills",
        "Certificaciones",
        "Idiomas",
        "Proyectos",
        "Links",
        "Informacion adicional",
      ]) {
        assert.ok(headings.includes(expected), `falta el titulo ${expected}`);
      }

      const initialItems = await cdp.evaluate(
        'document.querySelectorAll("[data-structured-item]").length',
      );
      assert.strictEqual(initialItems, 0, "el editor nuevo arranca sin items");

      await setInputValue(cdp, 'input[name="title"]', "CV Browser");
      await setInputValue(cdp, 'input[data-editor-field="personal.full_name"]', "Ana Browser");
      await setInputValue(cdp, 'input[data-editor-field="contact.email"]', "ana@example.com");

      await cdp.evaluate('document.querySelector(\'[data-add-item="experience"]\').click()');
      await cdp.evaluate('document.querySelector(\'[data-add-item="experience"]\').click()');
      await cdp.evaluate(
        `(function () {
           const cards = document.querySelectorAll('[data-structured-item="experience"]');
           if (cards.length !== 2) throw new Error("se esperaban 2 items");
           const setField = (card, field, value) => {
             const input = card.querySelector('[data-item-field="' + field + '"]');
             if (!input) throw new Error("falta campo " + field);
             input.value = value;
             input.dispatchEvent(new Event("input", { bubbles: true }));
           };
           setField(cards[0], "company", "Alpha");
           setField(cards[0], "role", "Dev");
           setField(cards[1], "company", "Beta");
           setField(cards[1], "role", "Lead");
           return true;
         })();`,
      );

      await cdp.evaluate(
        'document.querySelector(\'[data-structured-item="experience"][data-item-position="1"] [data-move-up]\').click()',
      );

      const collected = await cdp.evaluate(
        'document.querySelector("#structured-editor-root").__structuredEditorController.collectPayload()',
      );
      assert.strictEqual(collected.personal.full_name, "Ana Browser");
      assert.strictEqual(collected.experience[0].company, "Beta");
      assert.strictEqual(collected.experience[0].order, 1);
      assert.strictEqual(collected.experience[1].company, "Alpha");
      assert.strictEqual(collected.experience[1].order, 2);

      await cdp.evaluate(
        'document.querySelector("form[data-structured-form]").requestSubmit()',
      );
      await new Promise((resolve) => setTimeout(resolve, 800));

      const detailPath = await currentPagePath(cdp);
      assert.ok(/\/cvs\/\d+\?/.test(detailPath), `se esperaba el detalle del CV, llego ${detailPath}`);
      assert.ok(detailPath.includes("message="));
      const cvId = parseInt(detailPath.split("?")[0].split("/").pop(), 10);
      assert.ok(Number.isInteger(cvId));

      await cdp.navigate(`${baseUrl}/cvs/${cvId}/structured-edit`);
      await waitForEditorReady(cdp);
      const bootstrap = await cdp.evaluate(
        'JSON.parse(document.getElementById("structured-editor-bootstrap").textContent)',
      );
      assert.strictEqual(bootstrap.experience[0].company, "Beta");
      assert.strictEqual(bootstrap.experience[0].order, 1);
      assert.strictEqual(bootstrap.experience[1].company, "Alpha");
      const renderedFirstCompany = await cdp.evaluate(
        'document.querySelector(\'[data-structured-item="experience"][data-item-position="0"] [data-item-field="company"]\').value',
      );
      assert.strictEqual(renderedFirstCompany, "Beta");
      const structuredBadge = await cdp.evaluate(
        'document.body.textContent.includes("Datos estructurados validos")',
      );
      assert.ok(structuredBadge, "el editor reabierto debe indicar datos estructurados validos");
      return cvId;
    },
  },
  {
    name: "browser: submit fallido preserva lo ingresado con error en espanol",
    async fn(cdp, baseUrl) {
      await cdp.navigate(`${baseUrl}/cvs/new/structured`);
      await waitForEditorReady(cdp);

      await setInputValue(cdp, 'input[name="title"]', "");
      await setInputValue(cdp, 'input[data-editor-field="personal.full_name"]', "Nombre Browser");
      await cdp.evaluate('document.querySelector(\'[data-add-item="skills"]\').click()');
      await setInputValue(
        cdp,
        '[data-structured-item="skills"][data-item-position="0"] [data-item-field="label"]',
        "SkillX",
      );

      await cdp.evaluate(
        'document.querySelector("form[data-structured-form]").requestSubmit()',
      );
      await new Promise((resolve) => setTimeout(resolve, 800));

      const path = await currentPagePath(cdp);
      assert.ok(path.includes("/cvs/new/structured"), `se esperaba rerender 422, llego ${path}`);

      const errorBox = await cdp.evaluate(
        'document.querySelector(".structured-error-box") && document.querySelector(".structured-error-box").textContent',
      );
      assert.ok(errorBox, "debe existir la caja de errores");
      assert.ok(errorBox.includes("titulo interno"), "el error debe mencionar el titulo");

      const bootstrap = await cdp.evaluate(
        'JSON.parse(document.getElementById("structured-editor-bootstrap").textContent)',
      );
      assert.strictEqual(bootstrap.personal.full_name, "Nombre Browser");
      assert.strictEqual(bootstrap.skills[0].label, "SkillX");

      const skillInput = await cdp.evaluate(
        'document.querySelector(\'[data-structured-item="skills"][data-item-position="0"] [data-item-field="label"]\').value',
      );
      assert.strictEqual(skillInput, "SkillX");
      const nameInput = await cdp.evaluate(
        'document.querySelector(\'input[data-editor-field="personal.full_name"]\').value',
      );
      assert.strictEqual(nameInput, "Nombre Browser");
    },
  },
  {
    name: "browser: datos maliciosos no se ejecutan ni se inyectan como HTML",
    async fn(cdp, baseUrl) {
      await cdp.navigate(`${baseUrl}/cvs/new/structured`);
      await waitForEditorReady(cdp);

      await setInputValue(cdp, 'input[name="title"]', "CV XSS");
      await setInputValue(
        cdp,
        'input[data-editor-field="personal.full_name"]',
        '<img src=x onerror="window.__xssHit=1">',
      );
      await cdp.evaluate('document.querySelector(\'[data-add-item="experience"]\').click()');
      await setInputValue(
        cdp,
        '[data-structured-item="experience"][data-item-position="0"] [data-item-field="company"]',
        '<script>window.__xssHit=2;</script>',
      );

      await cdp.evaluate(
        'document.querySelector("form[data-structured-form]").requestSubmit()',
      );
      await new Promise((resolve) => setTimeout(resolve, 800));

      const path = await currentPagePath(cdp);
      assert.ok(/\/cvs\/\d+\?/.test(path), `se esperaba detalle tras submit valido, llego ${path}`);
      const cvId = parseInt(path.split("?")[0].split("/").pop(), 10);

      const xssHit = await cdp.evaluate("window.__xssHit || null");
      assert.strictEqual(xssHit, null, "ningun payload malicioso debe ejecutarse");

      await cdp.navigate(`${baseUrl}/cvs/${cvId}/structured-edit`);
      await waitForEditorReady(cdp);
      const xssHitAfterReopen = await cdp.evaluate("window.__xssHit || null");
      assert.strictEqual(xssHitAfterReopen, null, "reabrir el editor no debe ejecutar payloads");
      const injectedImg = await cdp.evaluate(
        'document.querySelectorAll("#structured-editor-root img").length',
      );
      assert.strictEqual(injectedImg, 0, "no debe existir un img inyectado en el editor");
      const companyValue = await cdp.evaluate(
        'document.querySelector(\'[data-structured-item="experience"][data-item-position="0"] [data-item-field="company"]\').value',
      );
      assert.ok(companyValue.includes("<script>"), "el valor debe quedar como texto, no como HTML");
    },
  },
  {
    name: "browser: CV legacy muestra advertencia y se convierte al guardar",
    async fn(cdp, baseUrl) {
      const cvId = await browserCreateLegacyCv(baseUrl);

      await cdp.navigate(`${baseUrl}/cvs/${cvId}/structured-edit`);
      await waitForEditorReady(cdp);
      const warning = await cdp.evaluate(
        'document.querySelector(".structured-warning") && document.querySelector(".structured-warning").textContent',
      );
      assert.ok(warning, "debe existir la advertencia de datos estructurados no disponibles");
      assert.ok(warning.includes("no tiene datos estructurados"), warning);

      const bootstrap = await cdp.evaluate(
        'JSON.parse(document.getElementById("structured-editor-bootstrap").textContent)',
      );
      assert.strictEqual(bootstrap.personal.full_name, "Persona Legacy");
      assert.strictEqual(bootstrap.experience[0].summary, "Experiencia legacy");

      await setInputValue(cdp, 'input[name="title"]', "CV Legacy Browser");
      await setInputValue(cdp, 'input[data-editor-field="personal.full_name"]', "Persona Legacy");
      await cdp.evaluate('document.querySelector(\'[data-add-item="certifications"]\').click()');
      await setInputValue(
        cdp,
        '[data-structured-item="certifications"][data-item-position="0"] [data-item-field="name"]',
        "AWS SA",
      );

      await cdp.evaluate(
        'document.querySelector("form[data-structured-form]").requestSubmit()',
      );
      await new Promise((resolve) => setTimeout(resolve, 800));

      const path = await currentPagePath(cdp);
      assert.ok(/\/cvs\/\d+\?/.test(path), `se esperaba detalle tras conversion, llego ${path}`);

      await cdp.navigate(`${baseUrl}/cvs/${cvId}/structured-edit`);
      await waitForEditorReady(cdp);
      const warningAfter = await cdp.evaluate(
        'document.querySelector(".structured-warning") ? true : false',
      );
      assert.strictEqual(warningAfter, false, "tras guardar no debe quedar advertencia");
      const bootstrapAfter = await cdp.evaluate(
        'JSON.parse(document.getElementById("structured-editor-bootstrap").textContent)',
      );
      assert.strictEqual(bootstrapAfter.metadata.source, "structured_editor");
      assert.strictEqual(bootstrapAfter.certifications[0].name, "AWS SA");
    },
  },
];

async function runBrowserTests(baseUrl) {
  const chromePath = process.env.CHROME_PATH || DEFAULT_CHROME_PATH;
  if (!fs.existsSync(chromePath)) {
    throw new Error(`No se encontro un binario chromium en ${chromePath}`);
  }
  const port = parseInt(process.env.CDP_PORT || "9333", 10);
  const profileDir = fs.mkdtempSync(path.join(os.tmpdir(), "cv-latex-t4-chrome-"));
  const chromeArgs = [
    "--headless=new",
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profileDir}`,
    "--no-sandbox",
    "--disable-gpu",
    "--no-first-run",
    "--disable-extensions",
    "about:blank",
  ];
  console.log(`Navegador: ${chromePath}`);
  console.log(`URL base: ${baseUrl}`);

  const chrome = spawn(chromePath, chromeArgs, { stdio: "ignore" });
  let cdp = null;
  try {
    await waitForHttp(`http://127.0.0.1:${port}/json/version`, 20000);
    cdp = await openPageTarget(port);
    for (const test of browserTests) {
      await runTest(test.name, () => test.fn(cdp, baseUrl));
    }
  } finally {
    if (cdp) cdp.close();
    chrome.kill("SIGTERM");
  }
}

async function main() {
  for (const test of unitTests) {
    await runTest(`unit: ${test.name}`, test);
  }

  const browserArgIndex = process.argv.indexOf("--browser");
  if (browserArgIndex !== -1) {
    const baseUrl = process.argv[browserArgIndex + 1];
    if (!baseUrl) {
      throw new Error("--browser requiere la URL base de la app");
    }
    try {
      await runBrowserTests(baseUrl);
    } catch (error) {
      record("browser: harness", error);
    }
  } else {
    console.log("Sin --browser <url>: se omiten las pruebas de navegador.");
  }

  console.log(`\nResultado: ${results.passed} pasaron, ${results.failed} fallaron.`);
  if (results.failed > 0) {
    process.exit(1);
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
