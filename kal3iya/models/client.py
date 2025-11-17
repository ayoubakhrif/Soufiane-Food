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

    @api.depends('sortie_ids', 'sortie_ids.week', 'sortie_ids.mt_vente_final')
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
                        background: white;
                        border-radius: 12px;
                        border: 2px solid #e2e8f0;
                        padding: 18px;
                        margin: 22px 0;
                        box-shadow: 0 6px 20px rgba(0,0,0,0.06);
                    }

                    .week-header {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        margin-bottom: 15px;
                        flex-wrap: wrap;
                    }

                    .week-title {
                        font-size: 22px;
                        font-weight: 700;
                        color: #4c51bf;
                    }

                    .week-total {
                        background: #4c51bf;
                        color: white;
                        padding: 8px 18px;
                        border-radius: 10px;
                        font-size: 17px;
                        font-weight: 700;
                        box-shadow: 0 4px 12px rgba(76,81,191,0.3);
                    }

                    .table-header {
                        display: grid;
                        grid-template-columns: 1.2fr 0.5fr 0.7fr 0.6fr 0.8fr 0.7fr 0.6fr;
                        padding: 10px;
                        background: #e2e8f0;
                        border-radius: 8px;
                        font-weight: 700;
                        color: #2d3748;
                        margin-bottom: 10px;
                    }

                    .list-row {
                        display: grid;
                        grid-template-columns: 1.2fr 0.5fr 0.7fr 0.6fr 0.8fr 0.7fr 0.6fr;
                        padding: 12px 10px;
                        background: #f7fafc;
                        border-radius: 8px;
                        margin-bottom: 8px;
                        border-left: 4px solid #4c51bf;
                        transition: 0.2s ease;
                    }
                    .list-row:hover {
                        background: #edf2f7;
                        transform: translateX(4px);
                    }

                    .col-label {
                        font-size: 14px;
                        color: #2d3748;
                        font-weight: 600;
                    }
                    .col-value {
                        font-size: 15px;
                        color: #4a5568;
                        font-weight: 500;
                    }

                    .amount {
                        color: #4c51bf;
                        font-weight: 700;
                    }

                    .date {
                        font-size: 14px;
                        color: #805ad5;
                    }

                    .edit-btn {
                        background: #4c51bf;
                        color: white !important;
                        padding: 6px 10px;
                        border-radius: 6px;
                        font-weight: 600;
                        font-size: 13px;
                        text-decoration: none;
                        text-align: center;
                        display: inline-block;
                    }

                    .edit-btn:hover {
                        background: #3b42a1;
                    }
                </style>

                <div class="sorties-container">
            """

            sorties = rec.sortie_ids.sorted(lambda s: s.date_exit or "")

            groups = {}
            for s in sorties:
                w = s.week or "Sans semaine"
                groups.setdefault(w, []).append(s)

            for week, records in groups.items():
                total_week = sum(
                    r.mt_vente_final or r.mt_vente
                    for r in records
                )


                html += f"""
                    <div class="week-card">
                        <div class="week-header">
                            <div class="week-title">📅 Semaine {week}</div>
                            <div class="week-total">{total_week:,.2f} Dh</div>
                        </div>

                        <div class="table-header">
                            <div>Produit</div>
                            <div>Qté</div>
                            <div>Tonnage final</div>
                            <div>Prix final</div>
                            <div>Montant final</div>
                            <div>Date</div>
                            <div>Action</div>
                        </div>
                """

                for s in records:
                    popup_url = f"/web#action=&id={s.id}&model=kal3iyasortie&view_type=form&view_id=588"
                    html += f"""
                        <div class="list-row">
                            <div class="col-label">{s.name}</div>
                            <div class="col-value">{s.quantity}</div>
                            <div class="col-value">{s.tonnage_final or s.tonnage}</div>
                            <div class="col-value">{(s.selling_price_final or s.selling_price)} Dh</div>
                            <div class="col-value amount">{s.mt_vente_final or s.mt_vente} Dh</div>
                            <div class="col-value date">{s.date_exit}</div>
                            <div>
                                <button type="object" 
                                        name="action_open_popup"
                                        context="{{'active_id': {s.id}}}" 
                                        class="btn btn-sm btn-primary">
                                    ✏️ Modifier
                                </button>
                            </div>
                        </div>
                    """
                html += "</div>"  # fermer container principal
                rec.sorties_grouped_html = html
