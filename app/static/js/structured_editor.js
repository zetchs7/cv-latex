/*
 * Editor estructurado de CV (T4).
 *
 * - Estado inicial: JSON de bootstrap serializado por el servidor con el filtro
 *   `tojson` de Jinja dentro de <script id="structured-editor-bootstrap">.
 * - Todo el contenido del usuario se inserta con nodos DOM y `textContent` /
 *   `value`; nunca con `innerHTML` (regla LL-001).
 * - El cliente NO valida: arma el payload y el servidor valida todo antes de
 *   persistir. Los limites en `maxlength`/botones deshabilitados son guia UX.
 * - Las claves desconocidas de payload, secciones e items viajan intactas:
 *   el estado guarda los objetos completos y `buildSubmitPayload` los mezcla.
 *
 * API pura exportada (testeable en Node sin navegador):
 *   buildEmptyPayload, parseBootstrapPayload, normalizeBootstrapPayload,
 *   itemsFromSection, moveItem, removeItem, appendItem, renumberItems,
 *   buildDefaultItem, textToLines, linesToText, buildSubmitPayload,
 *   SECTION_SPECS, SCALAR_FIELDS.
 */

(function (global, factory) {
  const api = factory(global);
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    global.StructuredCVEditor = api;
  }
})(typeof window !== "undefined" ? window : globalThis, function factory(global) {
  "use strict";

  const SCHEMA_VERSION = 2;

  const SCALAR_FIELDS = {
    personal: ["full_name", "headline", "location"],
    contact: ["email", "phone", "links"],
    summary: [],
  };

  const SECTION_SPECS = {
    experience: {
      title: "Experiencia laboral",
      addLabel: "Agregar experiencia",
      itemLabel: "Experiencia",
      maxItems: 30,
      fields: [
        { name: "company", label: "Empresa", type: "text", maxlength: 120 },
        { name: "role", label: "Cargo", type: "text", maxlength: 120 },
        { name: "location", label: "Ubicacion", type: "text", maxlength: 120 },
        { name: "start_date", label: "Inicio", type: "text", maxlength: 40 },
        { name: "end_date", label: "Fin", type: "text", maxlength: 40 },
        { name: "current", label: "Trabajo actual", type: "boolean" },
        { name: "summary", label: "Resumen", type: "textarea", maxlength: 600, rows: 3 },
        { name: "highlights", label: "Logros (uno por linea)", type: "lines", maxlength: 240, rows: 3 },
        { name: "technologies", label: "Tecnologias (una por linea)", type: "lines", maxlength: 60, rows: 2 },
      ],
    },
    education: {
      title: "Educacion",
      addLabel: "Agregar educacion",
      itemLabel: "Educacion",
      maxItems: 30,
      fields: [
        { name: "institution", label: "Institucion", type: "text", maxlength: 160 },
        { name: "degree", label: "Titulo", type: "text", maxlength: 160 },
        { name: "field", label: "Campo", type: "text", maxlength: 120 },
        { name: "start_date", label: "Inicio", type: "text", maxlength: 40 },
        { name: "end_date", label: "Fin", type: "text", maxlength: 40 },
        { name: "summary", label: "Resumen", type: "textarea", maxlength: 600, rows: 3 },
      ],
    },
    skills: {
      title: "Skills",
      addLabel: "Agregar skill",
      itemLabel: "Skill",
      maxItems: 40,
      fields: [
        { name: "label", label: "Skill", type: "text", maxlength: 120 },
        { name: "category", label: "Categoria", type: "text", maxlength: 80 },
        { name: "level", label: "Nivel", type: "text", maxlength: 80 },
      ],
    },
    certifications: {
      title: "Certificaciones",
      addLabel: "Agregar certificacion",
      itemLabel: "Certificacion",
      maxItems: 30,
      fields: [
        { name: "name", label: "Nombre", type: "text", maxlength: 160 },
        { name: "issuer", label: "Emisor", type: "text", maxlength: 120 },
        { name: "date", label: "Fecha", type: "text", maxlength: 40 },
      ],
    },
    languages: {
      title: "Idiomas",
      addLabel: "Agregar idioma",
      itemLabel: "Idioma",
      maxItems: 20,
      fields: [
        { name: "name", label: "Idioma", type: "text", maxlength: 60 },
        { name: "level", label: "Nivel", type: "text", maxlength: 60 },
      ],
    },
    projects: {
      title: "Proyectos",
      addLabel: "Agregar proyecto",
      itemLabel: "Proyecto",
      maxItems: 30,
      fields: [
        { name: "name", label: "Nombre", type: "text", maxlength: 160 },
        { name: "summary", label: "Resumen", type: "textarea", maxlength: 600, rows: 3 },
        { name: "link", label: "Link", type: "text", maxlength: 300 },
        { name: "technologies", label: "Tecnologias (una por linea)", type: "lines", maxlength: 60, rows: 2 },
      ],
    },
    links: {
      title: "Links",
      addLabel: "Agregar link",
      itemLabel: "Link",
      maxItems: 30,
      fields: [
        { name: "label", label: "Etiqueta", type: "text", maxlength: 80 },
        { name: "url", label: "URL", type: "text", maxlength: 300 },
      ],
    },
    additional_info: {
      title: "Informacion adicional",
      addLabel: "Agregar informacion",
      itemLabel: "Informacion",
      maxItems: 20,
      fields: [
        { name: "title", label: "Titulo", type: "text", maxlength: 120 },
        { name: "content", label: "Contenido", type: "textarea", maxlength: 600, rows: 3 },
      ],
    },
  };

  const ITEM_SECTION_NAMES = Object.keys(SECTION_SPECS);

  /* ------------------------- Funciones puras ------------------------- */

  function buildEmptyPayload() {
    return {
      schema_version: SCHEMA_VERSION,
      personal: { full_name: "", headline: "", location: "" },
      contact: { email: "", phone: "", links: [] },
      summary: "",
      skills: [],
      experience: [],
      education: [],
      certifications: [],
      languages: [],
      projects: [],
      links: [],
      additional_info: [],
      metadata: { source: "", synced_from_legacy_at: "" },
    };
  }

  function parseBootstrapPayload(rawPayload) {
    let payload;
    try {
      payload = JSON.parse(rawPayload);
    } catch (error) {
      return { error: "El contenido inicial del editor no es un JSON valido." };
    }
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
      return { error: "El contenido inicial del editor debe ser un objeto JSON." };
    }
    return { payload: payload };
  }

  function normalizeBootstrapPayload(payload) {
    const result = Object.assign({}, payload);
    if (typeof result.schema_version !== "number") {
      result.schema_version = SCHEMA_VERSION;
    }
    for (const section of ["personal", "contact", "metadata"]) {
      if (!result[section] || typeof result[section] !== "object" || Array.isArray(result[section])) {
        result[section] = {};
      }
    }
    if (typeof result.summary !== "string") {
      result.summary = "";
    }
    for (const section of ITEM_SECTION_NAMES) {
      if (!Array.isArray(result[section])) {
        result[section] = [];
      }
    }
    return result;
  }

  function itemsFromSection(basePayload, section) {
    const rawItems = basePayload[section];
    if (!Array.isArray(rawItems)) {
      return [];
    }
    return rawItems
      .filter((item) => item && typeof item === "object" && !Array.isArray(item))
      .map((item) => Object.assign({}, item));
  }

  function renumberItems(items) {
    return items.map((item, index) => Object.assign({}, item, { order: index + 1 }));
  }

  function moveItem(items, index, delta) {
    const target = index + delta;
    if (target < 0 || target >= items.length) {
      return items.map((item) => Object.assign({}, item));
    }
    const next = items.map((item) => Object.assign({}, item));
    const moved = next.splice(index, 1)[0];
    next.splice(target, 0, moved);
    return renumberItems(next);
  }

  function removeItem(items, index) {
    const next = items
      .filter((_, currentIndex) => currentIndex !== index)
      .map((item) => Object.assign({}, item));
    return renumberItems(next);
  }

  function appendItem(items, item) {
    const next = items.map((existing) => Object.assign({}, existing));
    const added = Object.assign({}, item, { order: next.length + 1 });
    next.push(added);
    return next;
  }

  function buildDefaultItem(section) {
    const item = {};
    for (const field of SECTION_SPECS[section].fields) {
      if (field.type === "boolean") {
        item[field.name] = false;
      } else if (field.type === "lines") {
        item[field.name] = [];
      } else {
        item[field.name] = "";
      }
    }
    return item;
  }

  function textToLines(rawText) {
    return String(rawText || "")
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line.length > 0);
  }

  function linesToText(lines) {
    if (!Array.isArray(lines)) {
      return "";
    }
    return lines.filter((line) => typeof line === "string").join("\n");
  }

  function buildSubmitPayload(options) {
    const basePayload = options.basePayload || {};
    const scalars = options.scalars || {};
    const sectionItems = options.sectionItems || {};

    const result = Object.assign({}, basePayload);
    result.personal = Object.assign({}, basePayload.personal || {}, scalars.personal || {});
    result.contact = Object.assign({}, basePayload.contact || {}, scalars.contact || {});
    result.summary = typeof scalars.summary === "string" ? scalars.summary : "";

    for (const section of ITEM_SECTION_NAMES) {
      const items = Array.isArray(sectionItems[section]) ? sectionItems[section] : [];
      result[section] = items.map((item, index) => Object.assign({}, item, { order: index + 1 }));
    }

    return result;
  }

  /* ------------------------- Funciones DOM ------------------------- */

  function createEl(tagName, className, text) {
    const element = document.createElement(tagName);
    if (className) {
      element.className = className;
    }
    if (text !== undefined && text !== null) {
      element.textContent = String(text);
    }
    return element;
  }

  function readScalarValue(input) {
    if (input.type === "checkbox") {
      return input.checked;
    }
    return input.value;
  }

  function readScalars(form) {
    const scalars = {
      personal: {},
      contact: {},
      summary: "",
    };
    const inputs = form.querySelectorAll("[data-editor-field]");
    for (const input of inputs) {
      const fieldName = input.getAttribute("data-editor-field");
      if (fieldName === "summary") {
        scalars.summary = input.value;
        continue;
      }
      const separatorIndex = fieldName.indexOf(".");
      if (separatorIndex === -1) {
        continue;
      }
      const section = fieldName.slice(0, separatorIndex);
      const field = fieldName.slice(separatorIndex + 1);
      if (!SCALAR_FIELDS[section] || !SCALAR_FIELDS[section].includes(field)) {
        continue;
      }
      if (section === "contact" && field === "links") {
        scalars.contact.links = textToLines(input.value);
      } else {
        scalars[section][field] = input.value;
      }
    }
    return scalars;
  }

  function collectPayload(state, form) {
    return buildSubmitPayload({
      basePayload: state.base,
      scalars: readScalars(form),
      sectionItems: state.items,
    });
  }

  function renderFatalError(root, message) {
    const container = createEl("div", "structured-warning");
    container.setAttribute("role", "alert");
    container.textContent = message;
    root.replaceChildren(container);
  }

  function createFieldControl(field, value) {
    let control;
    if (field.type === "boolean") {
      control = createEl("input");
      control.type = "checkbox";
      control.checked = value === true;
    } else if (field.type === "textarea" || field.type === "lines") {
      control = createEl("textarea");
      if (field.rows) {
        control.rows = field.rows;
      }
      control.value = field.type === "lines" ? linesToText(value) : typeof value === "string" ? value : "";
    } else {
      control = createEl("input");
      control.type = "text";
      control.value = typeof value === "string" ? value : "";
    }
    if (field.maxlength && field.type !== "boolean") {
      control.setAttribute("maxlength", String(field.maxlength));
    }
    control.setAttribute("data-item-field", field.name);
    return control;
  }

  function createItemCard(section, item, position, totalItems) {
    const spec = SECTION_SPECS[section];
    const card = createEl("article", "structured-item-card");
    card.setAttribute("data-structured-item", section);
    card.setAttribute("data-item-position", String(position));

    const head = createEl("div", "structured-item-head");
    head.appendChild(createEl("span", "structured-item-index", `${spec.itemLabel} ${position + 1}`));

    const actions = createEl("span", "structured-item-actions");
    const moveUp = createEl("button", "button small", "Subir");
    moveUp.type = "button";
    moveUp.setAttribute("data-move-up", "");
    moveUp.setAttribute("aria-label", `Subir ${spec.itemLabel.toLowerCase()} ${position + 1}`);
    moveUp.disabled = position === 0;
    const moveDown = createEl("button", "button small", "Bajar");
    moveDown.type = "button";
    moveDown.setAttribute("data-move-down", "");
    moveDown.setAttribute("aria-label", `Bajar ${spec.itemLabel.toLowerCase()} ${position + 1}`);
    moveDown.disabled = position === totalItems - 1;
    const removeButton = createEl("button", "button small danger", "Quitar");
    removeButton.type = "button";
    removeButton.setAttribute("data-remove-item", "");
    removeButton.setAttribute("aria-label", `Quitar ${spec.itemLabel.toLowerCase()} ${position + 1}`);
    actions.append(moveUp, moveDown, removeButton);
    head.appendChild(actions);
    card.appendChild(head);

    const fieldsContainer = createEl("div", "structured-item-fields");
    for (const field of spec.fields) {
      const label = createEl("label", null, `${field.label}${field.type === "boolean" ? "" : ""}`);
      const control = createFieldControl(field, item[field.name]);
      label.appendChild(control);
      fieldsContainer.appendChild(label);
    }
    card.appendChild(fieldsContainer);
    return card;
  }

  function renderSection(state, section, sectionElement) {
    const items = state.items[section];
    const itemsRoot = sectionElement.querySelector(`[data-items-root="${section}"]`);
    if (!itemsRoot) {
      return;
    }
    itemsRoot.replaceChildren();
    items.forEach((item, index) => {
      itemsRoot.appendChild(createItemCard(section, item, index, items.length));
    });

    const addButton = sectionElement.querySelector(`[data-add-item="${section}"]`);
    if (addButton) {
      addButton.disabled = items.length >= SECTION_SPECS[section].maxItems;
    }
  }

  function renderAllSections(state, root) {
    for (const section of ITEM_SECTION_NAMES) {
      const sectionElement = root.querySelector(`[data-structured-section="${section}"]`);
      if (sectionElement) {
        renderSection(state, section, sectionElement);
      }
    }
  }

  function findCardContext(target) {
    const card = target.closest("[data-structured-item]");
    if (!card) {
      return null;
    }
    const section = card.getAttribute("data-structured-item");
    const position = parseInt(card.getAttribute("data-item-position"), 10);
    if (!stateHasSection(section) || Number.isNaN(position)) {
      return null;
    }
    return { section, position };
  }

  function stateHasSection(section) {
    return Object.prototype.hasOwnProperty.call(SECTION_SPECS, section);
  }

  function mountEditor(options) {
    const root = options.root;
    const form = options.form;
    const payloadInput = options.payloadInput;

    const parsed = parseBootstrapPayload(options.bootstrapScript.textContent);
    if (parsed.error) {
      renderFatalError(root, parsed.error);
      root.dataset.structuredEditorReady = "true";
      return null;
    }

    const state = {
      base: normalizeBootstrapPayload(parsed.payload),
      items: {},
    };
    for (const section of ITEM_SECTION_NAMES) {
      state.items[section] = itemsFromSection(state.base, section);
    }

    root.addEventListener("click", (event) => {
      const target = event.target;
      const addButton = target.closest("[data-add-item]");
      if (addButton) {
        const section = addButton.getAttribute("data-add-item");
        if (stateHasSection(section)) {
          state.items[section] = appendItem(state.items[section], buildDefaultItem(section));
          const sectionElement = root.querySelector(`[data-structured-section="${section}"]`);
          renderSection(state, section, sectionElement);
          const firstInput = sectionElement.querySelector(
            `[data-structured-item="${section}"][data-item-position="${state.items[section].length - 1}"] [data-item-field]`,
          );
          if (firstInput) {
            firstInput.focus();
          }
        }
        return;
      }

      const context = findCardContext(target);
      if (!context) {
        return;
      }

      if (target.closest("[data-move-up]")) {
        state.items[context.section] = moveItem(state.items[context.section], context.position, -1);
        renderSection(state, context.section, target.closest("[data-structured-section]"));
        return;
      }
      if (target.closest("[data-move-down]")) {
        state.items[context.section] = moveItem(state.items[context.section], context.position, 1);
        renderSection(state, context.section, target.closest("[data-structured-section]"));
        return;
      }
      if (target.closest("[data-remove-item]")) {
        state.items[context.section] = removeItem(state.items[context.section], context.position);
        renderSection(state, context.section, target.closest("[data-structured-section]"));
      }
    });

    root.addEventListener("input", (event) => {
      const target = event.target;
      if (!target.matches("[data-item-field]")) {
        return;
      }
      const context = findCardContext(target);
      if (!context) {
        return;
      }
      const item = state.items[context.section][context.position];
      if (!item) {
        return;
      }
      const fieldName = target.getAttribute("data-item-field");
      const fieldSpec = SECTION_SPECS[context.section].fields.find(
        (candidate) => candidate.name === fieldName,
      );
      if (!fieldSpec) {
        return;
      }
      if (fieldSpec.type === "boolean") {
        item[fieldName] = target.checked;
      } else if (fieldSpec.type === "lines") {
        item[fieldName] = textToLines(target.value);
      } else {
        item[fieldName] = target.value;
      }
    });

    form.addEventListener("submit", () => {
      payloadInput.value = JSON.stringify(collectPayload(state, form));
    });

    renderAllSections(state, root);
    root.dataset.structuredEditorReady = "true";
    return {
      collectPayload: () => collectPayload(state, form),
    };
  }

  function initFromDocument() {
    const root = document.getElementById("structured-editor-root");
    if (!root) {
      return;
    }
    const form = document.querySelector("form[data-structured-form]");
    const bootstrapScript = document.getElementById("structured-editor-bootstrap");
    const payloadInput = document.getElementById("structured-payload-input");
    if (!form || !bootstrapScript || !payloadInput) {
      return;
    }
    const controller = mountEditor({ root, form, bootstrapScript, payloadInput });
    if (controller) {
      root.__structuredEditorController = controller;
    }
  }

  if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", initFromDocument);
    } else {
      initFromDocument();
    }
  }

  return {
    SCHEMA_VERSION,
    SCALAR_FIELDS,
    SECTION_SPECS,
    buildEmptyPayload,
    parseBootstrapPayload,
    normalizeBootstrapPayload,
    itemsFromSection,
    renumberItems,
    moveItem,
    removeItem,
    appendItem,
    buildDefaultItem,
    textToLines,
    linesToText,
    buildSubmitPayload,
    readScalars,
    collectPayload,
    mountEditor,
    initFromDocument,
  };
});
