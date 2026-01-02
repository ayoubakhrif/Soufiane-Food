```
from odoo import models, fields, api

class CasaClient(models.Model):
    _name = 'casa.client'
    _description = 'Client Casa'
    
    name = fields.Char(string='Nom Client', required=True)
    
    # Financial Relations
    sale_ids = fields.One2many('casa.sale', 'client_id', string='Ventes')
    return_ids = fields.One2many('casa.sale.return', 'client_id', string='Retours')
    advance_ids = fields.One2many('casa.advance', 'client_id', string='Avances')
    unpaid_ids = fields.One2many('casa.unpaid', 'client_id', string='Impayés')
    sale_supp_ids = fields.One2many('casa.sale.supp', 'client_id', string='Sorties Supp')
    
    # Computed Balance
    compte = fields.Float(string='Compte', compute='_compute_compte', store=True)
    compte_initial = fields.Float(string='Compte Initial')
    
    # Dashboard Fields
    sorties_grouped_html = fields.Html(string="Sorties Groupées", compute="_compute_sorties_grouped_html", sanitize=False)
    retours_grouped_html = fields.Html(string="Retours Groupés", compute="_compute_retours_grouped_html", sanitize=False)
    
    @api.depends('sale_ids.mt_vente', 'sale_ids.mt_vente_final', 'advance_ids.amount', 
                 'return_ids.amount', 'unpaid_ids.amount', 'sale_supp_ids.amount', 'compte_initial')
    def _compute_compte(self):
        for rec in self:
            total_ventes = sum(s.mt_vente_final or s.mt_vente for s in rec.sale_ids)
            total_avances = sum(a.amount for a in rec.advance_ids)
            total_impayes = sum(u.amount for u in rec.unpaid_ids)
            total_supp = sum(s.amount for s in rec.sale_supp_ids)
            total_retours = sum(r.amount for r in rec.return_ids)
            
            rec.compte = total_ventes + total_impayes + total_supp - total_avances - total_retours + rec.compte_initial

    @api.depends('sale_ids', 'sale_ids.date', 'sale_ids.mt_vente_final', 'sale_ids.mt_vente')
    def _compute_sorties_grouped_html(self):
        for rec in self:
            html = """
                <style>
                    .sorties-container { font-family: sans-serif; padding: 10px; }
                    .week-card { background: white; border-radius: 12px; border: 2px solid #e2e8f0; padding: 18px; margin: 22px 0; box-shadow: 0 6px 20px rgba(0,0,0,0.06); }
                    .week-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
                    .week-title { font-size: 22px; font-weight: 700; color: #4c51bf; }
                    .week-total { background: #4c51bf; color: white; padding: 8px 18px; border-radius: 10px; font-weight: 700; }
                    .table-header { display: grid; grid-template-columns: 1.2fr 0.5fr 0.6fr 0.8fr 0.6fr 0.9fr 0.8fr; padding: 10px; background: #e2e8f0; font-weight: 700; margin-bottom: 10px; }
                    .list-row { display: grid; grid-template-columns: 1.2fr 0.5fr 0.6fr 0.8fr 0.6fr 0.9fr 0.8fr; padding: 12px 10px; background: #f7fafc; border-left: 4px solid #4c51bf; margin-bottom: 8px; }
                </style>
                <div class="sorties-container">
            """
            
            # Total Banner
            html += f"""
                <div style="text-align:center; margin-bottom:25px;">
                    <div style="font-size:26px; font-weight:800; color:#4c51bf; padding: 14px 28px; display:inline-block; background:#ebf4ff; border:2px solid #4c51bf; border-radius:14px;">
                        💰 Total Compte : {rec.compte:,.2f} Dh
                    </div>
                </div>
            """

            sales = rec.sale_ids.sorted(lambda s: s.date or "")
            groups = {}
            for s in sales:
                w = s.week or "Sans semaine"
                groups.setdefault(w, []).append(s)

            for week, records in groups.items():
                total_week = sum(r.mt_vente_final or r.mt_vente for r in records)
                
                html += f"""
                    <div class="week-card">
                        <div class="week-header">
                            <div class="week-title">📅 Semaine {week}</div>
                            <div class="week-total">{total_week:,.2f} Dh</div>
                        </div>
                        <div class="table-header">
                            <div>Produit</div> <div>Qté</div> <div>Poids</div> <div>Tonnage</div> <div>Prix</div> <div>Montant</div> <div>Date</div>
                        </div>
                """
                
                for s in records:
                    html += f"""
                        <div class="list-row">
                            <div>{s.product_id.name}</div>
                            <div>{s.quantity}</div>
                            <div>{s.weight}</div>
                            <div>{s.tonnage_final or s.tonnage:.0f}</div>
                            <div>{(s.selling_price_final or s.selling_price):.2f} Dh</div>
                            <div style="color:#4c51bf; font-weight:700;">{(s.mt_vente_final or s.mt_vente):.2f} Dh</div>
                            <div>{s.date}</div>
                        </div>
                    """
                html += "</div>"
            
            html += "</div>"
            rec.sorties_grouped_html = html

    @api.depends('return_ids', 'return_ids.date', 'return_ids.amount')
    def _compute_retours_grouped_html(self):
        for rec in self:
            html = """
                <style>
                    .retours-container { font-family: sans-serif; padding: 10px; }
                    .retour-card { background: white; border-radius: 12px; border: 2px solid #feb2b2; padding: 18px; margin: 22px 0; }
                    .retour-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
                    .retour-title { font-size: 22px; font-weight: 700; color: #e53e3e; }
                    .retour-total { background: #e53e3e; color: white; padding: 8px 18px; border-radius: 10px; font-weight: 700; }
                    .table-header-ret { display: grid; grid-template-columns: 1.2fr 0.5fr 0.6fr 0.8fr 0.8fr 0.8fr; padding: 10px; background: #fed7d7; font-weight: 700; margin-bottom: 10px; }
                    .list-row-ret { display: grid; grid-template-columns: 1.2fr 0.5fr 0.6fr 0.8fr 0.8fr 0.8fr; padding: 12px 10px; background: #fff5f5; border-left: 4px solid #e53e3e; margin-bottom: 8px; }
                </style>
                <div class="retours-container">
            """
            
            returns = rec.return_ids.sorted(lambda r: r.date or "")
            groups = {}
            for r in returns:
                w = r.week or "Sans semaine"
                groups.setdefault(w, []).append(r)

            for week, records in groups.items():
                total_week = sum(r.amount for r in records)
                
                html += f"""
                    <div class="retour-card">
                        <div class="retour-header">
                            <div class="retour-title">🔄 Retours – Semaine {week}</div>
                            <div class="retour-total">{total_week:,.2f} Dh</div>
                        </div>
                        <div class="table-header-ret">
                            <div>Produit</div> <div>Qté</div> <div>Poids</div> <div>Tonnage</div> <div>Prix</div> <div>Montant</div>
                        </div>
                """
                
                for r in records:
                    html += f"""
                        <div class="list-row-ret">
                            <div>{r.product_id.name}</div>
                            <div>{r.quantity}</div>
                            <div>{r.weight}</div>
                            <div>{r.tonnage}</div>
                            <div>{r.price_unit:.2f} Dh</div>
                            <div style="color:#e53e3e; font-weight:700;">{r.amount:.2f} Dh</div>
                        </div>
                    """
                html += "</div>"
            
            html += "</div>"
            rec.retours_grouped_html = html
```
