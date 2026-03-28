from odoo import models, fields, api
from odoo.exceptions import UserError

class CasaClientInvoiceWizard(models.TransientModel):
    _name = 'casa.client.invoice.wizard'
    _description = 'Wizard pour imprimer la facture hebdomadaire du client Casa'

    client_id = fields.Many2one(
        'casa.client',
        string='Client',
        required=True,
        readonly=True,
    )
    week = fields.Selection(selection='_get_selection_weeks', string='Semaine', required=True)

    @api.model
    def _get_selection_weeks(self):
        """Return all unique weeks found in the system for validation."""
        weeks = set()
        
        def date_to_week(d):
            return d.strftime("%Y-W%W") if d else False
            
        env = self.env
        
        # Sorties
        exits = env['casa.stock.exit'].sudo().search([('week', '!=', False)])
        weeks.update(exits.mapped('week'))
        
        # Avances
        avances = env['casa.client.advance'].sudo().search([('date', '!=', False)])
        for date in avances.mapped('date'):
            weeks.add(date_to_week(date))
            
        # Impayés
        impayes = env['casa.client.unpaid'].sudo().search([('date', '!=', False)])
        for date in impayes.mapped('date'):
            weeks.add(date_to_week(date))
            
        sorted_weeks = sorted(weeks, reverse=True)
        
        selection = []
        for w in sorted_weeks:
            parts = w.split('-W')
            if len(parts) == 2:
                year, week_num = parts
                label = f"Semaine {week_num} ({year})"
                selection.append((w, label))
            else:
                selection.append((w, w))
                
        return selection

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        client_id = self.env.context.get('active_id')
        if not client_id:
            return res

        res['client_id'] = client_id
        client = self.env['casa.client'].browse(client_id)

        client_weeks = set()
        for s in client.exit_ids:
            if s.week: client_weeks.add(s.week)
        for a in client.advance_ids:
            if a.date: client_weeks.add(a.date.strftime("%Y-W%W"))
        for u in client.unpaid_ids:
            if u.date: client_weeks.add(u.date.strftime("%Y-W%W"))
                
        sorted_client_weeks = sorted(client_weeks, reverse=True)
        if sorted_client_weeks:
            res['week'] = sorted_client_weeks[0]
            
        return res

    def format_amount(self, value):
        """Format a number with plain space as thousand separator."""
        try:
            return '{:,.2f}'.format(float(value or 0)).replace(',', ' ')
        except (ValueError, TypeError):
            return '0.00'

    def action_print_invoice(self):
        """Génère le PDF pour la semaine choisie."""
        self.ensure_one()
        if not self.week:
            raise UserError("Veuillez sélectionner une semaine.")

        return self.env.ref(
            'casa_stock.action_report_casa_client_invoice'
        ).report_action(self)
