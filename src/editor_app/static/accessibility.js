(function () {
    // 1. Immediate initialization to prevent theme flicker
    const savedTheme = localStorage.getItem("user-theme-preference");
    if (savedTheme) {
        document.documentElement.setAttribute("data-theme", savedTheme);
        console.log("Accessibility: Initialized with saved theme:", savedTheme);
    } else {
        const systemHighContrast = window.matchMedia("(prefers-contrast: more)").matches;
        const systemDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
        let theme = systemDark ? "futuristic-dark" : "light";
        if (systemHighContrast) {
            theme = systemDark ? "high-contrast-dark" : "high-contrast-light";
        }
        document.documentElement.setAttribute("data-theme", theme);
        console.log("Accessibility: Initialized with system theme:", theme);
    }

    // 2. Setup theme switching controls and initialize tooltips after DOM loads
    document.addEventListener("DOMContentLoaded", () => {
        // Theme switching dropdown handlers
        const themeDropdown = document.getElementById("themeDropdown");
        if (themeDropdown) {
            const parent = themeDropdown.parentElement;
            const dropdownMenu = parent ? parent.querySelector(".dropdown-menu") : null;
            if (dropdownMenu) {
                const themeButtons = dropdownMenu.querySelectorAll("[data-theme-value]");
                themeButtons.forEach(button => {
                    button.addEventListener("click", (e) => {
                        e.preventDefault();
                        const themeName = button.getAttribute("data-theme-value");
                        if (themeName) {
                            document.documentElement.setAttribute("data-theme", themeName);
                            localStorage.setItem("user-theme-preference", themeName);
                            console.log("Accessibility: Theme changed to:", themeName);
                        }
                    });
                });
            }
        }

        // Initialize Bootstrap tooltips globally if bootstrap is present
        if (typeof bootstrap !== "undefined" && bootstrap.Tooltip) {
            const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
            tooltipTriggerList.forEach(tooltipTriggerEl => {
                if (!bootstrap.Tooltip.getInstance(tooltipTriggerEl)) {
                    new bootstrap.Tooltip(tooltipTriggerEl);
                }
            });
        }
    });
})();
