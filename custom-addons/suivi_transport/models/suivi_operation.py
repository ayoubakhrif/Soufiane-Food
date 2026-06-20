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
        for rec in self:
            for line in rec.line_ids:
                if line.stock_id:
                    self.env['suivi.stock.move'].create({
                        'product_id': line.stock_id.product_id.id,
                        'lot': line.stock_id.lot,
                        'dum': line.stock_id.dum,
                        'ville': rec.ville,
                        'qty': -line.qty,
                        'move_type': 'exit',
                        'state': 'done',
                        'date': rec.date,
                        'reference': rec.name,
                        'weight': line.stock_id.weight,
                        'calibre': line.stock_id.calibre,
                        'chauffeur_id': rec.chauffeur_id.id,
                        'res_model': 'suivi.operation',
                        'res_id': rec.id,
                    })
        self.write({'state': 'validated'})

    def action_set_initial(self):
        for rec in self:
            moves = self.env['suivi.stock.move'].search([
                ('res_model', '=', 'suivi.operation'),
                ('res_id', '=', rec.id),
                ('move_type', '=', 'exit'),
                ('state', '=', 'done')
            ])
            for move in moves:
                self.env['suivi.stock.move'].create({
                    'product_id': move.product_id.id,
                    'lot': move.lot,
                    'dum': move.dum,
                    'ville': move.ville,
                    'qty': -move.qty,
                    'move_type': 'cancel_exit',
                    'state': 'done',
                    'date': fields.Datetime.now(),
                    'reference': rec.name,
                    'weight': move.weight,
                    'calibre': move.calibre,
                    'chauffeur_id': rec.chauffeur_id.id,
                    'res_model': 'suivi.operation',
                    'res_id': rec.id,
                })
        self.write({'state': 'initial'})

class SuiviOperationLine(models.Model):
    _name = 'suivi.operation.line'
    _description = 'Ligne Opération Suivi Transport'

    operation_id = fields.Many2one('suivi.operation', string='Opération', required=True, ondelete='cascade')
    client_id = fields.Many2one('suivi.client', string='Client')
    
    stock_id = fields.Many2one('suivi.stock.stock', string='Stock Disponible')
    article_id = fields.Many2one('company.article', string='Article')
    
    qty = fields.Float(string='Quantité', required=True, default=1.0)
    lot = fields.Char(string='LOT')
    dum = fields.Char(string='DUM')

    @api.onchange('stock_id')
    def _onchange_stock_id(self):
        if self.stock_id:
            self.lot = self.stock_id.lot
            self.dum = self.stock_id.dum
            self.article_id = self.stock_id.product_id.article_id.id
            if self.qty == 0.0:
                self.qty = 1.0

    @api.constrains('qty', 'stock_id')
    def _check_stock_availability(self):
        for line in self:
            if line.stock_id:
                total_ordered = sum(
                    other_line.qty 
                    for other_line in line.operation_id.line_ids 
                    if other_line.stock_id.id == line.stock_id.id
                )
                if total_ordered > line.stock_id.quantity:
                    raise ValidationError(_(
                        "Quantité globale insuffisante pour le stock sélectionné.\n"
                        "Demandée au total: %(req)s, Disponible: %(avail)s"
                    ) % {'req': total_ordered, 'avail': line.stock_id.quantity})
