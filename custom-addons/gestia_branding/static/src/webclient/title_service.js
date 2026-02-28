/** @odoo-module **/

/**
 * Replace Odoo branding with Gestia
 * - Replace "Odoo" with "Gestia" in browser title
 * - Replace favicon with Gestia icon
 */

// ===== Title Replacement =====
// Replace current title immediately
if (document.title.includes("Odoo")) {
    document.title = document.title.replace(/Odoo/g, "Gestia");
}

// Watch for future title changes
const titleObserver = new MutationObserver(() => {
    if (document.title.includes("Odoo")) {
        document.title = document.title.replace(/Odoo/g, "Gestia");
    }
});

// Start observing the title element
const titleElement = document.querySelector('title');
if (titleElement) {
    titleObserver.observe(titleElement, {
        childList: true,
        characterData: true,
        subtree: true
    });
}

// ===== Favicon Replacement =====
function replaceOdooFavicon() {
    // Remove existing favicons
    const existingFavicons = document.querySelectorAll('link[rel="icon"], link[rel="shortcut icon"]');
    existingFavicons.forEach(link => link.remove());

    // Add Gestia favicon
    const link = document.createElement('link');
    link.rel = 'icon';
    link.type = 'image/png';
    link.href = '/gestia_branding/static/src/img/favicon.png';
    document.head.appendChild(link);
}

// Replace favicon when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', replaceOdooFavicon);
} else {
    replaceOdooFavicon();
}
