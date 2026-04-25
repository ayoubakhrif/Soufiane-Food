from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class SuiviOperation(models.Model):
    _name = 'suivi.operation'
    _description = 'Opération Suivi Transport'
    _order = 'date desc, id desc'

    name = fields.Char(string='Référence', required=True, copy=False, readonly=True, default='/')
    ville = fields.Selection([
        ('tanger', 'Tanger'),
        ('casa', 'Casa'),
        ('kenitra', 'Kenitra'),
        ('agadir', 'Agadir'),
        ('marrakech', 'Marrakech'),
    ], string='Ville', required=True)
    chauffeur_id = fields.Many2one('suivi.chauffeur', string='Chauffeur', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    lot = fields.Char(string='LOT')
    montant = fields.Float(string='Montant')
    credit = fields.Float(string='Crédit', help="Si la commande n'est pas payée")
    payer_id = fields.Many2one('suivi.client', string='Qui a payé')
    state = fields.Selection([
        ('initial', 'Initial'),
        ('paid', 'Payé'),
        ('validated', 'Validé')
    ], string='État', default='initial', tracking=True)

    line_ids = fields.One2many('suivi.operation.line', 'operation_id', string='Détails des opérations')

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('suivi.operation') or '/'
        return super(SuiviOperation, self).create(vals)

    @api.constrains('montant', 'credit', 'ville')
    def _check_montant_credit(self):
        for rec in self:
            if rec.ville != 'casa':
                if rec.montant <= 0 and rec.credit <= 0:
                    raise ValidationError(_("Pour les villes hors Casa, soit le montant soit le crédit doit être positif."))

    def action_pay(self):
        for rec in self:
            if rec.credit > 0:
                raise ValidationError(_("Impossible de passer à l'état 'Payé' tant que le crédit n'est pas nul."))
            rec.state = 'paid'

    def action_validate(self):
        self.write({'state': 'validated'})

    def action_set_initial(self):
        self.write({'state': 'initial'})

class SuiviOperationLine(models.Model):
    _name = 'suivi.operation.line'
    _description = 'Ligne Opération Suivi Transport'

    operation_id = fields.Many2one('suivi.operation', string='Opération', required=True, ondelete='cascade')
    client_id = fields.Many2one('suivi.client', string='Client')
    article_id = fields.Many2one('company.article', string='Article')
    lot = fields.Char(string='LOT')
