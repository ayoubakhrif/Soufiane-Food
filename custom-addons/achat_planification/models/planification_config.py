from odoo import models, fields, api

class PlanificationConfig(models.Model):
    _name = 'achat.planification.config'
    _description = 'Configuration Planification Achats'

    name = fields.Char(string='Nom', default='Configuration Budget', required=True)
    montant_hebdomadaire_max = fields.Monetary(string='Budget Hebdomadaire Max', required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Devise', default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', string='Société', default=lambda self: self.env.company)

    @api.model
    def create(self, vals):
        if self.search_count([]) >= 1:
            # S'assurer qu'il n'y a qu'un seul enregistrement de configuration
            return self.search([], limit=1)
        return super(PlanificationConfig, self).create(vals)
