from odoo import models, fields, api
from odoo.exceptions import UserError

class ClientWeekInvoiceWizard(models.TransientModel):
    _name = 'client.week.invoice.wizard'
    _description = 'Wizard pour imprimer la facture hebdomadaire du client'

    client_id = fields.Many2one('kal3iya.client', string='Client', required=True, readonly=True)
    week = fields.Selection([], string='Semaine', required=True)

    @api.model
    def default_get(self, fields_list):
        """Initialiser automatiquement le client"""
        res = super().default_get(fields_list)
        if self.env.context.get('active_id'):
            res['client_id'] = self.env.context.get('active_id')
        return res

    @api.onchange('client_id')
    def _onchange_client_id(self):
        """Recharge dynamiquement la liste des semaines disponibles"""
        if not self.client_id:
            self.week = False
            return

        weeks = set()

        # Sorties
        for s in self.client_id.sortie_ids:
            if s.week:
                weeks.add(s.week)

        # Retours
        for r in self.client_id.retour_ids:
            if hasattr(r, 'week') and r.week:
                weeks.add(r.week)

        # Avances
        for a in self.client_id.avances:
            if a.date_paid:
                weeks.add(a.date_paid.strftime("%Y-W%W"))

        # Trier
        sorted_weeks = sorted(weeks, reverse=True)

        # Construire la liste finale
        selection = []
        for week in sorted_weeks:
            year, week_num = week.split('-W')
            label = f"Semaine {week_num} ({year})"
            selection.append((week, label))

        # 🔥 appliquer dynamiquement les valeurs possibles :
        self._fields['week'].selection = selection
        self.week = False   # réinitialiser l'ancien choix

    def action_print_invoice(self):
        self.ensure_one()

        if not self.week:
            raise UserError("Veuillez sélectionner une semaine.")

        return self.env.ref('kal3iya.action_report_client_week_invoice').report_action(self)
