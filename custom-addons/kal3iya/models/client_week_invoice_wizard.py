from odoo import models, fields, api
from odoo.exceptions import UserError

class ClientWeekInvoiceWizard(models.TransientModel):
    _name = 'client.week.invoice.wizard'
    _description = 'Wizard pour imprimer la facture hebdomadaire du client'

    client_id = fields.Many2one('kal3iya.client', string='Client', required=True, readonly=True)
    week = fields.Selection(selection='_get_available_weeks', string='Semaine', required=True)

    @api.model
    def _get_available_weeks(self):
        """Retourne toutes les semaines où le client a eu une activité"""
        if not self.client_id:
            return []
        
        weeks = set()
        
        # Récupérer les semaines des sorties
        for sortie in self.client_id.sortie_ids:
            if sortie.week:
                weeks.add(sortie.week)
        
        # Récupérer les semaines des retours
        for retour in self.client_id.retour_ids:
            if hasattr(retour, 'week') and retour.week:
                weeks.add(retour.week)
        
        # Récupérer les semaines des avances
        for avance in self.client_id.avances:
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