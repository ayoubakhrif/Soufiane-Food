/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { TitleService } from "@web/core/browser/title_service";

patch(TitleService.prototype, {
    setParts(parts) {
        // Call original behavior
        this._super(parts);

        // Replace Odoo branding in browser title
        if (document.title && document.title.includes("Odoo")) {
            document.title = document.title.replace(/Odoo/g, "Gestia");
        }
    },
});
