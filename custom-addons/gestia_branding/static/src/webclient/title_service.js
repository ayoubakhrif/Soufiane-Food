/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { TitleService } from "@web/core/browser/title_service";

patch(TitleService.prototype, {
    /**
     * Override the _updateTitle method to replace "Odoo" with "Gestia"
     */
    _updateTitle() {
        super._updateTitle();
        // Replace "Odoo" with "Gestia" in the document title
        if (document.title.includes("Odoo")) {
            document.title = document.title.replace(/Odoo/g, "Gestia");
        }
    },
});
