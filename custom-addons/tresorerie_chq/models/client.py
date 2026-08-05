from odoo import models, fields

class TresorerieChqClientAlias(models.Model):
    _name = 'tresorerie_chq.client.alias'
    _description = 'Alias Client'

    name = fields.Char(string='Alias', required=True)
    client_id = fields.Many2one('tresorerie_chq.client', string='Client', required=True, ondelete='cascade')

class TresorerieChqClient(models.Model):
    _name = 'tresorerie_chq.client'
    _description = 'Client (Trésorerie Chèques & Effets)'

    name = fields.Char(string='Nom', required=True)
    cin = fields.Char(string='CIN')
    phone = fields.Char(string='Téléphone')
    email = fields.Char(string='E-mail')
    address = fields.Text(string='Adresse')
    allow_no_date = fields.Boolean(
        string="Autoriser sans échéance",
        default=False,
        help="Si coché, permet d'enregistrer des chèques ou des effets sans date d'échéance pour ce client."
    )
    
    paiement_ids = fields.One2many('tresorerie_chq.paiement', 'client_id', string='Paiements')
    alias_ids = fields.One2many('tresorerie_chq.client.alias', 'client_id', string='Alias')
    
    cheque_ids = fields.One2many('tresorerie_chq.cheque', 'client_id', string='Chèques')
    effet_ids = fields.One2many('tresorerie_chq.effet', 'client_id', string='Effets')

    def get_all_cheques(self):
        self.ensure_one()
        return self.env['tresorerie_chq.cheque'].search([('client_id', '=', self.id)], order='check_date asc, id desc')

    def get_all_effets(self):
        self.ensure_one()
        return self.env['tresorerie_chq.effet'].search([('client_id', '=', self.id)], order='check_date asc, id desc')

