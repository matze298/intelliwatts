document.addEventListener("DOMContentLoaded", () => {
    const themeStylesheet = document.getElementById("theme-stylesheet");
    const themeSwitcher = document.getElementById("theme-switcher");

    if (!themeStylesheet || !themeSwitcher) {
        return;
    }

    const themes = {
        pro: "/static/tailwind-pro.css",
        retro: "/static/tailwind-retro.css",
        minimal: "/static/tailwind-minimal.css",
    };

    const applyTheme = (theme) => {
        themeStylesheet.href = themes[theme] || themes.pro;
    };

    const savedTheme = localStorage.getItem("selectedTheme") || "pro";
    themeSwitcher.value = savedTheme;
    applyTheme(savedTheme);

    themeSwitcher.addEventListener("change", (event) => {
        const selectedTheme = event.target.value;
        localStorage.setItem("selectedTheme", selectedTheme);
        applyTheme(selectedTheme);
    });
});
