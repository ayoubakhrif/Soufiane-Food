# -*- coding: utf-8 -*-

from odoo import models, fields, tools

class DashboardProfitClient(models.Model):
    _name = "dashboard.profit.client"
    _description = "Dashboard: Profit par Client"
    _auto = False  # Vue SQL, pas de table réelle
    _order = "profit desc"

    client_id = fields.Many2one('res.partner', string='Client', readonly=True)
    tonnage_sold = fields.Float(string='Tonnage Vendu (Kg)', readonly=True)
    mt_vente = fields.Float(string='Montant Ventes', readonly=True)
    mt_achat = fields.Float(string='Montant Achats', readonly=True)
    profit = fields.Float(string='Profit', readonly=True)
    profit_margin = fields.Float(string='Marge (%)', readonly=True)

    def init(self):
        """
        Créer la vue SQL qui agrège les données de ventes par client
        Adaptez cette requête selon votre structure de données
        """
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        # EXEMPLE DE REQUÊTE - À ADAPTER SELON VOTRE STRUCTURE
        query = """
            CREATE OR REPLACE VIEW dashboard_profit_client AS (
                SELECT 
                    ROW_NUMBER() OVER (ORDER BY SUM(sol.price_subtotal - sol.purchase_price * sol.product_uom_qty) DESC) as id,
                    so.partner_id as client_id,
                    SUM(sol.product_uom_qty) as tonnage_sold,
                    SUM(sol.price_subtotal) as mt_vente,
                    SUM(sol.purchase_price * sol.product_uom_qty) as mt_achat,
                    SUM(sol.price_subtotal - sol.purchase_price * sol.product_uom_qty) as profit,
                    CASE 
                        WHEN SUM(sol.price_subtotal) > 0 
                        THEN (SUM(sol.price_subtotal - sol.purchase_price * sol.product_uom_qty) / SUM(sol.price_subtotal)) * 100
                        ELSE 0 
                    END as profit_margin
                FROM 
                    sale_order_line sol
                    INNER JOIN sale_order so ON sol.order_id = so.id
                WHERE 
                    so.state IN ('sale', 'done')
                GROUP BY 
                    so.partner_id
            )
        """
        self.env.cr.execute(query)