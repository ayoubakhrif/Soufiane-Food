/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { TitleService } from "@web/core/browser/title_service";

patch(TitleService.prototype, {
    /**
     * Override setParts to replace Odoo with Gestia in browser title
     */
    setParts(parts) {
        // Call the original method
        this._super(...arguments);
        // Replace "Odoo" with "Gestia" in the document title
        if (document.title.includes("Odoo")) {
            document.title = document.title.replace(/Odoo/g, "Gestia");
        }
    },
});
