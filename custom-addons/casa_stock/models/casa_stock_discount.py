from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CasaStockDiscount(models.Model):
    _name = 'casa.stock.discount'
    _description = 'Réduction Commerciale'
    _order = 'date desc, id desc'

    name = fields.Char(string='Référence', readonly=True, default='/')

    order_id = fields.Many2one(
        'casa.stock.order', string='Commande', required=True,
        domain="[('state', '=', 'done')]",
    )
    client_id = fields.Many2one('casa.client', string='Client')
    date = fields.Date(string='Date')
    driver_id = fields.Many2one('casa.driver', string='Chauffeur')

    discount_type = fields.Selection([
        ('amount', 'Montant'),
        ('percentage', 'Pourcentage'),
    ], string='Type de Réduction', required=True, default='amount')

    distribution_type = fields.Selection([
        ('proportional_amount', 'Proportionnel au Montant'),
        ('proportional_qty', 'Proportionnel à la Quantité'),
        ('manual', 'Manuel'),
    ], string='Type de Distribution', required=True, default='proportional_amount')

    reason = fields.Char(string='Motif de Réduction')
    comment = fields.Text(string='Commentaire')

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Confirmé'),
        ('cancel', 'Annulé'),
    ], string='État', default='draft', required=True)

    line_ids = fields.One2many(
        'casa.stock.discount.line', 'discount_id', string='Lignes de Réduction',
    )

    # --- Totals ---
    total_before_discount = fields.Float(
        string='Total Avant Réduction',
        compute='_compute_totals', store=True,
    )
    total_discount = fields.Float(
        string='Montant Réduction',
        compute='_compute_totals', store=True,
    )
    total_after_discount = fields.Float(
        string='Total Après Réduction',
        compute='_compute_totals', store=True,
    )

    # Field to collect the global discount value used for distribution
    global_discount_value = fields.Float(string='Valeur de Réduction Globale')

    # -------------------------------------------------------------------------
    # Computed
    # -------------------------------------------------------------------------
    @api.depends(
        'line_ids.initial_amount',
        'line_ids.discount_amount',
        'line_ids.final_amount',
    )
    def _compute_totals(self):
        for rec in self:
            rec.total_before_discount = sum(rec.line_ids.mapped('initial_amount'))
            rec.total_discount = sum(rec.line_ids.mapped('discount_amount'))
            rec.total_after_discount = sum(rec.line_ids.mapped('final_amount'))

    # -------------------------------------------------------------------------
    # Onchanges
    # -------------------------------------------------------------------------
    @api.onchange('order_id')
    def _onchange_order_id(self):
        if self.order_id:
            self.client_id = self.order_id.client_id
            self.date = self.order_id.date
            self.driver_id = self.order_id.driver_id
            # Populate lines from confirmed exits
            lines = []
            for exit_rec in self.order_id.exit_ids.filtered(lambda e: e.state == 'done'):
                lines.append((0, 0, {
                    'exit_id': exit_rec.id,
                }))
            self.line_ids = lines
        else:
            self.client_id = False
            self.date = False
            self.driver_id = False
            self.line_ids = [(5, 0, 0)]

    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------
    @api.constrains('order_id')
    def _check_unique_order_discount(self):
        """Block creating two active (non-cancelled) discounts for the same order."""
        for rec in self:
            if rec.order_id:
                existing = self.search([
                    ('order_id', '=', rec.order_id.id),
                    ('state', '!=', 'cancel'),
                    ('id', '!=', rec.id),
                ])
                if existing:
                    raise UserError(_(
                        "Une réduction active existe déjà pour la commande %s. "
                        "Vous ne pouvez pas créer deux réductions pour la même commande."
                    ) % rec.order_id.name)

    # -------------------------------------------------------------------------
    # CRUD
    # -------------------------------------------------------------------------
    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('casa.stock.discount') or '/'
        return super().create(vals)

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------
    def action_distribute(self):
        """Distribute the global discount value across lines based on distribution_type."""
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("La réduction doit être en brouillon pour distribuer."))
            if rec.distribution_type == 'manual':
                raise UserError(_("La distribution manuelle ne permet pas la distribution automatique."))
            if not rec.global_discount_value:
                raise UserError(_("Veuillez saisir une valeur de réduction globale avant de distribuer."))
            if not rec.line_ids:
                raise UserError(_("Aucune ligne de sortie à distribuer."))

            total_weight = 0.0
            if rec.distribution_type == 'proportional_amount':
                total_weight = sum(rec.line_ids.mapped('initial_amount'))
            elif rec.distribution_type == 'proportional_qty':
                total_weight = sum(rec.line_ids.mapped('qty'))

            if total_weight <= 0:
                raise UserError(_("Le total pour la distribution est nul. Impossible de distribuer."))

            for line in rec.line_ids:
                if rec.distribution_type == 'proportional_amount':
                    ratio = line.initial_amount / total_weight if total_weight else 0
                else:  # proportional_qty
                    ratio = line.qty / total_weight if total_weight else 0
                line.discount_value = rec.global_discount_value * ratio

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            if not rec.line_ids:
                raise UserError(_("Aucune ligne de réduction à confirmer."))

            total_order_amount = sum(rec.line_ids.mapped('initial_amount'))

            for line in rec.line_ids:
                if line.discount_amount < 0:
                    raise UserError(_(
                        "La réduction ne peut pas être négative pour le produit %s."
                    ) % line.product_id.display_name)
                if line.discount_amount > line.initial_amount:
                    raise UserError(_(
                        "La réduction (%s) dépasse le montant initial (%s) pour le produit %s."
                    ) % (line.discount_amount, line.initial_amount, line.product_id.display_name))

            total_discount = sum(rec.line_ids.mapped('discount_amount'))
            if total_discount > total_order_amount:
                raise UserError(_(
                    "Le total de la réduction (%s) dépasse le montant total de la commande (%s)."
                ) % (total_discount, total_order_amount))

            # Write discount to each exit
            for line in rec.line_ids:
                line.exit_id.sudo().write({
                    'discount_amount': line.discount_amount,
                })

            rec.write({'state': 'done'})

    def action_cancel(self):
        for rec in self:
            if rec.state != 'done':
                raise UserError(_("Vous ne pouvez annuler que des réductions confirmées."))
            # Reset discount on exits
            for line in rec.line_ids:
                line.exit_id.sudo().write({
                    'discount_amount': 0.0,
                })
            rec.write({'state': 'cancel'})

    def action_draft(self):
        for rec in self:
            if rec.state != 'cancel':
                raise UserError(_("Seules les réductions annulées peuvent être remises en brouillon."))
            rec.write({'state': 'draft'})


class CasaStockDiscountLine(models.Model):
    _name = 'casa.stock.discount.line'
    _description = 'Ligne de Réduction Commerciale'

    discount_id = fields.Many2one(
        'casa.stock.discount', string='Réduction',
        required=True, ondelete='cascade',
    )

    exit_id = fields.Many2one('casa.stock.exit', string='Sortie', required=True, readonly=True)

    # Related fields from exit (readonly)
    product_id = fields.Many2one('casa.product', string='Produit', related='exit_id.product_id', store=True, readonly=True)
    qty = fields.Float(string='Quantité', related='exit_id.qty', store=True, readonly=True)
    weight = fields.Float(string='Poids unit (Kg)', related='exit_id.weight', store=True, readonly=True)
    tonnage = fields.Float(string='Tonnage', related='exit_id.tonnage', store=True, readonly=True)
    price_sale = fields.Float(string='Prix Vente Initial', related='exit_id.price_sale', store=True, readonly=True)

    # Computed from exit
    initial_amount = fields.Float(
        string='Montant Initial',
        compute='_compute_amounts', store=True,
    )

    # Editable discount field
    discount_value = fields.Float(string='Réduction')

    # Computed discount in currency
    discount_amount = fields.Float(
        string='Montant Réduction',
        compute='_compute_amounts', store=True,
    )
    final_amount = fields.Float(
        string='Montant Final',
        compute='_compute_amounts', store=True,
    )

    @api.depends('tonnage', 'price_sale', 'discount_value', 'discount_id.discount_type')
    def _compute_amounts(self):
        for line in self:
            line.initial_amount = (line.price_sale or 0.0) * (line.tonnage or 0.0)
            if line.discount_id.discount_type == 'percentage':
                line.discount_amount = line.initial_amount * (line.discount_value or 0.0) / 100.0
            else:
                line.discount_amount = line.discount_value or 0.0
            line.final_amount = line.initial_amount - line.discount_amount
