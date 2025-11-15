from odoo import models, fields, api

class Kal3iyaClient(models.Model):
    _name = 'kal3iya.client'
    _description = 'Clients'

    name = fields.Char(string='Client', required=True)

    # Lignes de sorties automatiquement calculées
    sortie_ids = fields.One2many(
        'kal3iyasortie',
        'client_id',
        string='Sorties de ce client',
        compute='_compute_sortie_ids',
        store=False,
    )

    sortie_count = fields.Integer(
        string="Nombre de commandes",
        compute='_compute_sortie_ids'
    )

    sorties_grouped_html = fields.Html(
        string="Sorties groupées",
        compute="_compute_sorties_grouped_html",
        sanitize=False,
    )


    avances = fields.One2many('kal3iya.advance', 'client_id', string='Avances')
    compte = fields.Float(readonly=True, compute='_compute_compte', store=True)

    def _compute_sortie_ids(self):
        """Récupère automatiquement les sorties liées à ce client"""
        for client in self:
            sorties = self.env['kal3iyasortie'].search([('client_id', '=', client.id)])
            client.sortie_ids = sorties
            client.sortie_count = len(sorties)



    # Lignes de retours automatiquement calculées
    retour_ids = fields.One2many(
        'kal3iyaentry',
        'client_id',
        string='Retours de ce client',
        compute='_compute_retour_ids',
        store=False,
    )

    retour_count = fields.Integer(
        string="Nombre de retours",
        compute='_compute_retour_ids'
    )


    def _compute_retour_ids(self):
        """Récupère automatiquement les retours liées à ce client"""
        for client in self:
            retours = self.env['kal3iyaentry'].search([('client_id', '=', client.id)])
            client.retour_ids = retours
            client.retour_count = len(retours)


    @api.depends('sortie_ids.mt_vente', 'avances.amount', 'retour_ids.selling_price', 'retour_ids.tonnage', 'retour_ids.state')
    def _compute_compte(self):
        """Compte = ventes - avances - retours"""
        for client in self:
            # 💰 Total des ventes
            total_ventes = sum(client.sortie_ids.mapped('mt_vente'))

            # 💵 Total des avances
            total_avances = sum(client.avances.mapped('amount'))

            # 🔄 Total des retours (entrées avec state='retour')
            retours = client.retour_ids.filtered(lambda r: r.state == 'retour')
            total_retours = sum(r.selling_price*r.tonnage for r in retours)

            # 🧮 Calcul final
            client.compte = total_ventes - total_avances - total_retours

    @api.depends('sortie_ids', 'sortie_ids.week', 'sortie_ids.mt_vente')
    def _compute_sorties_grouped_html(self):
        for rec in self:
            html = """
                <style>
                    .sorties-container {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                        max-width: 100%;
                        padding: 10px;
                    }
                    .week-card {
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        border-radius: 16px;
                        padding: 24px;
                        margin: 24px 0;
                        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.25);
                        transition: transform 0.3s ease;
                    }
                    .week-card:hover {
                        transform: translateY(-2px);
                        box-shadow: 0 15px 40px rgba(102, 126, 234, 0.35);
                    }
                    .week-header {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        margin-bottom: 20px;
                        flex-wrap: wrap;
                        gap: 12px;
                    }
                    .week-title {
                        color: white;
                        font-size: 24px;
                        font-weight: 700;
                        margin: 0;
                        display: flex;
                        align-items: center;
                        gap: 8px;
                    }
                    .week-total {
                        background: rgba(255, 255, 255, 0.95);
                        color: #667eea;
                        padding: 10px 20px;
                        border-radius: 12px;
                        font-size: 18px;
                        font-weight: 700;
                        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                    }
                    .products-grid {
                        display: grid;
                        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                        gap: 16px;
                    }
                    .product-card {
                        background: white;
                        border-radius: 14px;
                        padding: 18px;
                        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
                        transition: all 0.3s ease;
                        border-left: 4px solid #667eea;
                    }
                    .product-card:hover {
                        transform: translateY(-4px);
                        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
                        border-left-color: #764ba2;
                    }
                    .product-name {
                        font-size: 17px;
                        font-weight: 700;
                        color: #2d3748;
                        margin-bottom: 12px;
                        line-height: 1.4;
                    }
                    .product-details {
                        display: flex;
                        flex-direction: column;
                        gap: 8px;
                    }
                    .product-detail-row {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        font-size: 14px;
                        color: #4a5568;
                        padding: 6px 0;
                        border-bottom: 1px solid #f7fafc;
                    }
                    .product-detail-row:last-child {
                        border-bottom: none;
                    }
                    .detail-label {
                        font-weight: 500;
                        color: #718096;
                    }
                    .detail-value {
                        font-weight: 600;
                        color: #2d3748;
                    }
                    .detail-value.amount {
                        color: #667eea;
                        font-size: 16px;
                    }
                    .detail-value.date {
                        color: #805ad5;
                        font-size: 13px;
                    }
                    @media (max-width: 768px) {
                        .week-header {
                            flex-direction: column;
                            align-items: flex-start;
                        }
                        .products-grid {
                            grid-template-columns: 1fr;
                        }
                    }
                </style>
                <div class="sorties-container">
            """
            
            sorties = rec.sortie_ids.sorted(lambda s: s.date_exit or "")

            # Regroupement par semaine
            groups = {}
            for s in sorties:
                w = s.week or "Sans semaine"
                groups.setdefault(w, []).append(s)

            # Construction du HTML
            for week, records in groups.items():
                # Total ventes de la semaine
                total_week = sum(r.mt_vente for r in records)

                html += f"""
                    <div class="week-card">
                        <div class="week-header">
                            <h3 class="week-title">
                                <span>📅</span>
                                <span>Semaine {week}</span>
                            </h3>
                            <div class="week-total">
                                {total_week:,.2f} Dh
                            </div>
                        </div>

                        <div class="products-grid">
                """

                # Cartes pour chaque produit
                for s in records:
                    html += f"""
                        <div class="product-card">
                            <div class="product-name">{s.name}</div>
                            <div class="product-details">
                                <div class="product-detail-row">
                                    <span class="detail-label">Quantité</span>
                                    <span class="detail-value">{s.quantity}</span>
                                </div>
                                <div class="product-detail-row">
                                    <span class="detail-label">Prix unitaire</span>
                                    <span class="detail-value">{s.selling_price} Dh</span>
                                </div>
                                <div class="product-detail-row">
                                    <span class="detail-label">Montant</span>
                                    <span class="detail-value amount">{s.mt_vente} Dh</span>
                                </div>
                                <div class="product-detail-row">
                                    <span class="detail-label">Date</span>
                                    <span class="detail-value date">{s.date_exit}</span>
                                </div>
                            </div>
                        </div>
                    """

                html += """
                        </div>
                    </div>
                """

            html += "</div>"
            rec.sorties_grouped_html = html