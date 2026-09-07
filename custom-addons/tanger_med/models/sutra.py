from odoo import models, fields, api

class SutraDossier(models.Model):
    _name = 'sutra.dossier'
    _description = 'Dossier de Transit SUTRA'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Nom', required=True, tracking=True)
    logistics_id = fields.Many2one('logistique.entry', string='Dossier Logistique', tracking=True)
    facture_ids = fields.One2many('sutra.facture', 'sutra_id', string='Factures')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') and vals.get('logistics_id'):
                log_entry = self.env['logistique.entry'].browse(vals['logistics_id'])
                if log_entry.exists():
                    vals['name'] = f'SUTRA - {log_entry.display_name}'
        return super(SutraDossier, self).create(vals_list)


class SutraFacture(models.Model):
    _name = 'sutra.facture'
    _description = 'Facture SUTRA'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    sutra_id = fields.Many2one('sutra.dossier', string='Dossier SUTRA', ondelete='cascade', required=True)
    name = fields.Char(string='Numéro de Facture', required=True, tracking=True)
    date = fields.Date(string='Date', tracking=True)
    amount = fields.Float(string='Montant TTC', tracking=True)
    state = fields.Selection([
        ('non_paye', 'Non Payé'),
        ('paye', 'Payé')
    ], string='Statut Paiement', default='non_paye', tracking=True)
    pdf_file = fields.Binary(string='Facture (PDF)', attachment=True)
    pdf_filename = fields.Char(string='Nom du fichier PDF')


