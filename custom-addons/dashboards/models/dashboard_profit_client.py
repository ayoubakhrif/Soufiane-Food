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
        # Le code ci-dessous utilise le module standard 'sale', que vous ne souhaitez pas utiliser.
        # Veuillez adapter cette vue pour utiliser vos modules personnalisés (ex: kal3iya, casa_stock).
        # Pour l'instant, nous désactivons cette vue pour éviter les erreurs.
        
        query = """
            CREATE OR REPLACE VIEW dashboard_profit_client AS (
                SELECT 
                    0 as id,
                    null as client_id,
                    0.0 as tonnage_sold,
                    0.0 as mt_vente,
                    0.0 as mt_achat,
                    0.0 as profit,
                    0.0 as profit_margin
            )
        """
        self.env.cr.execute(query)