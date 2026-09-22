from odoo import models, fields, api

class PlanificationDossier(models.Model):
    _name = 'achat.planification.dossier'
    _description = 'Dossier Acheté'
    _order = 'eta_date desc, id desc'

    bl_number = fields.Char(string='Numéro de BL', required=True)
    article_id = fields.Many2one('achat.article', string='Article')
    invoice_number = fields.Char(string='Invoice Num')
    montant_total = fields.Monetary(string='Montant', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Devise', default=lambda self: self.env.company.currency_id)
    eta_date = fields.Date(string='ETA (Date d\'arrivée prévue)')
    container_names = fields.Char(string='Numéros de Conteneurs', help='Séparés par des virgules')
    fournisseur_id = fields.Many2one('logistique.supplier', string='Fournisseur')
    state = fields.Selection([
        ('charge', 'Chargé'),
        ('arrive', 'Arrivé au port'),
        ('decharge', 'Déchargé'),
        ('paye', 'Payé')
    ], string='Statut', default='charge', tracking=True)
    
    # Pour le groupement par semaine
    week_number = fields.Char(string='Semaine ETA', compute='_compute_week_number', store=True)

    @api.depends('eta_date')
    def _compute_week_number(self):
        for rec in self:
            if rec.eta_date:
                # Format: YYYY-Www (e.g. 2024-W12)
                rec.week_number = rec.eta_date.strftime('%Y-W%V')
            else:
                rec.week_number = False

    def name_get(self):
        result = []
        for rec in self:
            name = f"{rec.bl_number} - {rec.fournisseur_id.name if rec.fournisseur_id else 'Sans Fournisseur'}"
            result.append((rec.id, name))
        return result
