/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, xml } from "@odoo/owl";

class FinanceLoader extends Component {
    setup() {
        const action = useService("action");
        onWillStart(async () => {
            // Redirect to the actual act_window
            await action.doAction("finance.data_cheque_action", {
                clearBreadcrumbs: true,
            });
        });
    }
}

FinanceLoader.template = xml`
<div class="o_finance_loader h-100 d-flex align-items-center justify-content-center">
    <i class="fa fa-circle-o-notch fa-spin fa-3x text-muted"/>
</div>`;

registry.category("actions").add("finance.app_entry", FinanceLoader);
