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
            html = ""
            sorties = rec.sortie_ids.sorted(lambda s: s.date_exit or "")

            # Regroupement par semaine
            groups = {}
            for s in sorties:
                w = s.week or "Sans semaine"
                groups.setdefault(w, []).append(s)

            # Construction du HTML amélioré
            for week, records in groups.items():

                # Total ventes de la semaine
                total_week = sum(r.mt_vente for r in records)

                html += f"""
                    <div style="
                        padding:18px; 
                        margin:18px 0; 
                        border:2px solid #d9d9d9; 
                        border-radius:12px; 
                        background:#f8f9fa;
                        box-shadow:0 2px 6px rgba(0,0,0,0.06);
                    ">
                        <h3 style="
                            margin:0 0 12px 0; 
                            color:#5a2ca0; 
                            font-size:20px;
                            font-weight:700;
                            display:flex;
                            justify-content:space-between;
                            align-items:center;
                        ">
                            <span>📅 Semaine {week}</span>
                            <span style="
                                font-size:18px;
                                color:#155724;
                                background:#d4edda;
                                padding:4px 10px;
                                border-radius:8px;
                                font-weight:600;
                            ">
                                Total : {total_week:,.2f} Dh
                            </span>
                        </h3>

                        <div style="
                            display:grid; 
                            grid-template-columns:repeat(auto-fill, minmax(260px, 1fr)); 
                            gap:12px;
                            margin-top:10px;
                        ">
                """

                # Cartes pour chaque produit
                for s in records:
                    html += f"""
                        <div style="
                            background:white;
                            border:1px solid #e2e2e2; 
                            border-radius:10px; 
                            padding:12px;
                            box-shadow:0 1px 4px rgba(0,0,0,0.05);
                        ">
                            <div style="font-size:16px; font-weight:700; color:#333;">
                                {s.name}
                            </div>
                            <div style="margin-top:6px; font-size:14px; color:#555;">
                                Qté : <b>{s.quantity}</b><br/>
                                Prix : <b>{s.selling_price}</b><br/>
                                Mt : <b style="color:#0069d9;">{s.mt_vente}</b><br/>
                                Date : {s.date_exit}
                            </div>
                        </div>
                    """

                html += """
                        </div>
                    </div>
                """

            rec.sorties_grouped_html = html

