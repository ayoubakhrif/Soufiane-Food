odoo.define('kal3iya.week_grouped_html', function (require) {
    "use strict";

    var FieldHtml = require('web.basic_fields').FieldHtml;
    var field_registry = require('web.field_registry');

    var WeekGroupedHtml = FieldHtml.extend({
        events: _.extend({}, FieldHtml.prototype.events, {
            'click .js_open_week_wizard': '_onOpenWeekWizard',
        }),

        _onOpenWeekWizard: function (ev) {
            ev.preventDefault();
            ev.stopPropagation();

            var $target = $(ev.currentTarget);
            var activeId = $target.data('active-id');

            // Ouvrir le wizard via do_action
            this.do_action({
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
        },
    });

    field_registry.add('week_grouped_html', WeekGroupedHtml);

    return WeekGroupedHtml;
});
