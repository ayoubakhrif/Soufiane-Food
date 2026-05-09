from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class SuiviTransportTangerOperation(models.Model):
    _name = 'suivi.transport.tanger.operation'
    _description = 'Opération Suivi Transport Tanger'
    _order = 'date desc, id desc'

    name = fields.Char(string='Référence', required=True, copy=False, readonly=True, default='/')
    ville = fields.Selection([
        ('tanger', 'Tanger'),
        ('casa', 'Casa'),
        ('kenitra', 'Kenitra'),
        ('agadir', 'Agadir'),
        ('marrakech', 'Marrakech'),
    ], string='Ville', required=True, default='tanger')
    chauffeur_id = fields.Many2one('stock.kal3iya.driver', string='Chauffeur', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    lot = fields.Char(string='LOT')
    montant = fields.Float(string='Montant', default=0.0)
    credit = fields.Float(string='Crédit', help="Si la commande n'est pas payée", default=0.0)
    casa_payer_id = fields.Many2one('casa.client', string='Qui a payé')
    available_client_ids = fields.Many2many('casa.client', compute='_compute_available_client_ids', store=False)
    state = fields.Selection([
        ('initial', 'Initial'),
        ('paid', 'Payé'),
        ('validated', 'Validé')
    ], string='État', default='initial', tracking=True)

    line_ids = fields.One2many('suivi.transport.tanger.operation.line', 'operation_id', string='Détails des opérations')

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('suivi.transport.tanger.operation') or '/'
        return super(SuiviTransportTangerOperation, self).create(vals)

    @api.constrains('montant', 'credit', 'ville')
    def _check_montant_credit(self):
        for rec in self:
            if rec.ville != 'casa':
                if rec.montant < 0 or rec.credit < 0:
                    raise ValidationError(_("Le montant ou le crédit ne peuvent pas être négatifs."))

    @api.depends('line_ids.casa_client_id')
    def _compute_available_client_ids(self):
        for rec in self:
            rec.available_client_ids = rec.line_ids.mapped('casa_client_id')

    def action_pay(self):
        for rec in self:
            if rec.credit > 0:
                raise ValidationError(_("Impossible de passer à l'état 'Payé' tant que le crédit n'est pas nul."))
            rec.state = 'paid'

    def action_validate(self):
        for rec in self:
            if rec.ville == 'tanger':
                if not self.env.user.has_group('casa_stock.group_manager'):
                    raise ValidationError(_("Seul le responsable de stock_casa peut valider les opérations de Tanger."))
            
            if rec.credit > 0:
                raise ValidationError(_("La validation n'est possible que si le crédit est de 0."))
            
            # Créer l'avance si un client a payé un montant
            if rec.casa_payer_id and rec.montant > 0:
                self.env['casa.client.advance'].with_context(is_transport_operation=True).create({
                    'client_id': rec.casa_payer_id.id,
                    'amount': rec.montant,
                    'date': rec.date,
                    'payment_mode': 'transport',
                    'ville': rec.ville,
                    'comment': f"Paiement transport {rec.name}",
                    'state': 'confirmed',
                })

            rec.state = 'validated'

    def action_set_initial(self):
        self.write({'state': 'initial'})

class SuiviTransportTangerOperationLine(models.Model):
    _name = 'suivi.transport.tanger.operation.line'
    _description = 'Ligne Opération Suivi Transport Tanger'

    operation_id = fields.Many2one('suivi.transport.tanger.operation', string='Opération', required=True, ondelete='cascade')
    casa_client_id = fields.Many2one('casa.client', string='Client')
    article_id = fields.Many2one('stock.kal3iya.product', string='Article')
    lot = fields.Char(string='LOT')
    exit_id = fields.Many2one('stock.kal3iya.exit', string='Sortie Stock Liée')
