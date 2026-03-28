from collections import defaultdict
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CasaClient(models.Model):
    _name = 'casa.client'
    _description = 'Clients Casa'

    name = fields.Char(string='Nom', required=True)
    compte_initial = fields.Float(
        string='Compte initial',
        help="Solde du client avant l'utilisation du système"
    )

    # Champ computed pour le nombre de commandes
    exit_count = fields.Integer(
        string='Commandes',
        compute='_compute_exit_count',
        store=True,
    )

    exit_ids = fields.One2many(
        'casa.stock.exit',
        'client_id',
        string='Sorties de ce client',
    )

    discount_ids = fields.One2many(
        'casa.stock.discount',
        'client_id',
        string='Réductions',
    )
    advance_ids = fields.One2many(
        'casa.client.advance',
        'client_id',
        string='Avances',
    )
    unpaid_ids = fields.One2many(
        'casa.client.unpaid',
        'client_id',
        string='Impayés',
    )

    exits_to_discount_ids = fields.One2many(
        'casa.stock.exit',
        'client_id',
        string='Sorties à Réduire',
        domain=[('state', '=', 'done'), ('discount_amount', '=', 0)],
    )

    def action_apply_discounts(self):
        """
        Process exits that have a price_sale_corrected set.
        Group them by order_id, create a discount record per order, 
        and confirm it.
        """
        self.ensure_one()
        # Find all exits with a corrected price
        exits = self.exits_to_discount_ids.filtered(lambda e: e.price_sale_corrected > 0)
        
        if not exits:
            raise UserError(_("Veuillez saisir un 'Nouveau Prix de Vente' pour au moins une sortie avant d'appliquer les réductions."))

        # 1. Validation check for order_id
        missing_order = exits.filtered(lambda e: not e.order_id)
        if missing_order:
            raise UserError(_(
                "Certaines sorties ne sont pas liées à une commande. "
                "Veuillez vous assurer que toutes les sorties sont associées à une commande valide avant d'appliquer les réductions."
            ))

        # 2. Group exits by order_id
        orders_exits = {}
        for ex in exits:
            if ex.order_id not in orders_exits:
                orders_exits[ex.order_id] = []
            orders_exits[ex.order_id].append(ex)

        # 3. Create and confirm discounts
        for order, group_exits in orders_exits.items():
            # Create the main discount record
            discount_vals = {
                'order_id': order.id,
                'client_id': self.id,
                'date': fields.Date.context_today(self),
                'discount_type': 'amount',
                'distribution_type': 'manual',
                'reason': _('Réduction appliquée via le formulaire client (Correction de prix)'),
            }
            discount = self.env['casa.stock.discount'].create(discount_vals)

            # Create lines
            line_vals_list = []
            for ex in group_exits:
                # amount = (initial_price - corrected_price) * tonnage
                discount_amount = (ex.price_sale - ex.price_sale_corrected) * (ex.tonnage or 0.0)
                line_vals_list.append((0, 0, {
                    'discount_id': discount.id,
                    'exit_id': ex.id,
                    'discount_value': discount_amount,
                }))
            
            discount.write({'line_ids': line_vals_list})
            
            # Confirm the discount
            discount.action_confirm()

            # Clear the temporary corrected price on exits
            for ex in group_exits:
                ex.write({'price_sale_corrected': 0.0})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Réductions Appliquées'),
                'message': _('Les réductions ont été créées et confirmées pour %s commandes.') % len(orders_exits),
                'sticky': False,
                'type': 'success',
            }
        }

    total_commandes = fields.Float(
        string='Total commandes',
        compute='_compute_totals',
        store=True
    )

    compte_total = fields.Float(
        string='Compte total',
        compute='_compute_totals',
        store=True
    )

    sorties_grouped_html = fields.Html(
        string="Historique des commandes",
        compute="_compute_sorties_grouped_html",
        sanitize=False,
    )

    # --- Résumé Client ---
    total_orders_amount = fields.Float(
        string='Total Commandes (Avant Réductions)',
        compute='_compute_client_summary', store=True,
    )
    total_client_discounts = fields.Float(
        string='Total Réductions',
        compute='_compute_client_summary', store=True,
    )
    discount_rate = fields.Float(
        string='Taux de Réduction (%)',
        compute='_compute_client_summary', store=True,
    )
    total_profit = fields.Float(
        string='Total Profit',
        compute='_compute_client_summary', store=True,
    )

    summary_html = fields.Html(
        string='Resume Client',
        compute='_compute_summary_html',
        sanitize=False,
    )

    @api.depends('exit_ids', 'exit_ids.state')
    def _compute_exit_count(self):
        """Compte uniquement les sorties confirmées (done)"""
        for rec in self:
            rec.exit_count = len(rec.exit_ids.filtered(lambda s: s.state == 'done'))

    @api.depends('exit_ids.state', 'exit_ids.mt_vente', 'exit_ids.discount_amount', 'compte_initial', 'advance_ids.amount', 'unpaid_ids.amount')
    def _compute_totals(self):
        for client in self:
            commandes = client.exit_ids.filtered(lambda s: s.state == 'done')
            total_ventes = sum(commandes.mapped('mt_vente'))
            total_discounts = sum(commandes.mapped('discount_amount'))
            total_advances = sum(client.advance_ids.mapped('amount'))
            total_impayes = sum(client.unpaid_ids.mapped('amount'))

            client.total_commandes = total_ventes
            client.compte_total = (client.compte_initial or 0.0) + total_ventes + total_impayes - total_discounts - total_advances

    @api.depends('exit_ids.state', 'exit_ids.mt_vente', 'exit_ids.discount_amount', 'exit_ids.margin')
    def _compute_client_summary(self):
        for client in self:
            commandes = client.exit_ids.filtered(lambda s: s.state == 'done')
            total_orders = sum(commandes.mapped('mt_vente'))
            total_discounts = sum(commandes.mapped('discount_amount'))
            total_profit = sum(commandes.mapped('margin'))

            client.total_orders_amount = total_orders
            client.total_client_discounts = total_discounts
            client.discount_rate = (total_discounts / total_orders * 100) if total_orders else 0.0
            client.total_profit = total_profit

    @api.depends('total_orders_amount', 'total_client_discounts', 'discount_rate', 'total_profit')
    def _compute_summary_html(self):
        for client in self:
            profit = client.total_profit or 0.0
            if profit > 0:
                profit_color = '#059669'
                profit_bg = '#ecfdf5'
                profit_border = '#a7f3d0'
                profit_icon = '&#x2705;'
            elif profit == 0:
                profit_color = '#d97706'
                profit_bg = '#fffbeb'
                profit_border = '#fde68a'
                profit_icon = '&#x26A0;'
            else:
                profit_color = '#dc2626'
                profit_bg = '#fef2f2'
                profit_border = '#fecaca'
                profit_icon = '&#x274C;'

            client.summary_html = """
            <style>
                .kpi-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                    gap: 20px;
                    padding: 20px 0;
                }}
                .kpi-card {{
                    border-radius: 16px;
                    padding: 24px;
                    text-align: center;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.08);
                    transition: transform 0.2s;
                }}
                .kpi-card:hover {{
                    transform: translateY(-3px);
                    box-shadow: 0 8px 25px rgba(0,0,0,0.12);
                }}
                .kpi-icon {{
                    font-size: 32px;
                    margin-bottom: 8px;
                }}
                .kpi-label {{
                    font-size: 13px;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    margin-bottom: 8px;
                }}
                .kpi-value {{
                    font-size: 28px;
                    font-weight: 800;
                    line-height: 1.2;
                }}
                .kpi-unit {{
                    font-size: 14px;
                    font-weight: 400;
                    opacity: 0.7;
                }}
            </style>
            <div class="kpi-grid">
                <div class="kpi-card" style="background: #eff6ff; border: 2px solid #93c5fd;">
                    <div class="kpi-icon">&#x1F4E6;</div>
                    <div class="kpi-label" style="color: #1e40af;">Total Commandes</div>
                    <div class="kpi-value" style="color: #1d4ed8;">
                        {total_orders:,.2f}
                        <span class="kpi-unit">Dh</span>
                    </div>
                </div>
                <div class="kpi-card" style="background: #fef2f2; border: 2px solid #fca5a5;">
                    <div class="kpi-icon">&#x1F3F7;</div>
                    <div class="kpi-label" style="color: #991b1b;">Total Reductions</div>
                    <div class="kpi-value" style="color: #dc2626;">
                        {total_discounts:,.2f}
                        <span class="kpi-unit">Dh</span>
                    </div>
                </div>
                <div class="kpi-card" style="background: #fffbeb; border: 2px solid #fcd34d;">
                    <div class="kpi-icon">&#x1F4CA;</div>
                    <div class="kpi-label" style="color: #92400e;">Taux de Reduction</div>
                    <div class="kpi-value" style="color: #d97706;">
                        {rate:.2f}
                        <span class="kpi-unit">%</span>
                    </div>
                </div>
                <div class="kpi-card" style="background: {profit_bg}; border: 2px solid {profit_border};">
                    <div class="kpi-icon">{profit_icon}</div>
                    <div class="kpi-label" style="color: {profit_color};">Total Profit</div>
                    <div class="kpi-value" style="color: {profit_color};">
                        {profit_val:,.2f}
                        <span class="kpi-unit">Dh</span>
                    </div>
                </div>
            </div>
            """.format(
                total_orders=client.total_orders_amount or 0.0,
                total_discounts=client.total_client_discounts or 0.0,
                rate=client.discount_rate or 0.0,
                profit_bg=profit_bg,
                profit_border=profit_border,
                profit_icon=profit_icon,
                profit_color=profit_color,
                profit_val=profit,
            )


    @api.depends('name')
    def _compute_sorties_grouped_html(self):
        for client in self:

            # 1️⃣ Récupérer les sorties NON annulées du client
            exits = self.env['casa.stock.exit'].search([
                ('client_id', '=', client.id),
                ('state', '=', 'done'),
            ], order='date asc')

            if not exits:
                client.sorties_grouped_html = "<p style='padding:10px;'>Aucune commande.</p>"
                continue

            # 2️⃣ Grouper par semaine
            grouped = defaultdict(list)
            for e in exits:
                if e.date:
                    week = e.date.isocalendar()[1]
                else:
                    week = "N/A"
                grouped[week].append(e)

            # 3️⃣ Construction du HTML
            html = """
            <style>
                .week-card {
                    background: #ffffff;
                    border: 1px solid #e5e7eb;
                    border-radius: 12px;
                    padding: 16px;
                    margin-bottom: 20px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                }
                .week-header {
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 12px;
                }
                .week-title {
                    font-size: 18px;
                    font-weight: 700;
                    color: #1f2937;
                }
                .week-total {
                    background: #2563eb;
                    color: white;
                    padding: 6px 14px;
                    border-radius: 999px;
                    font-weight: 700;
                }
                .row {
                    display: grid;
                    grid-template-columns: 2fr 1fr 1fr 1fr 1fr 1fr 1fr;
                    padding: 8px 0;
                    border-bottom: 1px dashed #e5e7eb;
                    font-size: 13px;
                }
                .row.header {
                    font-weight: 700;
                    border-bottom: 2px solid #e5e7eb;
                }
            </style>
            """

            for week, records in grouped.items():
                total_week = sum(
                    (r.tonnage or 0) * (r.price_sale or 0)
                    for r in records
                )

                html += f"""
                <div class="week-card">
                    <div class="week-header">
                        <div class="week-title">📅 Semaine {week}</div>
                        <div class="week-total">{total_week:,.2f} Dh</div>
                    </div>

                    <div class="row header">
                        <div>Produit</div>
                        <div>Qté</div>
                        <div>Prix</div>
                        <div>Montant</div>
                        <div>Réduction</div>
                        <div>Montant Final</div>
                        <div>Date</div>
                    </div>
                """

                for r in records:
                    montant = (r.tonnage or 0) * (r.price_sale or 0)
                    reduction = r.discount_amount or 0.0
                    montant_final = montant - reduction
                    html += f"""
                    <div class="row">
                        <div>{r.product_id.name if r.product_id else ''}</div>
                        <div>{r.qty}</div>
                        <div>{r.price_sale:.2f}</div>
                        <div style="font-weight:700;color:#2563eb;">
                            {montant:.2f}
                        </div>
                        <div style="color:#e53e3e;">{reduction:.2f}</div>
                        <div style="font-weight:700;color:#38a169;">{montant_final:.2f}</div>
                        <div>{r.date}</div>
                    </div>
                    """

                html += "</div>"

            client.sorties_grouped_html = html
