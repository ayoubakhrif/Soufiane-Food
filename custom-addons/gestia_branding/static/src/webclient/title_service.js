/** @odoo-module **/

/**
 * Simple and robust approach to replace "Odoo" with "Gestia" in browser title
 * Uses MutationObserver to watch for title changes
 */

// Replace current title immediately
if (document.title.includes("Odoo")) {
    document.title = document.title.replace(/Odoo/g, "Gestia");
}

// Watch for future title changes
const observer = new MutationObserver(() => {
    if (document.title.includes("Odoo")) {
        document.title = document.title.replace(/Odoo/g, "Gestia");
    }
});

// Start observing the title element
const titleElement = document.querySelector('title');
if (titleElement) {
    observer.observe(titleElement, {
        childList: true,
        characterData: true,
        subtree: true
    });
}
