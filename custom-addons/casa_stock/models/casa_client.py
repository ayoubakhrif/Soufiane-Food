from collections import defaultdict
from odoo import models, fields, api

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

    @api.depends('exit_ids', 'exit_ids.state')
    def _compute_exit_count(self):
        """Compte uniquement les sorties confirmées (done)"""
        for rec in self:
            rec.exit_count = len(rec.exit_ids.filtered(lambda s: s.state == 'done'))

    @api.depends('exit_ids.state', 'exit_ids.mt_vente', 'compte_initial')
    def _compute_totals(self):
        for client in self:
            commandes = client.exit_ids.filtered(lambda s: s.state == 'done')
            total_ventes = sum(commandes.mapped('mt_vente'))

            client.total_commandes = total_ventes
            client.compte_total = (client.compte_initial or 0.0) + total_ventes

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


    @api.depends('name')
    def _compute_sorties_grouped_html(self):
        for client in self:

            # 1️⃣ Récupérer les sorties NON annulées du client
            exits = self.env['casa.stock.exit'].search([
                ('client_id', '=', client.id),
                ('state', '!=', 'cancel'),
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
