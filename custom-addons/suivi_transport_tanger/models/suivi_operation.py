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
    paid_by_caisse = fields.Boolean(string='Payé par la caisse', default=False)
    available_client_ids = fields.Many2many('casa.client', compute='_compute_available_client_ids', store=False)

    @api.onchange('paid_by_caisse')
    def _onchange_paid_by_caisse(self):
        if self.paid_by_caisse:
            self.casa_payer_id = False

    state = fields.Selection([
        ('initial', 'Initial'),
        ('paid', 'Payé'),
        ('validated', 'Validé'),
        ('cancelled', 'Annulé')
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
            if not self.env.user.has_group('casa_stock.group_manager'):
                raise ValidationError(_("Seul le responsable de stock_casa peut valider les opérations."))
            
            if rec.credit > 0:
                raise ValidationError(_("La validation n'est possible que si le crédit est de 0."))
            
            # Créer ou mettre à jour l'avance si un client a payé un montant
            if rec.casa_payer_id and rec.montant > 0:
                existing_advance = self.env['casa.client.advance'].sudo().search([('comment', '=', f"Paiement transport {rec.name}")], limit=1)
                if existing_advance:
                    existing_advance.with_context(is_transport_operation=True).write({
                        'client_id': rec.casa_payer_id.id,
                        'amount': rec.montant,
                        'date': rec.date,
                        'ville': rec.ville,
                        'state': 'confirmed',
                    })
                else:
                    self.env['casa.client.advance'].sudo().with_context(is_transport_operation=True).create({
                        'client_id': rec.casa_payer_id.id,
                        'amount': rec.montant,
                        'date': rec.date,
                        'payment_mode': 'transport',
                        'ville': rec.ville,
                        'comment': f"Paiement transport {rec.name}",
                        'state': 'confirmed',
                    })

            rec.sudo().write({'state': 'validated'})

    def action_set_initial(self):
        for rec in self:
            rec.write({'state': 'initial'})
            advance = self.env['casa.client.advance'].sudo().search([('comment', '=', f"Paiement transport {rec.name}")])
            if advance:
                advance.with_context(is_transport_operation=True).action_draft()

    def action_cancel(self):
        for rec in self:
            rec.write({'state': 'cancelled'})
            advance = self.env['casa.client.advance'].sudo().search([('comment', '=', f"Paiement transport {rec.name}")])
            if advance:
                advance.with_context(is_transport_operation=True).action_cancel()

    def unlink(self):
        for rec in self:
            if rec.state not in ('initial', 'cancelled'):
                raise ValidationError(_("Vous ne pouvez supprimer que les opérations à l'état Initial ou Annulé."))
            advance = self.env['casa.client.advance'].sudo().search([('comment', '=', f"Paiement transport {rec.name}")])
            if advance:
                advance.with_context(is_transport_operation=True).unlink()
        return super(SuiviTransportTangerOperation, self).unlink()

class SuiviTransportTangerOperationLine(models.Model):
    _name = 'suivi.transport.tanger.operation.line'
    _description = 'Ligne Opération Suivi Transport Tanger'

    operation_id = fields.Many2one('suivi.transport.tanger.operation', string='Opération', required=True, ondelete='cascade')
    casa_client_id = fields.Many2one('casa.client', string='Client', required=True)
    use_client2 = fields.Boolean(related='casa_client_id.use_client2', string='Utiliser Client 2', readonly=True)
    client2 = fields.Char(string='Client 2')
    article_id = fields.Many2one('stock.kal3iya.product', string='Article')
    lot = fields.Char(string='LOT')
    exit_id = fields.Many2one('stock.kal3iya.exit', string='Sortie Stock Liée')
