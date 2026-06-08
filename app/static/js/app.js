const THEME_STORAGE_KEY = "cv-theme";

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;

  const toggleLabel = document.querySelector("[data-theme-toggle-label]");
  if (toggleLabel) {
    toggleLabel.textContent = theme === "dark" ? "Light mode" : "Dark mode";
  }
}

function initializeThemeToggle() {
  const toggle = document.querySelector("[data-theme-toggle]");
  if (!toggle) {
    return;
  }

  const currentTheme = document.documentElement.dataset.theme || "light";
  applyTheme(currentTheme);

  toggle.addEventListener("click", () => {
    const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
    applyTheme(nextTheme);
  });
}

function initializeActiveNavigation() {
  const currentPath = window.location.pathname;
  const links = document.querySelectorAll("[data-nav-path]");

  links.forEach((link) => {
    const navPath = link.getAttribute("data-nav-path");
    const isDashboardLink = navPath === "/";
    const isActive = isDashboardLink ? currentPath === "/" : currentPath.startsWith(navPath);
    link.classList.toggle("is-active", isActive);
  });
}

function closeActionMenus() {
  document.querySelectorAll("[data-action-menu][open]").forEach((menu) => {
    menu.removeAttribute("open");
  });
}

function updateActionMenuState(menu) {
  const toggle = menu.querySelector("[data-action-menu-toggle]");
  if (toggle) {
    toggle.setAttribute("aria-expanded", menu.hasAttribute("open") ? "true" : "false");
  }
}

function initializeActionMenus() {
  const menus = document.querySelectorAll("[data-action-menu]");
  if (!menus.length) {
    return;
  }

  menus.forEach((menu) => {
    updateActionMenuState(menu);
    menu.addEventListener("toggle", () => updateActionMenuState(menu));
  });

  document.addEventListener("click", (event) => {
    const clickedMenu = event.target.closest("[data-action-menu]");
    menus.forEach((menu) => {
      if (menu !== clickedMenu && menu.hasAttribute("open")) {
        menu.removeAttribute("open");
      }
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeActionMenus();
    }
  });
}

function closeAtsModal() {
  const overlay = document.querySelector("[data-ats-overlay]");
  if (!overlay) {
    return;
  }

  overlay.remove();
  document.body.classList.remove("modal-open");
}

function closeConfirmModal() {
  const overlay = document.querySelector("[data-confirm-overlay]");
  if (!overlay) {
    return;
  }

  overlay.remove();
  document.body.classList.remove("modal-open");
}

function openConfirmModal({ title, message, confirmLabel, onConfirm }) {
  closeConfirmModal();

  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.dataset.confirmOverlay = "true";

  const backdrop = document.createElement("div");
  backdrop.className = "modal-backdrop";
  backdrop.dataset.confirmClose = "true";

  const frame = document.createElement("div");
  frame.className = "modal-frame";

  const dialog = document.createElement("div");
  dialog.className = "confirm-dialog-card";
  dialog.setAttribute("role", "dialog");
  dialog.setAttribute("aria-modal", "true");
  dialog.setAttribute("aria-labelledby", "confirm-dialog-title");
  dialog.setAttribute("tabindex", "-1");

  const dialogHead = document.createElement("div");
  dialogHead.className = "confirm-dialog-head";

  const titleGroup = document.createElement("div");

  const eyebrow = document.createElement("p");
  eyebrow.className = "eyebrow";
  eyebrow.textContent = "Confirmacion";

  const titleElement = document.createElement("h2");
  titleElement.id = "confirm-dialog-title";
  titleElement.textContent = title;

  titleGroup.append(eyebrow, titleElement);

  const closeButton = document.createElement("button");
  closeButton.className = "button small";
  closeButton.type = "button";
  closeButton.dataset.confirmClose = "true";
  closeButton.textContent = "Cerrar";

  dialogHead.append(titleGroup, closeButton);

  const messageElement = document.createElement("p");
  messageElement.className = "section-copy";
  messageElement.textContent = message;

  const actions = document.createElement("div");
  actions.className = "confirm-dialog-actions";

  const cancelButton = document.createElement("button");
  cancelButton.className = "button";
  cancelButton.type = "button";
  cancelButton.dataset.confirmClose = "true";
  cancelButton.textContent = "Cancelar";

  const acceptButton = document.createElement("button");
  acceptButton.className = "button primary";
  acceptButton.type = "button";
  acceptButton.dataset.confirmAccept = "true";
  acceptButton.textContent = confirmLabel;

  actions.append(cancelButton, acceptButton);
  dialog.append(dialogHead, messageElement, actions);
  frame.appendChild(dialog);
  overlay.append(backdrop, frame);

  const root = document.getElementById("app-modal-root") || document.body;
  root.appendChild(overlay);
  document.body.classList.add("modal-open");

  dialog.focus();

  overlay.querySelector("[data-confirm-accept]")?.addEventListener("click", () => {
    closeConfirmModal();
    onConfirm();
  });
}

async function openAtsModal(trigger) {
  const modalUrl = trigger.getAttribute("data-ats-modal-url");
  const fallbackUrl = trigger.getAttribute("href");
  if (!modalUrl) {
    window.location.href = fallbackUrl;
    return;
  }

  try {
    const response = await fetch(modalUrl, {
      headers: {
        "X-Requested-With": "fetch",
      },
    });

    if (!response.ok) {
      throw new Error(`ATS modal request failed: ${response.status}`);
    }

    const html = await response.text();
    closeAtsModal();

    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    overlay.dataset.atsOverlay = "true";
    overlay.innerHTML = `
      <div class="modal-backdrop" data-ats-close></div>
      <div class="modal-frame">${html}</div>
    `;

    const root = document.getElementById("app-modal-root") || document.body;
    root.appendChild(overlay);
    document.body.classList.add("modal-open");

    const dialog = overlay.querySelector("[data-ats-modal]");
    if (dialog) {
      dialog.focus();
    }
  } catch (error) {
    window.location.href = fallbackUrl;
  }
}

function initializeAtsModal() {
  document.addEventListener("click", (event) => {
    const openTrigger = event.target.closest("[data-ats-open]");
    if (openTrigger) {
      event.preventDefault();
      closeActionMenus();
      openAtsModal(openTrigger);
      return;
    }

    const closeTrigger = event.target.closest("[data-ats-close]");
    if (closeTrigger) {
      event.preventDefault();
      closeAtsModal();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeAtsModal();
    }
  });
}

function initializeConfirmSubmit() {
  document.addEventListener("submit", (event) => {
    const form = event.target.closest("[data-confirm-submit]");
    if (!form || form.dataset.confirmed === "true") {
      return;
    }

    event.preventDefault();
    closeActionMenus();

    openConfirmModal({
      title: form.getAttribute("data-confirm-title") || "Confirmar accion",
      message: form.getAttribute("data-confirm-message") || "Confirma la accion para continuar.",
      confirmLabel: form.getAttribute("data-confirm-label") || "Confirmar",
      onConfirm: () => {
        form.dataset.confirmed = "true";
        HTMLFormElement.prototype.submit.call(form);
      },
    });
  });

  document.addEventListener("click", (event) => {
    if (event.target.closest("[data-confirm-close]")) {
      event.preventDefault();
      closeConfirmModal();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeConfirmModal();
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initializeThemeToggle();
  initializeActiveNavigation();
  initializeActionMenus();
  initializeAtsModal();
  initializeConfirmSubmit();
});
