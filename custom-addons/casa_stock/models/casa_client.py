from collections import defaultdict
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CasaClient(models.Model):
    _name = 'casa.client'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Clients Casa'

    name = fields.Char(string='Nom', required=True, tracking=True)
    compte_initial = fields.Float(
        string='Compte initial',
        help="Solde du client avant l'utilisation du système",
        tracking=True,
    )

    # Champ computed pour le nombre de commandes
    exit_count = fields.Integer(
        string='Commandes',
        compute='_compute_exit_count',
        store=True,
        tracking=True,
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
    discount_line_ids = fields.One2many(
        'casa.stock.discount.line',
        'client_id',
        string='Lignes de réduction',
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

    other_sale_ids = fields.One2many(
        'casa.other.sale',
        'client_id',
        string='Autres Ventes',
    )

    sortie_supp_ids = fields.One2many(
        'casa.sortie.supp',
        'client_id',
        string='Sorties Supplémentaires',
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
        store=True,
        tracking=True
    )

    compte_total = fields.Float(
        string='Compte total',
        compute='_compute_totals',
        store=True,
        tracking=True
    )

    compte_provisoire = fields.Float(
        string='Compte Provisoire',
        compute='_compute_totals',
        store=True,
        help="Solde incluant les commandes confirmées non encore validées.",
        tracking=True
    )

    total_advances = fields.Float(
        string='Total Avances',
        compute='_compute_totals',
        store=True,
        tracking=True
    )

    sorties_grouped_html = fields.Html(
        string="Historique des commandes",
        compute="_compute_sorties_grouped_html",
        sanitize=False,
    )

    # --- Résumé Client ---
    total_orders_amount = fields.Float(
        string='Total Commandes (Avant Réductions)',
        compute='_compute_client_summary', store=True, tracking=True,
    )
    total_client_discounts = fields.Float(
        string='Total Réductions',
        compute='_compute_client_summary', store=True, tracking=True,
    )
    discount_rate = fields.Float(
        string='Taux de Réduction (%)',
        compute='_compute_client_summary', store=True, tracking=True,
    )
    total_profit = fields.Float(
        string='Total Profit',
        compute='_compute_client_summary', store=True, tracking=True,
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

    @api.depends('exit_ids.state', 'exit_ids.mt_vente', 'exit_ids.discount_amount', 'other_sale_ids.state', 'other_sale_ids.mt_vente', 'other_sale_ids.discount_amount', 'sortie_supp_ids.amount', 'compte_initial', 'advance_ids.amount', 'advance_ids.state', 'unpaid_ids.amount')
    def _compute_totals(self):
        for client in self:
            # Official totals (Valide/Done only)
            commandes = client.exit_ids.filtered(lambda s: s.state == 'done')
            otras = client.other_sale_ids.filtered(lambda s: s.state == 'done')
            
            total_ventes = sum(commandes.mapped('mt_vente')) + sum(otras.mapped('mt_vente'))
            total_discounts = sum(commandes.mapped('discount_amount')) + sum(otras.mapped('discount_amount'))
            
            total_advances = sum(client.advance_ids.filtered(lambda a: a.state == 'confirmed').mapped('amount'))
            total_impayes = sum(client.unpaid_ids.mapped('amount'))
            total_sorties_supp = sum(client.sortie_supp_ids.mapped('amount'))

            client.total_commandes = total_ventes
            client.total_advances = total_advances
            client.compte_total = (client.compte_initial or 0.0) + total_ventes + total_impayes + total_sorties_supp - total_discounts - total_advances
            
            # Provisional totals (Confirmed + Done)
            # As per user request: only count validated advances, so total_advances remains the same.
            commandes_prov = client.exit_ids.filtered(lambda s: s.state in ('confirmed', 'done'))
            otras_prov = client.other_sale_ids.filtered(lambda s: s.state in ('confirmed', 'done'))
            
            total_ventes_prov = sum(commandes_prov.mapped('mt_vente')) + sum(otras_prov.mapped('mt_vente'))
            total_discounts_prov = sum(commandes_prov.mapped('discount_amount')) + sum(otras_prov.mapped('discount_amount'))
            
            client.compte_provisoire = (client.compte_initial or 0.0) + total_ventes_prov + total_impayes + total_sorties_supp - total_discounts_prov - total_advances

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
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px;
                    padding: 20px 0;
                }}
                .kpi-card {{
                    border-radius: 16px;
                    padding: 20px;
                    text-align: center;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.08);
                    transition: transform 0.2s;
                }}
                .kpi-card:hover {{
                    transform: translateY(-3px);
                    box-shadow: 0 8px 25px rgba(0,0,0,0.12);
                }}
                .kpi-icon {{
                    font-size: 28px;
                    margin-bottom: 8px;
                }}
                .kpi-label {{
                    font-size: 12px;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    margin-bottom: 8px;
                }}
                .kpi-value {{
                    font-size: 24px;
                    font-weight: 800;
                    line-height: 1.2;
                }}
                .kpi-unit {{
                    font-size: 13px;
                    font-weight: 400;
                    opacity: 0.7;
                }}
            </style>
            <div class="kpi-grid">
                <div class="kpi-card" style="background: #ebf4ff; border: 2px solid #4c51bf;">
                    <div class="kpi-icon">📋</div>
                    <div class="kpi-label" style="color: #4c51bf;">Solde Provisoire</div>
                    <div class="kpi-value" style="color: #4c51bf;">
                        {compte_provisoire:,.2f}
                        <span class="kpi-unit">Dh</span>
                    </div>
                </div>
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
                compte_provisoire=client.compte_provisoire or 0.0,
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

            # 1️⃣ Récupérer les sorties et autres ventes NON annulées du client
            exits = self.env['casa.stock.exit'].search([
                ('client_id', '=', client.id),
                ('state', '=', 'done'),
            ])
            
            others = self.env['casa.other.sale'].search([
                ('client_id', '=', client.id),
                ('state', '=', 'done'),
            ])

            # Merge and Sort
            all_records = sorted(list(exits) + list(others), key=lambda r: r.date if r.date else fields.Date.today())

            if not all_records:
                client.sorties_grouped_html = "<p style='padding:10px;'>Aucune commande.</p>"
                continue

            # 2️⃣ Grouper par semaine
            grouped = defaultdict(list)
            for e in all_records:
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
                    grid-template-columns: 2fr 1fr 1fr 1fr 1fr 1fr 1fr 1fr;
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
                    ((r.tonnage or 0) * (r.price_sale or 0)) - (r.discount_amount or 0.0)
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
                        <div>Prix Net</div>
                        <div>Montant Final</div>
                        <div>Date</div>
                    </div>
                """

                for r in records:
                    is_other = r._name == 'casa.other.sale'
                    type_label = f"<span style='font-size:10px;color:#6b7280;margin-left:5px;'>({r.de_qui or 'Autre'})</span>" if is_other else ""
                    
                    montant = (r.tonnage or 0) * (r.price_sale or 0)
                    reduction = r.discount_amount or 0.0
                    montant_final = montant - reduction
                    price_final = (montant_final / r.tonnage) if r.tonnage else r.price_sale
                    html += f"""
                    <div class="row">
                        <div>{r.product_id.name if r.product_id else ''} {type_label}</div>
                        <div>{r.qty}</div>
                        <div>{r.price_sale:.2f}</div>
                        <div style="font-weight:700;color:#2563eb;">
                            {montant:.2f}
                        </div>
                        <div style="color:#e53e3e;">{reduction:.2f}</div>
                        <div style="font-weight:700;color:#4c51bf;">{price_final:.2f}</div>
                        <div style="font-weight:700;color:#38a169;">{montant_final:.2f}</div>
                        <div>{r.date}</div>
                    </div>
                    """

                html += "</div>"

            client.sorties_grouped_html = html

    # ==============================
    #  🧮 Utilitaire pour le rapport
    # ==============================

    def get_all_weeks_list(self):
        """Return a sorted list of all unique weeks for this client."""
        weeks = set()
        
        def date_to_week(d):
            return d.strftime("%Y-W%W") if d else False
            
        # Sorties
        for s in self.exit_ids:
            if s.week: weeks.add(s.week)
        
        # Avances
        for a in self.advance_ids:
            if a.date: weeks.add(date_to_week(a.date))
            
        # Impayés
        for u in self.unpaid_ids:
            if u.date: weeks.add(date_to_week(u.date))
            
        return sorted(list(weeks), reverse=True)

    def _get_week_data(self, week):
        """
        Retourne un dict avec tous les totaux pour une semaine donnée.
        week : string au format 'YYYY-Www' (ex: '2025-W48')
        Utilisé par le rapport (QWeb).
        """
        from datetime import datetime, timedelta
        
        self.ensure_one()

        # 1️⃣ Filtrer sorties de la semaine
        sorties = self.exit_ids.filtered(lambda s: s.week == week and s.state == 'done')
        total_sorties = sum((s.mt_vente or 0.0) for s in sorties)
        total_discounts = sum((s.discount_amount or 0.0) for s in sorties)
        total_net_sorties = total_sorties - total_discounts

        # 2️⃣ Filtrer avances de la semaine (en se basant sur la date)
        avances = self.advance_ids.filtered(
            lambda a: a.date and a.date.strftime("%Y-W%W") == week
        )
        total_avances = sum(avances.mapped('amount'))

        # 3️⃣ Filtrer impayés de la semaine
        impayes = self.unpaid_ids.filtered(
            lambda u: u.date and u.date.strftime("%Y-W%W") == week
        )
        total_impayes = sum(impayes.mapped('amount'))

        # 4️⃣ Filtrer sorties supplémentaires de la semaine
        sorties_supp = self.sortie_supp_ids.filtered(
            lambda s: s.date and s.date.strftime("%Y-W%W") == week
        )
        total_sorties_supp = sum(sorties_supp.mapped('amount'))

        # 5️⃣ Compte de la semaine
        compte_semaine = total_net_sorties + total_impayes + total_sorties_supp - total_avances

        # 5️⃣ Calculer les dates de début et fin de semaine
        start_date = None
        end_date = None
        
        try:
            # Parser le format 'YYYY-Www' (ex: '2025-W48')
            year, week_num = week.split('-W')
            year = int(year)
            week_num = int(week_num)
            
            # Trouver le premier jour de la semaine (Lundi)
            # ISO: semaine commence le lundi
            jan_4 = datetime(year, 1, 4)
            week_1_monday = jan_4 - timedelta(days=jan_4.weekday())
            start_date_obj = week_1_monday + timedelta(weeks=week_num - 1)
            
            # Calculer le dernier jour (Dimanche)
            end_date_obj = start_date_obj + timedelta(days=6)
            
            # Formater les dates
            start_date = start_date_obj.strftime('%d/%m/%Y')
            end_date = end_date_obj.strftime('%d/%m/%Y')
        except:
            pass

        return {
            'week': week,
            'start_date': start_date,
            'end_date': end_date,
            'sorties': sorties,
            'avances': avances,
            'impayes': impayes,
            'sorties_supp': sorties_supp,
            'total_sorties': total_sorties,
            'total_discounts': total_discounts,
            'total_net_sorties': total_net_sorties,
            'total_avances': total_avances,
            'total_impayes': total_impayes,
            'total_sorties_supp': total_sorties_supp,
            'compte_semaine': compte_semaine,
            'compte_total': self.compte_total,
        }
    def _get_total_clients_report_data(self):
        """Prepare data for the Global Client Balance Summary report."""
        # Find all clients with a non-zero provisional balance
        clients = self.search([('compte_provisoire', '!=', 0)])
        if not clients:
            return {'clients': [], 'grand_total': 0}

        # Sort by provisional balance descending
        clients = clients.sorted(key=lambda c: c.compte_provisoire, reverse=True)
        
        report_data = {
            'report_date': fields.Date.today().strftime('%d/%m/%y'),
            'clients': [],
            'grand_total': sum(clients.mapped('compte_provisoire'))
        }
        
        for client in clients:
            report_data['clients'].append({
                'name': client.name,
                'compte_provisoire': client.compte_provisoire
            })
            
        return report_data
