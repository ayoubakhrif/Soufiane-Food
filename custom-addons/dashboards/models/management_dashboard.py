# -*- coding: utf-8 -*-

from datetime import datetime
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
        """Render Client Profitability Dashboard"""
        # 1. Fetch Data (Already aggregated by SQL View)
        records = self.env['dashboard.profit.client'].search([], order='profit desc')
        
        # 2. Calculate KPIs
        total_profit = sum(r.profit for r in records)
        total_tonnage = sum(r.tonnage_sold for r in records)
        
        best_client = records[0].client_id.name if records else "N/A"
        worst_client = records[-1].client_id.name if len(records) > 1 else "N/A"
        
        # Calculate average margin
        avg_margin = sum(r.profit_margin for r in records) / len(records) if records else 0
        
        # 3. Build HTML
        html = f"""
        <div style="font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 24px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh;">
            
            <!-- Header -->
            <div style="margin-bottom: 32px;">
                <h2 style="color: white; font-size: 28px; font-weight: 700; margin: 0 0 8px 0; text-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    📈 Client Performance Dashboard
                </h2>
                <p style="color: rgba(255,255,255,0.9); margin: 0; font-size: 14px;">
                    Analyse complète de la rentabilité et des performances par client
                </p>
            </div>
            
            <!-- KPIs Grid -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; margin-bottom: 32px;">
                
                {self._render_kpi_card("Total Profit", self._format_currency(total_profit), "💰", "#10b981", "#059669", True)}
                {self._render_kpi_card("Total Tonnage", f"{total_tonnage:,.0f} Kg", "📦", "#3b82f6", "#2563eb", False)}
                {self._render_kpi_card("Best Client", best_client, "🏆", "#8b5cf6", "#7c3aed", False)}
                {self._render_kpi_card("Needs Attention", worst_client, "⚠️", "#ef4444", "#dc2626", False)}
                
            </div>
            
            <!-- Stats Bar -->
            <div style="background: rgba(255,255,255,0.95); border-radius: 12px; padding: 16px 24px; margin-bottom: 32px; box-shadow: 0 4px 6px rgba(0,0,0,0.07); display: flex; justify-content: space-around; flex-wrap: wrap; gap: 20px;">
                <div style="text-align: center;">
                    <div style="font-size: 24px; font-weight: 700; color: #111827;">{len(records)}</div>
                    <div style="font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">Total Clients</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 24px; font-weight: 700; color: #8b5cf6;">{avg_margin:.1f}%</div>
                    <div style="font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">Avg Margin</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 24px; font-weight: 700; color: #10b981;">{len([r for r in records if r.profit > 0])}</div>
                    <div style="font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">Profitable</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 24px; font-weight: 700; color: #ef4444;">{len([r for r in records if r.profit < 0])}</div>
                    <div style="font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">Loss-Making</div>
                </div>
            </div>
            
            <!-- Table Section -->
            <div style="background: white; border-radius: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.07), 0 10px 20px rgba(0,0,0,0.1); overflow: hidden;">
                
                <!-- Table Header -->
                <div style="padding: 24px 24px 16px 24px; border-bottom: 2px solid #f3f4f6;">
                    <h3 style="margin: 0; font-size: 20px; font-weight: 700; color: #111827; display: flex; align-items: center; gap: 8px;">
                        <span>📊</span> Client Profitability Ranking
                    </h3>
                    <p style="margin: 4px 0 0 0; color: #6b7280; font-size: 13px;">
                        Classé par contribution au profit • {len(records)} clients
                    </p>
                </div>
                
                <!-- Table -->
                <div style="overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                        <thead>
                            <tr style="background: linear-gradient(180deg, #f9fafb 0%, #f3f4f6 100%); border-bottom: 2px solid #e5e7eb;">
                                <th style="text-align: left; padding: 16px 24px; font-weight: 600; color: #374151; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Rank</th>
                                <th style="text-align: left; padding: 16px 24px; font-weight: 600; color: #374151; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Client</th>
                                <th style="text-align: right; padding: 16px 24px; font-weight: 600; color: #374151; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Tonnage</th>
                                <th style="text-align: right; padding: 16px 24px; font-weight: 600; color: #374151; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Ventes</th>
                                <th style="text-align: right; padding: 16px 24px; font-weight: 600; color: #374151; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Coûts</th>
                                <th style="text-align: right; padding: 16px 24px; font-weight: 600; color: #374151; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Marge</th>
                                <th style="text-align: right; padding: 16px 24px; font-weight: 600; color: #374151; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Profit</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        
        # Render table rows
        for idx, rec in enumerate(records, 1):
            html += self._render_table_row(idx, rec)
            
        html += f"""
                        </tbody>
                    </table>
                </div>
                
                <!-- Table Footer -->
                <div style="padding: 16px 24px; background-color: #f9fafb; border-top: 2px solid #e5e7eb; text-align: center;">
                    <span style="color: #6b7280; font-size: 12px;">
                        📅 Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}
                    </span>
                </div>
                
            </div>
        </div>
        """
        return html

    def _render_profit_product(self):
        """Render Product Profitability Dashboard"""
        records = self.env['dashboard.profit.product'].search([], order='profit desc')
        
        if not records:
            return """
            <div style="font-family: 'Inter', sans-serif; padding: 40px; text-align: center;">
                <div style="font-size: 48px; margin-bottom: 16px;">📦</div>
                <h3 style="color: #6b7280; margin: 0;">Aucune donnée disponible</h3>
                <p style="color: #9ca3af; margin-top: 8px;">Les données de profit par produit seront affichées ici.</p>
            </div>
            """
        
        total_profit = sum(r.profit for r in records)
        total_qty = sum(r.qty_sold for r in records)
        
        return f"""
        <div style="font-family: 'Inter', sans-serif; padding: 24px; background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); min-height: 100vh;">
            <div style="margin-bottom: 32px;">
                <h2 style="color: white; font-size: 28px; font-weight: 700; margin: 0 0 8px 0;">
                    📦 Product Profitability Dashboard
                </h2>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px;">
                {self._render_kpi_card("Total Profit", self._format_currency(total_profit), "💰", "#10b981", "#059669", True)}
                {self._render_kpi_card("Total Quantity", f"{total_qty:,.0f}", "📦", "#3b82f6", "#2563eb", False)}
                {self._render_kpi_card("Products", str(len(records)), "🏷️", "#8b5cf6", "#7c3aed", False)}
            </div>
        </div>
        """

    # --------------------------------------------------------
    # HELPERS
    # --------------------------------------------------------
    def _render_kpi_card(self, title, value, icon, color1, color2, is_currency):
        """Render a KPI card with consistent styling"""
        return f"""
        <div style="background: white; border-radius: 16px; padding: 24px; box-shadow: 0 4px 6px rgba(0,0,0,0.07), 0 10px 20px rgba(0,0,0,0.1); position: relative; overflow: hidden;">
            <div style="position: absolute; top: -20px; right: -20px; width: 80px; height: 80px; background: linear-gradient(135deg, {color1}, {color2}); border-radius: 50%; opacity: 0.1;"></div>
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                <span style="color: #6b7280; font-size: 13px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;">{title}</span>
                <span style="font-size: 24px;">{icon}</span>
            </div>
            <div style="font-size: {'28px' if is_currency else '20px'}; font-weight: {'700' if is_currency else '600'}; color: {color1}; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{value}">
                {value}
            </div>
            <div style="height: 3px; width: 40px; background: linear-gradient(90deg, {color1}, {color2}); border-radius: 2px;"></div>
        </div>
        """

    def _render_table_row(self, idx, rec):
        """Render a single table row with all formatting"""
        profit_color = "#10b981" if rec.profit >= 0 else "#ef4444"
        profit_bg = "rgba(16, 185, 129, 0.1)" if rec.profit >= 0 else "rgba(239, 68, 68, 0.1)"
        bg_color = "#fafafa" if idx % 2 == 0 else "white"
        
        # Rank medal
        rank_icon = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}"
        
        # Progress bar for margin
        margin_width = min(abs(rec.profit_margin), 100)
        margin_bar_color = "#10b981" if rec.profit_margin >= 0 else "#ef4444"
        
        return f"""
        <tr style="border-bottom: 1px solid #f3f4f6; background-color: {bg_color}; transition: background-color 0.2s;" onmouseover="this.style.backgroundColor='#f9fafb'" onmouseout="this.style.backgroundColor='{bg_color}'">
            <td style="padding: 16px 24px; text-align: center; font-size: 18px;">
                {rank_icon}
            </td>
            <td style="padding: 16px 24px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #667eea, #764ba2); display: flex; align-items: center; justify-content: center; color: white; font-weight: 700; font-size: 14px; flex-shrink: 0;">
                        {(rec.client_id.name or 'U')[0].upper()}
                    </div>
                    <span style="font-weight: 600; color: #111827;">{rec.client_id.name or 'Unknown'}</span>
                </div>
            </td>
            <td style="padding: 16px 24px; text-align: right;">
                <span style="color: #6b7280; font-weight: 500;">{rec.tonnage_sold:,.0f}</span>
                <span style="color: #9ca3af; font-size: 12px; margin-left: 4px;">Kg</span>
            </td>
            <td style="padding: 16px 24px; text-align: right; color: #111827; font-weight: 500;">
                {self._format_currency(rec.mt_vente)}
            </td>
            <td style="padding: 16px 24px; text-align: right; color: #6b7280; font-weight: 500;">
                {self._format_currency(rec.mt_achat)}
            </td>
            <td style="padding: 16px 24px; text-align: right;">
                <div style="display: flex; align-items: center; justify-content: flex-end; gap: 8px;">
                    <div style="width: 60px; height: 6px; background-color: #f3f4f6; border-radius: 3px; overflow: hidden;">
                        <div style="height: 100%; width: {margin_width}%; background-color: {margin_bar_color}; border-radius: 3px; transition: width 0.3s;"></div>
                    </div>
                    <span style="color: #6b7280; font-weight: 600; min-width: 45px;">{rec.profit_margin:.1f}%</span>
                </div>
            </td>
            <td style="padding: 16px 24px; text-align: right;">
                <div style="display: inline-block; padding: 6px 12px; background-color: {profit_bg}; border-radius: 8px;">
                    <span style="font-weight: 700; color: {profit_color};">
                        {self._format_currency(rec.profit)}
                    </span>
                </div>
            </td>
        </tr>
        """

    def _format_currency(self, amount):
        """Format currency with proper thousand separators"""
        return f"{amount:,.2f} MAD"