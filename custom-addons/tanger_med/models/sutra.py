from odoo import models, fields, api

class SutraConfigSte(models.Model):
    _name = 'sutra.config.ste'
    _description = 'Configuration SUTRA par Societe'

    ste_id = fields.Many2one('logistique.ste', string='Societe', required=True)
    amount = fields.Float(string='Montant par defaut', required=True)

    _sql_constraints = [
        ('ste_unique', 'unique(ste_id)', 'Une configuration existe deja pour cette societe !')
    ]

class SutraDossier(models.Model):
    _name = 'sutra.dossier'
    _description = 'Dossier de Transit SUTRA'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Nom', required=True, tracking=True)
    logistics_id = fields.Many2one('logistique.entry', string='Dossier Logistique', tracking=True)
    amount = fields.Float(string='Montant SUTRA', tracking=True)
    facture_ids = fields.One2many('sutra.facture', 'sutra_id', string='Factures')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('logistics_id'):
                log_entry = self.env['logistique.entry'].browse(vals['logistics_id'])
                if log_entry.exists():
                    if not vals.get('name'):
                        vals['name'] = f'SUTRA - {log_entry.display_name}'
                    if not vals.get('amount') and log_entry.ste_id:
                        config = self.env['sutra.config.ste'].search([('ste_id', '=', log_entry.ste_id.id)], limit=1)
                        if config:
                            vals['amount'] = config.amount
        return super(SutraDossier, self).create(vals_list)

class SutraFacture(models.Model):
    _name = 'sutra.facture'
    _description = 'Facture SUTRA'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    sutra_id = fields.Many2one('sutra.dossier', string='Dossier SUTRA', ondelete='cascade', required=True)
    name = fields.Char(string='Numero de Facture', required=True, tracking=True)
    date = fields.Date(string='Date', tracking=True)
    amount = fields.Float(string='Montant TTC', tracking=True)
    state = fields.Selection([
        ('non_paye', 'Non Paye'),
        ('encours', 'En Cours'),
        ('paye', 'Paye')
    ], string='Statut Paiement', default='non_paye', tracking=True)
    
    cheque_id = fields.Many2one('finance2.cheque', string='Cheque de Paiement', tracking=True)
    pdf_file = fields.Binary(string='Facture (PDF)', attachment=True)
    pdf_filename = fields.Char(string='Nom du fichier PDF')
