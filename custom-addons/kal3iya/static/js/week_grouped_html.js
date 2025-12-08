/** @odoo-module */

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { Component, xml } from "@odoo/owl";

export class WeekGroupedHtml extends Component {
    setup() {
        this.action = useService("action");
    }

    onClick(ev) {
        const target = ev.target.closest(".js_open_week_wizard");
        if (target) {
            ev.preventDefault();
            ev.stopPropagation();
            // dataset attributes are strings, parse if needed, but passing ID as is usually works for context
            const activeId = parseInt(target.dataset.activeId);

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

WeekGroupedHtml.template = xml`
    <div class="o_field_html" t-on-click="onClick" t-out="props.record.data[props.name] || ''" />
`;

WeekGroupedHtml.props = {
    ...standardFieldProps,
};

registry.category("fields").add("week_grouped_html", {
    component: WeekGroupedHtml,
    supportedTypes: ["html"],
});
