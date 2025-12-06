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
    # on laisse la sélection vide ici, on la remplit dynamiquement
    week = fields.Selection([], string='Semaine', required=True)

    @api.model
    def default_get(self, fields_list):
        """Initialise le wizard avec le client actif + remplit la liste des semaines."""
        res = super().default_get(fields_list)

        client_id = self.env.context.get('active_id')
        if not client_id:
            return res

        res['client_id'] = client_id
        client = self.env['kal3iya.client'].browse(client_id)

        weeks = set()

        # Sorties
        for s in client.sortie_ids:
            if s.week:
                weeks.add(s.week)

        # Retours
        for r in client.retour_ids:
            if getattr(r, 'week', False):
                weeks.add(r.week)

        # Avances (date → semaine)
        for a in client.avances:
            if a.date_paid:
                weeks.add(a.date_paid.strftime("%Y-W%W"))

        # Tri décroissant
        sorted_weeks = sorted(weeks, reverse=True)

        selection = []
        for week in sorted_weeks:
            # "2025-W47" → "Semaine 47 (2025)"
            parts = week.split('-W')
            if len(parts) == 2:
                year, week_num = parts
                label = f"Semaine {week_num} ({year})"
                selection.append((week, label))

        # 👉 IMPORTANT : on injecte la sélection dans le champ AVANT la création du record
        self._fields['week'].selection = selection

        # optionnel : mettre par défaut la semaine la plus récente
        if selection:
            res.setdefault('week', selection[0][0])

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
