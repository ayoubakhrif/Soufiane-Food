# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ManagementDashboard(models.Model):
    _name = "management.dashboard"
    _description = "Executive Management Dashboard"

    name = fields.Char(string="Dashboard Name", required=True)
    dashboard_type = fields.Selection([
        ('profit_client', 'Profit par Client'),
        ('profit_product', 'Profit par Produit'),
    ], string="Type", required=True)
    
    content_html = fields.Html(string="Contenu du Dashboard", compute="_compute_content_html", sanitize=False)
    
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
            bg_color = "transparent" # Can iterate for zebra striping if needed
            
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
        # Stub for now, can implement similarly
        return "<div class='p-4'>Profit by Product implementation pending.</div>"

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
        # Custom simple formatter: 1,234.56
        return f"{amount:,.2f}" # Standard Python format
