from odoo import models, fields, api
from odoo.exceptions import UserError

class ClientWeekInvoiceWizard(models.TransientModel):
    _name = 'client.week.invoice.wizard'
    _description = 'Wizard pour imprimer la facture hebdomadaire du client'

    client_id = fields.Many2one(
        'kal3iya.client',
        string='Client',
        required=True,
        readonly=True,
    )
    week = fields.Selection(selection='_get_selection_weeks', string='Semaine', required=True)

    @api.model
    def _get_selection_weeks(self):
        """Return all unique weeks found in the system for validation."""
        weeks = set()
        
        # Helper to format date to week
        def date_to_week(d):
            return d.strftime("%Y-W%W") if d else False
            
        # Collect weeks from all records
        # Use sudo to ensure we see all weeks regardless of permissions
        env = self.env
        
        # Sorties
        sorties = env['kal3iya.sortie'].sudo().search([('week', '!=', False)])
        weeks.update(sorties.mapped('week'))
        
        # Retours
        retours = env['kal3iya.retour'].sudo().search([('week', '!=', False)])
        weeks.update(retours.mapped('week'))
        
        # Avances
        avances = env['kal3iya.avance'].sudo().search([('date_paid', '!=', False)])
        for date in avances.mapped('date_paid'):
            weeks.add(date_to_week(date))
            
        # Sort desc
        sorted_weeks = sorted(weeks, reverse=True)
        
        selection = []
        for w in sorted_weeks:
            # "2025-W47" -> "Semaine 47 (2025)"
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
        """Initialize wizard with default client and most recent week."""
        res = super().default_get(fields_list)

        client_id = self.env.context.get('active_id')
        if not client_id:
            return res

        res['client_id'] = client_id
        client = self.env['kal3iya.client'].browse(client_id)

        # Calculate weeks SPECIFIC to this client to set a smart default
        client_weeks = set()
        
        for s in client.sortie_ids:
            if s.week: client_weeks.add(s.week)
            
        for r in client.retour_ids:
            if getattr(r, 'week', False): client_weeks.add(r.week)
            
        for a in client.avances:
            if a.date_paid:
                client_weeks.add(a.date_paid.strftime("%Y-W%W"))
                
        sorted_client_weeks = sorted(client_weeks, reverse=True)

        # Set default to the most recent week for this client
        if sorted_client_weeks:
            res['week'] = sorted_client_weeks[0]
            
        return res

    def action_print_invoice(self):
        """Génère le PDF pour la semaine choisie."""
        self.ensure_one()

        if not self.week:
            raise UserError("Veuillez sélectionner une semaine.")

        # on garde ton action de rapport telle quelle
        return self.env.ref(
            'kal3iya.action_report_client_week_invoice'
        ).report_action(self)
