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

document.addEventListener("DOMContentLoaded", () => {
  initializeThemeToggle();
  initializeActiveNavigation();
  initializeActionMenus();
  initializeAtsModal();
});
