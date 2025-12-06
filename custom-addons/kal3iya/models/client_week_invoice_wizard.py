from odoo import models, fields, api
from odoo.exceptions import UserError

class ClientWeekInvoiceWizard(models.TransientModel):
    _name = 'client.week.invoice.wizard'
    _description = 'Wizard pour imprimer la facture hebdomadaire du client'

    client_id = fields.Many2one('kal3iya.client', string='Client', required=True, readonly=True)
    week = fields.Selection(selection='_get_available_weeks', string='Semaine', required=True)

    @api.model
    def default_get(self, fields_list):
        """Initialiser le wizard avec le client actif"""
        res = super().default_get(fields_list)
        if self.env.context.get('active_id'):
            res['client_id'] = self.env.context.get('active_id')
        return res

    def _get_available_weeks(self):
        """Retourne toutes les semaines où le client a eu une activité"""
        # Si le wizard n'est pas encore créé (premier appel), utiliser le contexte
        client_id = self.client_id.id if self.client_id else self.env.context.get('active_id')
        
        if not client_id:
            return []
        
        client = self.env['kal3iya.client'].browse(client_id)
        weeks = set()
        
        # Récupérer les semaines des sorties
        for sortie in client.sortie_ids:
            if sortie.week:
                weeks.add(sortie.week)
        
        # Récupérer les semaines des retours
        for retour in client.retour_ids:
            if hasattr(retour, 'week') and retour.week:
                weeks.add(retour.week)
        
        # Récupérer les semaines des avances
        for avance in client.avances:
            if avance.date_paid:
                week_str = avance.date_paid.strftime("%Y-W%W")
                weeks.add(week_str)
        
        # Trier par ordre décroissant (plus récent en premier)
        sorted_weeks = sorted(weeks, reverse=True)
        
        # Formater pour l'affichage : "Semaine 48 (2025)"
        result = []
        for week in sorted_weeks:
            # week format: "2025-W48"
            parts = week.split('-W')
            if len(parts) == 2:
                year, week_num = parts[0], parts[1]
                label = f"Semaine {week_num} ({year})"
                result.append((week, label))
        
        return result

    def action_print_invoice(self):
        """Génère et télécharge le PDF de la facture hebdomadaire"""
        self.ensure_one()
        
        if not self.week:
            raise UserError("Veuillez sélectionner une semaine.")
        
        # Appeler le rapport QWeb
        return self.env.ref('kal3iya.action_report_client_week_invoice').report_action(self)