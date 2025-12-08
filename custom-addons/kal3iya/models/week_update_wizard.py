from odoo import models, fields, api

class WeekUpdateWizard(models.TransientModel):
    _name = 'kal3iya.week.update.wizard'
    _description = 'Wizard pour modification hebdomadaire'

    def _default_week(self):
        active_id = self.env.context.get('active_id')
        if active_id:
            record = self.env['kal3iyasortie'].browse(active_id)
            return record.week
        return False

    week = fields.Char(string='Semaine', default=_default_week, readonly=True)
    line_ids = fields.One2many('kal3iya.week.update.line', 'wizard_id', string='Lignes')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if not active_id:
            return res
            
        record = self.env['kal3iyasortie'].browse(active_id)
        if not record.week:
            return res

        # Find all records for the same week
        domain = [('week', '=', record.week)]
        # Optional: Add other filters like same client if needed, but request implied "all orders of the week"
        # Assuming we want to filter by the same strict criterion as the view, but "all orders of the week" is broad.
        # Let's start with all orders of that week mostly likely. 
        # But wait, looking at user request: "modifier les tonnages et les prix de toutes les commandes de la semaine"
        # It's safer to probably just get everything for that week.
        
        all_records = self.env['kal3iyasortie'].search(domain)
        
        lines = []
        for rec in all_records:
            lines.append((0, 0, {
                'sortie_id': rec.id,
                'tonnage_final': rec.tonnage_final or rec.tonnage,
                'price_final': rec.selling_price_final or rec.selling_price,
            }))
        
        res['line_ids'] = lines
        res['week'] = record.week
        return res

    def action_save(self):
        self.ensure_one()
        for line in self.line_ids:
            line.sortie_id.write({
                'tonnage_final': line.tonnage_final,
                'selling_price_final': line.price_final,
            })
        return {'type': 'ir.actions.act_window_close'}


class WeekUpdateLine(models.TransientModel):
    _name = 'kal3iya.week.update.line'
    _description = 'Ligne de modification hebdomadaire'

    wizard_id = fields.Many2one('kal3iya.week.update.wizard', required=True)
    sortie_id = fields.Many2one('kal3iyasortie', string='Commande', required=True)
    
    # Related fields for display
    product_id = fields.Many2one(related='sortie_id.product_id', readonly=True)
    client_id = fields.Many2one(related='sortie_id.client_id', readonly=True)
    tonnage_initial = fields.Float(related='sortie_id.tonnage', string='Tonnage Init.', readonly=True)
    price_initial = fields.Float(related='sortie_id.selling_price', string='Prix Init.', readonly=True)
    
    # Editable fields
    tonnage_final = fields.Float(string='Tonnage Final')
    price_final = fields.Float(string='Prix Final')
