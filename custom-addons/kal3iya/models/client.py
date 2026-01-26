from odoo import models, fields, api
from odoo.exceptions import UserError

class Kal3iyaClient(models.Model):
    _name = 'kal3iya.client'
    _description = 'Clients'

    name = fields.Char(string='Client', required=True)

    # Lignes de sorties automatiquement calculées
    sortie_ids = fields.One2many(
        'kal3iyasortie',
        'client_id',
        string='Sorties de ce client',
    )

    sortie_count = fields.Integer(
        string="Nombre de commandes",
        compute='_compute_sortie_count',
        store=True
    )

    sorties_grouped_html = fields.Html(
        string="Sorties groupées",
        compute="_compute_sorties_grouped_html",
        sanitize=False,
    )

    retours_grouped_html = fields.Html(
        string="Retours groupés",
        compute="_compute_retours_grouped_html",
        sanitize=False,
    )


    is_internal = fields.Boolean(default=False)
    avances = fields.One2many('kal3iya.advance', 'client_id', string='Avances')
    unpaid_ids = fields.One2many('kal3iya.unpaid', 'client_id', string='Impayés')
    sortie_supp_ids = fields.One2many('kal3iya.sortie.supp', 'client_id', string='Sorties supp')
    compte = fields.Float(readonly=True, compute='_compute_compte', store=True)
    compte_initial = fields.Float(string='Compte initial')

    @api.depends('sortie_ids')
    def _compute_sortie_count(self):
            for rec in self:
                rec.sortie_count = len(rec.sortie_ids)



    # Lignes de retours automatiquement calculées
    retour_ids = fields.One2many(
        'kal3iyaentry',
        'client_id',
        string='Retours de ce client',
    )

    retour_count = fields.Integer(
        string="Nombre de retours",
        compute='_compute_retour_count',
        store=True
    )


    @api.depends('retour_ids')
    def _compute_retour_count(self):
        for rec in self:
            rec.retour_count = len(rec.retour_ids)

    def write(self, vals):
        for rec in self:
            # si tentative de modification et non création
            if 'compte_initial' in vals:
                # Seul le responsable peut modifier le compte initial
                if rec.id and not self.env.user.has_group('kal3iya.group_kal3iya_responsible'):
                    raise UserError("Impossible de modifier le compte initial après création. Contactez un responsable.")
        return super().write(vals)



    @api.depends(
        'sortie_ids.mt_vente',
        'sortie_ids.mt_vente_final',
        'sortie_ids.tonnage',
        'sortie_ids.tonnage_final',
        'avances.amount',
        'retour_ids.selling_price',
        'retour_ids.tonnage',
        'unpaid_ids.amount',
        'sortie_supp_ids.amount',
        'retour_ids.state',
        'compte_initial'
    )
    def _compute_compte(self):
        """Compte = ventes + impayés - avances - retours + initial"""
        for client in self:
            # 💰 Total des ventes
            sorties = client.sortie_ids.filtered(
                lambda s: s.client_id.name != 'Transfert interne'
            )            
            total_ventes = sum(s.mt_vente_final or s.mt_vente for s in client.sortie_ids)

            # 💵 Total des avances
            total_avances = sum(client.avances.mapped('amount'))

            # 🚨 Total des impayés
            total_impayes = sum(client.unpaid_ids.mapped('amount'))
            total_sortie_supp = sum(client.sortie_supp_ids.mapped('amount'))

            # 🔄 Total des retours (entrées avec state='retour')
            retours = client.retour_ids.filtered(lambda r: r.state == 'retour')
            total_retours = sum(r.selling_price*r.tonnage for r in retours)

            # 🧮 Calcul final (Ajout des impayés et sorties supp au dû client)
            client.compte = total_ventes + total_impayes + total_sortie_supp - total_avances - total_retours + client.compte_initial

    @api.depends(
    'sortie_ids',
    'sortie_ids.product_id',
    'sortie_ids.quantity',
    'sortie_ids.weight',
    'sortie_ids.tonnage_final',
    'sortie_ids.tonnage',
    'sortie_ids.selling_price_final',
    'sortie_ids.selling_price',
    'sortie_ids.date_exit',
    'sortie_ids.week',
    'compte',
    'sortie_ids.selling_price'
    )
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
                        grid-template-columns: 1.2fr 0.5fr 0.6fr 0.8fr 0.6fr 0.9fr 0.8fr 0.8fr;
                        padding: 10px;
                        background: #e2e8f0;
                        border-radius: 8px;
                        font-weight: 700;
                        color: #2d3748;
                        margin-bottom: 10px;
                    }

                    .list-row {
                        display: grid;
                        grid-template-columns: 1.2fr 0.5fr 0.6fr 0.8fr 0.6fr 0.9fr 0.8fr 0.8fr;
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
            html += f"""
                <div style="width:100%; text-align:center; margin-bottom:25px;">
                    <div style="
                        font-size:26px;
                        font-weight:800;
                        color:#4c51bf;
                        padding: 14px 28px;
                        display:inline-block;
                        background:#ebf4ff;
                        border:2px solid #4c51bf;
                        border-radius:14px;
                        box-shadow:0 4px 14px rgba(76,81,191,0.25);
                    ">
                        💰 Total Compte : {rec.compte:,.2f} Dh
                    </div>
                </div>
            """



            sorties = rec.sortie_ids.sorted(lambda s: s.date_exit or "")

            groups = {}
            for s in sorties:
                w = s.week or "Sans semaine"
                groups.setdefault(w, []).append(s)

            # Action de liste pour modification
            list_action = self.env.ref('kal3iya.action_kal3iya_week_update_list')
            list_action_id = list_action.id if list_action else False
            
            import urllib.parse
            import json

            for week, records in groups.items():
                total_week = sum(
                    r.mt_vente_final or r.mt_vente
                    for r in records
                )

                # URL vers la vue liste filtrée
                # On passe le contexte dans l'URL pour que l'action l'utilise dans son domain
                wizard_url = "#"
                if list_action_id:
                    # Gérer le cas "Sans semaine" -> pas de semaine (False)
                    search_week = week if week != "Sans semaine" else False
                    
                    # Construction du contexte
                    ctx = {
                        'target_week': search_week,
                        'target_client_id': rec.id,
                    }
                    
                    # Serialize to JSON and then URL encode
                    ctx_json = json.dumps(ctx)
                    ctx_encoded = urllib.parse.quote(ctx_json)
                    
                    # On utilise &context=... au lieu de &domain=...
                    wizard_url = f"/web#action={list_action_id}&model=kal3iyasortie&view_type=list&context={ctx_encoded}"

                html += f"""
                    <div class="week-card">
                        <div class="week-header">
                            <div class="week-title">
                                📅 Semaine {week}
                                <a href="{wizard_url}" 
                                   class="edit-btn oe_kanban_action oe_kanban_global_click"
                                   style="margin-left: 15px; font-size: 14px; padding: 5px 12px; background: #667eea;">
                                   ✏️ Modifier la semaine
                                </a>
                            </div>
                            <div class="week-total">{total_week:,.2f} Dh</div>
                        </div>

                        <div class="table-header" style="grid-template-columns: 1.2fr 0.5fr 0.6fr 0.8fr 0.6fr 0.9fr 0.8fr;">
                            <div>Produit</div>
                            <div>Qté</div>
                            <div>Poids(Kg)</div>
                            <div>Tonnage final</div>
                            <div>Prix final</div>
                            <div>Montant final</div>
                            <div>Date</div>
                        </div>
                """

                for s in records:
                    html += f"""
                        <div class="list-row" style="grid-template-columns: 1.2fr 0.5fr 0.6fr 0.8fr 0.6fr 0.9fr 0.8fr;">
                            <div class="col-label">{s.product_id.name}</div>
                            <div class="col-value">{s.quantity}</div>
                            <div class="col-value">{s.weight}</div>
                            <div class="col-value">{s.tonnage_final or s.tonnage}</div>
                            <div class="col-value">{(s.selling_price_final or s.selling_price)} Dh</div>
                            <div class="col-value amount">{s.mt_vente_final or s.mt_vente} Dh</div>
                            <div class="col-value date">{s.date_exit}</div>
                        </div>
                    """

                html += "</div>"

            html += "</div>"
            rec.sorties_grouped_html = html

    @api.depends(
        'retour_ids',
        'retour_ids.product_id',
        'retour_ids.quantity',
        'retour_ids.weight',
        'retour_ids.tonnage',
        'retour_ids.selling_price',
        'retour_ids.date_entry',
    )
    def _compute_retours_grouped_html(self):
        for rec in self:
            html = """
                <style>
                    .retours-container {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                        max-width: 100%;
                        padding: 10px;
                    }

                    .retour-card {
                        background: white;
                        border-radius: 12px;
                        border: 2px solid #feb2b2;
                        padding: 18px;
                        margin: 22px 0;
                        box-shadow: 0 6px 20px rgba(0,0,0,0.06);
                    }

                    .retour-header {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        margin-bottom: 15px;
                        flex-wrap: wrap;
                    }

                    .retour-title {
                        font-size: 22px;
                        font-weight: 700;
                        color: #e53e3e;
                    }

                    .retour-total {
                        background: #e53e3e;
                        color: white;
                        padding: 8px 18px;
                        border-radius: 10px;
                        font-size: 17px;
                        font-weight: 700;
                        box-shadow: 0 4px 12px rgba(229,62,62,0.3);
                    }

                    .table-header {
                        display: grid;
                        grid-template-columns: 1.2fr 0.5fr 0.6fr 0.8fr 0.8fr 0.8fr;
                        padding: 10px;
                        background: #fed7d7;
                        border-radius: 8px;
                        font-weight: 700;
                        color: #2d3748;
                        margin-bottom: 10px;
                    }

                    .list-row {
                        display: grid;
                        grid-template-columns: 1.2fr 0.5fr 0.6fr 0.8fr 0.8fr 0.8fr;
                        padding: 12px 10px;
                        background: #fff5f5;
                        border-radius: 8px;
                        margin-bottom: 8px;
                        border-left: 4px solid #e53e3e;
                        transition: 0.2s ease;
                    }
                    .list-row:hover {
                        background: #fed7d7;
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
                        color: #e53e3e;
                        font-weight: 700;
                    }

                    .date {
                        font-size: 14px;
                        color: #c53030;
                    }

                </style>

                <div class="retours-container">
            """

            # Trier par date
            retours = rec.retour_ids.sorted(lambda r: r.date_entry or "")

            # Regroupement par semaine
            groups = {}
            for r in retours:
                week = r.week if hasattr(r, 'week') and r.week else "Sans semaine"
                groups.setdefault(week, []).append(r)

            # Construire les cartes
            for week, records in groups.items():

                total_week = sum(r.selling_price * r.tonnage for r in records)

                html += f"""
                    <div class="retour-card">
                        <div class="retour-header">
                            <div class="retour-title">🔄 Retours – Semaine {week}</div>
                            <div class="retour-total">{total_week:,.2f} Dh</div>
                        </div>

                        <div class="table-header">
                            <div>Produit</div>
                            <div>Qté</div>
                            <div>Poids(Kg)</div>
                            <div>Tonnage</div>
                            <div>Prix</div>
                            <div>Montant</div>
                        </div>
                """

                for r in records:
                    mt_total = r.selling_price * r.tonnage

                    html += f"""
                        <div class="list-row">
                            <div class="col-label">{r.product_id.name}</div>
                            <div class="col-value">{r.quantity}</div>
                            <div class="col-value">{r.weight}</div>
                            <div class="col-value">{r.tonnage}</div>
                            <div class="col-value">{r.selling_price} Dh</div>
                            <div class="col-value amount">{mt_total} Dh</div>
                        </div>
                    """

                html += "</div>"

            html += "</div>"
            rec.retours_grouped_html = html

    # ==============================
    #  🧮 Utilitaire pour le rapport
    # ==============================

    def _get_week_data(self, week):
        """
        Retourne un dict avec tous les totaux pour une semaine donnée.
        week : string au format 'YYYY-Www' (ex: '2025-W48')
        Utilisé par le rapport (QWeb).
        """
        from datetime import datetime, timedelta
        
        self.ensure_one()

        # 1️⃣ Filtrer sorties de la semaine
        sorties = self.sortie_ids.filtered(lambda s: s.week == week)
        total_sorties = sum((s.mt_vente_final or s.mt_vente or 0.0) for s in sorties)

        # 2️⃣ Filtrer retours de la semaine (state = 'retour')
        retours = self.retour_ids.filtered(
            lambda r: r.week == week and r.state == 'retour'
        )
        total_retours = sum((r.selling_price or 0.0) * (r.tonnage or 0.0) for r in retours)

        # 3️⃣ Filtrer avances de la semaine (en se basant sur la date)
        avances = self.avances.filtered(
            lambda a: a.date_paid and a.date_paid.strftime("%Y-W%W") == week
        )
        total_avances = sum(avances.mapped('amount'))

        # 4️⃣ Compte de la semaine
        compte_semaine = total_sorties - total_retours - total_avances

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
            # En cas d'erreur, laisser vide
            pass

        return {
            'week': week,
            'start_date': start_date,
            'end_date': end_date,
            'sorties': sorties,
            'retours': retours,
            'avances': avances,
            'total_sorties': total_sorties,
            'total_retours': total_retours,
            'total_avances': total_avances,
            'compte_semaine': compte_semaine,
            'compte_total': self.compte,
        }
