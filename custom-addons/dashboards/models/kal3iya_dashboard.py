# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools

class DashboardKal3iyaInventory(models.Model):
    _name = "dashboard.kal3iya.inventory"
    _description = "Kal3iya Inventory Dashboard"
    _auto = False
    _rec_name = 'product_id'
    _order = 'mt_achat desc'

    product_id = fields.Many2one('kal3iya.product', string='Produit', readonly=True)
    ville = fields.Selection([
        ('tanger', 'Tanger'),
        ('casa', 'Casa'),
    ], string='Ville', readonly=True)
    frigo = fields.Selection([
        ('frigo1', 'Frigo 1'),
        ('frigo2', 'Frigo 2'),
        ('stock_casa', 'Stock'),
    ], string='Frigo', readonly=True)
    
    quantity = fields.Float(string='Quantité', readonly=True)
    tonnage = fields.Float(string='Tonnage (Kg)', readonly=True)
    mt_achat = fields.Float(string='Valeur Stock (Achat)', readonly=True)
    
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    min(s.id) as id,
                    s.product_id,
                    s.ville,
                    s.frigo,
                    sum(s.quantity) as quantity,
                    sum(s.tonnage) as tonnage,
                    sum(s.mt_achat) as mt_achat
                FROM
                    kal3iya_stock s
                WHERE
                    s.quantity > 0 AND s.active = true
                GROUP BY
                    s.product_id,
                    s.ville,
                    s.frigo
            )
        """ % self._table)


class DashboardKal3iyaPerformance(models.Model):
    _name = "dashboard.kal3iya.performance"
    _description = "Kal3iya Sales Performance"
    _auto = False
    _rec_name = 'product_id'
    _order = 'date_exit desc'

    date_exit = fields.Date(string='Date Sortie', readonly=True)
    product_id = fields.Many2one('kal3iya.product', string='Produit', readonly=True)
    client_id = fields.Many2one('kal3iya.client', string='Client', readonly=True)
    ville = fields.Selection([
        ('tanger', 'Tanger'),
        ('casa', 'Casa'),
    ], string='Ville', readonly=True)
    
    tonnage = fields.Float(string='Tonnage Vendu', readonly=True)
    mt_vente = fields.Float(string='Chiffre d\'Affaires', readonly=True)
    mt_achat = fields.Float(string='Coût Achat', readonly=True)
    diff = fields.Float(string='Marge (Bérif/Perte)', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    s.id as id,
                    s.date_exit,
                    s.product_id,
                    s.client_id,
                    s.ville,
                    s.tonnage,
                    s.mt_vente,
                    s.mt_achat,
                    s.diff
                FROM
                    kal3iyasortie s
            )
        """ % self._table)


class DashboardProfitClient(models.Model):
    _name = "dashboard.profit.client"
    _description = "Profitability by Client"
    _auto = False
    _order = 'profit desc'

    client_id = fields.Many2one('kal3iya.client', string='Client', readonly=True)
    tonnage_sold = fields.Float(string='Tonnage Vendu (Kg)', readonly=True)
    mt_vente = fields.Float(string='Total Ventes', readonly=True)
    mt_achat = fields.Float(string='Total Achat', readonly=True)
    profit = fields.Float(string='Marge (Profit)', readonly=True)
    profit_margin = fields.Float(string='Marge (%)', readonly=True, group_operator="avg")

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    min(s.id) as id,
                    s.client_id,
                    sum(s.tonnage) as tonnage_sold,
                    sum(COALESCE(s.mt_vente_final, s.mt_vente)) as mt_vente,
                    sum(s.mt_achat) as mt_achat,
                    sum(COALESCE(s.mt_vente_final, s.mt_vente) - s.mt_achat) as profit,
                    CASE 
                        WHEN sum(COALESCE(s.mt_vente_final, s.mt_vente)) != 0 
                        THEN (sum(COALESCE(s.mt_vente_final, s.mt_vente) - s.mt_achat) / sum(COALESCE(s.mt_vente_final, s.mt_vente))) * 100 
                        ELSE 0 
                    END as profit_margin
                FROM
                    kal3iyasortie s
                GROUP BY
                    s.client_id
                HAVING
                    sum(COALESCE(s.mt_vente_final, s.mt_vente) - s.mt_achat) IS NOT NULL
            )
        """ % self._table)


class DashboardProfitProduct(models.Model):
    _name = "dashboard.profit.product"
    _description = "Profitability by Product"
    _auto = False
    _order = 'profit desc'

    product_id = fields.Many2one('kal3iya.product', string='Produit', readonly=True)
    tonnage_sold = fields.Float(string='Tonnage Vendu (Kg)', readonly=True)
    mt_vente = fields.Float(string='Total Ventes', readonly=True)
    mt_achat = fields.Float(string='Total Achat', readonly=True)
    profit = fields.Float(string='Marge (Profit)', readonly=True)
    profit_margin = fields.Float(string='Marge (%)', readonly=True, group_operator="avg")

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    min(s.id) as id,
                    s.product_id,
                    sum(s.tonnage) as tonnage_sold,
                    sum(COALESCE(s.mt_vente_final, s.mt_vente)) as mt_vente,
                    sum(s.mt_achat) as mt_achat,
                    sum(COALESCE(s.mt_vente_final, s.mt_vente) - s.mt_achat) as profit,
                    CASE 
                        WHEN sum(COALESCE(s.mt_vente_final, s.mt_vente)) != 0 
                        THEN (sum(COALESCE(s.mt_vente_final, s.mt_vente) - s.mt_achat) / sum(COALESCE(s.mt_vente_final, s.mt_vente))) * 100 
                        ELSE 0 
                    END as profit_margin
                FROM
                    kal3iyasortie s
                GROUP BY
                    s.product_id
                HAVING
                    sum(COALESCE(s.mt_vente_final, s.mt_vente) - s.mt_achat) IS NOT NULL
            )
        """ % self._table)
