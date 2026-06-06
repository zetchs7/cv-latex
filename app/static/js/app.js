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

document.addEventListener("DOMContentLoaded", () => {
  initializeThemeToggle();
  initializeActiveNavigation();
});
