/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, xml } from "@odoo/owl";

export class WeekGroupedHtml extends Component {
    setup() {
        this.action = useService("action");
    }

    onClick(ev) {
        // Find closest button in case user clicked icon inside span
        const target = ev.target.closest(".js_open_week_wizard");
        if (target) {
            ev.preventDefault();
            ev.stopPropagation();

            // Safe parsing of ID
            const activeIdStr = target.dataset.activeId;
            if (activeIdStr) {
                const activeId = parseInt(activeIdStr);

                this.action.doAction({
                    type: 'ir.actions.act_window',
                    name: 'Modifier la semaine',
                    res_model: 'kal3iya.week.update.wizard',
                    view_mode: 'form',
                    views: [[false, 'form']],
                    target: 'new',
                    context: {
                        active_id: activeId,
                        active_model: 'kal3iyasortie'
                    }
                });
            }
        }
    }
}

WeekGroupedHtml.template = xml`
    <div class="o_field_html" t-on-click="onClick" t-out="props.record.data[props.name] || ''" />
`;

// Minimal props definition to avoid import issues
WeekGroupedHtml.props = {
    name: String,
    record: Object,
    readonly: { type: Boolean, optional: true },
};

registry.category("fields").add("week_grouped_html", {
    component: WeekGroupedHtml,
    supportedTypes: ["html"],
});
