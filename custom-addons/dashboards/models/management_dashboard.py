# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools

class ManagementDashboard(models.Model):
    _name = "management.dashboard"
    _description = "Executive Management Dashboard"

    name = fields.Char(string="Dashboard Name", required=True)
    dashboard_type = fields.Selection([
        ('profit_client', 'Profit by Client'),
        ('profit_product', 'Profit by Product'),
    ], string="Type", required=True)
    
    content_html = fields.Html(string="Dashboard Content", compute="_compute_content_html", sanitize=False)
    
    # --------------------------------------------------------
    # MAIN COMPUTE
    # --------------------------------------------------------
    @api.depends('dashboard_type')
    def _compute_content_html(self):
        for rec in self:
            if rec.dashboard_type == 'profit_client':
                rec.content_html = rec._render_profit_client()
            elif rec.dashboard_type == 'profit_product':
                rec.content_html = rec._render_profit_product()
            else:
                rec.content_html = "<div class='alert alert-info'>Select a dashboard type.</div>"

    # --------------------------------------------------------
    # RENDERERS
    # --------------------------------------------------------
    def _render_profit_client(self):
        # 1. Fetch Data (Already aggregated by SQL View)
        # Sort by Profit DESC
        records = self.env['dashboard.profit.client'].search([], order='profit desc')
        
        # 2. Calculate KPIs
        total_profit = sum(r.profit for r in records)
        total_tonnage = sum(r.tonnage_sold for r in records)
        
        best_client = records[0].client_id.name if records else "N/A"
        worst_client_rec = records[-1] if records else None
        worst_client = worst_client_rec.client_id.name if worst_client_rec else "N/A"
        
        # 3. Build HTML
        html = f"""
        <div style="font-family: 'Inter', sans-serif; padding: 20px; background-color: #f9fafb;">
            
            <!-- KPIs -->
            <div style="display: flex; gap: 20px; margin-bottom: 30px; flex-wrap: wrap;">
                {self._card("Total Profit", self._format_currency(total_profit), "bg-white border-l-4 border-green-500")}
                {self._card("Total Tonnage", f"{total_tonnage:,.0f} Kg", "bg-white border-l-4 border-blue-500")}
                {self._card("Best Client", best_client, "bg-white border-l-4 border-indigo-500")}
                {self._card("Worst Client", worst_client, "bg-white border-l-4 border-red-500")}
            </div>
            
            <!-- TITLE -->
            <div style="margin-bottom: 15px; font-size: 18px; font-weight: 600; color: #374151;">
                Client Profitability Ranking
            </div>

            <!-- TABLE -->
            <div style="background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow: hidden;">
                <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                    <thead style="background-color: #f3f4f6; border-bottom: 1px solid #e5e7eb;">
                        <tr>
                            <th style="text-align: left; padding: 12px 16px; font-weight: 600; color: #4b5563;">Client</th>
                            <th style="text-align: right; padding: 12px 16px; font-weight: 600; color: #4b5563;">Tonnage (Kg)</th>
                            <th style="text-align: right; padding: 12px 16px; font-weight: 600; color: #4b5563;">Sales</th>
                            <th style="text-align: right; padding: 12px 16px; font-weight: 600; color: #4b5563;">Cost</th>
                            <th style="text-align: right; padding: 12px 16px; font-weight: 600; color: #4b5563;">Margin %</th>
                            <th style="text-align: right; padding: 12px 16px; font-weight: 600; color: #4b5563;">Profit</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for rec in records:
            profit_color = "#16a34a" if rec.profit >= 0 else "#dc2626" # Green or Red
            
            html += f"""
                        <tr style="border-bottom: 1px solid #f3f4f6;">
                            <td style="padding: 12px 16px; color: #111827;">{rec.client_id.name or 'Unknown'}</td>
                            <td style="padding: 12px 16px; text-align: right; color: #6b7280;">{rec.tonnage_sold:,.0f}</td>
                            <td style="padding: 12px 16px; text-align: right; color: #6b7280;">{self._format_currency(rec.mt_vente)}</td>
                            <td style="padding: 12px 16px; text-align: right; color: #6b7280;">{self._format_currency(rec.mt_achat)}</td>
                             <td style="padding: 12px 16px; text-align: right; color: #6b7280;">{rec.profit_margin:.1f}%</td>
                            <td style="padding: 12px 16px; text-align: right; font-weight: 600; color: {profit_color};">
                                {self._format_currency(rec.profit)}
                            </td>
                        </tr>
            """
            
        html += """
                    </tbody>
                </table>
            </div>
        </div>
        """
        return html

    def _render_profit_product(self):
        # 1. Fetch Data
        records = self.env['dashboard.profit.product'].search([], order='profit desc')
        
        # 2. KPIs
        total_profit = sum(r.profit for r in records)
        total_tonnage = sum(r.tonnage_sold for r in records)
        best_product = records[0].product_id.name if records else "N/A"
        
        # 3. HTML
        html = f"""
        <div style="font-family: 'Inter', sans-serif; padding: 20px; background-color: #f9fafb;">
             <div style="display: flex; gap: 20px; margin-bottom: 30px; flex-wrap: wrap;">
                {self._card("Total Profit", self._format_currency(total_profit), "bg-white border-l-4 border-green-500")}
                {self._card("Total Tonnage", f"{total_tonnage:,.0f} Kg", "bg-white border-l-4 border-blue-500")}
                {self._card("Best Product", best_product, "bg-white border-l-4 border-indigo-500")}
            </div>
            
             <!-- TITLE -->
            <div style="margin-bottom: 15px; font-size: 18px; font-weight: 600; color: #374151;">
                Product Profitability Ranking
            </div>

            <div style="background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow: hidden;">
                <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                    <thead style="background-color: #f3f4f6; border-bottom: 1px solid #e5e7eb;">
                         <tr>
                            <th style="text-align: left; padding: 12px 16px; font-weight: 600; color: #4b5563;">Product</th>
                            <th style="text-align: right; padding: 12px 16px; font-weight: 600; color: #4b5563;">Tonnage (Kg)</th>
                            <th style="text-align: right; padding: 12px 16px; font-weight: 600; color: #4b5563;">Sales</th>
                            <th style="text-align: right; padding: 12px 16px; font-weight: 600; color: #4b5563;">Cost</th>
                            <th style="text-align: right; padding: 12px 16px; font-weight: 600; color: #4b5563;">Margin %</th>
                            <th style="text-align: right; padding: 12px 16px; font-weight: 600; color: #4b5563;">Profit</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        for rec in records:
            profit_color = "#16a34a" if rec.profit >= 0 else "#dc2626"
            html += f"""
                        <tr style="border-bottom: 1px solid #f3f4f6;">
                            <td style="padding: 12px 16px; color: #111827;">{rec.product_id.name}</td>
                            <td style="padding: 12px 16px; text-align: right; color: #6b7280;">{rec.tonnage_sold:,.0f}</td>
                            <td style="padding: 12px 16px; text-align: right; color: #6b7280;">{self._format_currency(rec.mt_vente)}</td>
                            <td style="padding: 12px 16px; text-align: right; color: #6b7280;">{self._format_currency(rec.mt_achat)}</td>
                             <td style="padding: 12px 16px; text-align: right; color: #6b7280;">{rec.profit_margin:.1f}%</td>
                            <td style="padding: 12px 16px; text-align: right; font-weight: 600; color: {profit_color};">
                                {self._format_currency(rec.profit)}
                            </td>
                        </tr>
            """
        html += "</tbody></table></div></div>"
        return html

    # --------------------------------------------------------
    # HELPERS
    # --------------------------------------------------------
    def _card(self, title, value, classes):
        return f"""
        <div class="{classes}" style="flex: 1; min-width: 200px; padding: 20px; border-radius: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
            <div style="font-size: 13px; font-weight: 500; color: #6b7280; text-transform: uppercase; margin-bottom: 8px;">{title}</div>
            <div style="font-size: 24px; font-weight: 700; color: #111827;">{value}</div>
        </div>
        """

    def _format_currency(self, amount):
        return f"{amount:,.2f}"


# -------------------------------------------------------------------------
#  RESTORED SQL VIEW MODELS (Required for data access/security)
# -------------------------------------------------------------------------

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
