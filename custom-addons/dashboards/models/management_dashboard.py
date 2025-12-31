# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import models, fields, api, tools

class ManagementDashboard(models.Model):
    _name = "management.dashboard"
    _description = "Executive Management Dashboard"

    name = fields.Char(string="Dashboard Name", required=True)
    dashboard_type = fields.Selection([
        ('profit_client', 'Profit par Client'),
        ('profit_product', 'Profit par Produit'),
    ], string="Type", required=True)
    
    last_refresh = fields.Datetime(string="Last Refresh", default=fields.Datetime.now)
    
    content_html = fields.Html(
        string="Dashboard Content",
        sanitize=False,
        readonly=True
    )
    
    # --------------------------------------------------------
    # MAIN COMPUTE
    # --------------------------------------------------------
    @api.model
    def create(self, vals):
        rec = super().create(vals)
        rec.action_reload_dashboard()
        return rec


    @api.depends('dashboard_type', 'last_refresh')
    def _compute_content_html(self):
        for rec in self:
            if rec.dashboard_type == 'profit_client':
                rec.content_html = rec._render_profit_client()
            elif rec.dashboard_type == 'profit_product':
                rec.content_html = rec._render_profit_product()
            else:
                rec.content_html = "<div class='alert alert-info'>Sélectionnez un type de dashboard.</div>"

    def action_reload_dashboard(self):
        self.ensure_one()

        # 🔥 OBLIGATOIRE : synchroniser ORM → PostgreSQL
        self.env.cr.flush()

        if self.dashboard_type == 'profit_client':
            html = self._render_profit_client()
        elif self.dashboard_type == 'profit_product':
            html = self._render_profit_product()
        else:
            html = "<div class='alert alert-info'>Sélectionnez un type de dashboard.</div>"

        self.sudo().write({
            'content_html': html,
            'last_refresh': fields.Datetime.now(),
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'management.dashboard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }






    # --------------------------------------------------------
    # RENDERERS
    # --------------------------------------------------------
    def _render_profit_client(self):
        """Render Client Profitability Dashboard"""
        # 1. Fetch Data from SQL View
        records = self.env['dashboard.profit.client'].sudo().with_context(prefetch_fields=False).search([], order='profit desc')

        
        if not records:
            return self._render_empty_state("clients")
        
        # 2. Calculate KPIs
        total_profit = sum(r.profit for r in records)
        total_tonnage = sum(r.tonnage_sold for r in records)
        total_ventes = sum(r.mt_vente for r in records)
        best_client = records[0].client_id.name if records else "N/A"
        worst_client = records[-1].client_id.name if len(records) > 1 else "N/A"
        avg_margin = sum(r.profit_margin for r in records) / len(records) if records else 0
        
        # 3. Build Modern HTML
        html = f"""
        <div style="font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 24px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh;">
            
            <!-- Header -->
            <div style="margin-bottom: 32px;">
                <h2 style="color: white; font-size: 28px; font-weight: 700; margin: 0 0 8px 0; text-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    📈 Tableau de Bord - Rentabilité par Client
                </h2>
                <p style="color: rgba(255,255,255,0.9); margin: 0; font-size: 14px;">
                    Analyse complète des performances commerciales • {len(records)} clients actifs
                </p>
            </div>
            
            <!-- KPIs Grid -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; margin-bottom: 32px;">
                {self._render_kpi_card("Profit Total", self._format_currency(total_profit), "💰", "#10b981", "#059669", True)}
                {self._render_kpi_card("CA Total", self._format_currency(total_ventes), "💵", "#f59e0b", "#d97706", True)}
                {self._render_kpi_card("Tonnage Total", f"{total_tonnage:,.0f} Kg", "📦", "#3b82f6", "#2563eb", False)}
                {self._render_kpi_card("Meilleur Client", best_client, "🏆", "#8b5cf6", "#7c3aed", False)}
            </div>
            
            <!-- Stats Bar -->
            <div style="background: rgba(255,255,255,0.95); border-radius: 12px; padding: 16px 24px; margin-bottom: 32px; box-shadow: 0 4px 6px rgba(0,0,0,0.07); display: flex; justify-content: space-around; flex-wrap: wrap; gap: 20px;">
                <div style="text-align: center;">
                    <div style="font-size: 24px; font-weight: 700; color: #111827;">{len(records)}</div>
                    <div style="font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">Clients</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 24px; font-weight: 700; color: #8b5cf6;">{avg_margin:.1f}%</div>
                    <div style="font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">Marge Moy.</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 24px; font-weight: 700; color: #10b981;">{len([r for r in records if r.profit > 0])}</div>
                    <div style="font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">Rentables</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 24px; font-weight: 700; color: #ef4444;">{len([r for r in records if r.profit < 0])}</div>
                    <div style="font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">Déficitaires</div>
                </div>
            </div>
            
            <!-- Table Section -->
            <div style="background: white; border-radius: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.07), 0 10px 20px rgba(0,0,0,0.1); overflow: hidden;">
                
                <!-- Table Header -->
                <div style="padding: 24px 24px 16px 24px; border-bottom: 2px solid #f3f4f6;">
                    <h3 style="margin: 0; font-size: 20px; font-weight: 700; color: #111827; display: flex; align-items: center; gap: 8px;">
                        <span>📊</span> Classement de Rentabilité par Client
                    </h3>
                    <p style="margin: 4px 0 0 0; color: #6b7280; font-size: 13px;">
                        Trié par contribution au profit • Données agrégées
                    </p>
                </div>
                
                <!-- Table -->
                <div style="overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                        <thead>
                            <tr style="background: linear-gradient(180deg, #f9fafb 0%, #f3f4f6 100%); border-bottom: 2px solid #e5e7eb;">
                                <th style="text-align: center; padding: 16px 20px; font-weight: 600; color: #374151; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Rang</th>
                                <th style="text-align: left; padding: 16px 20px; font-weight: 600; color: #374151; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Client</th>
                                <th style="text-align: right; padding: 16px 20px; font-weight: 600; color: #374151; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Tonnage</th>
                                <th style="text-align: right; padding: 16px 20px; font-weight: 600; color: #374151; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">CA</th>
                                <th style="text-align: right; padding: 16px 20px; font-weight: 600; color: #374151; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Coûts</th>
                                <th style="text-align: right; padding: 16px 20px; font-weight: 600; color: #374151; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Marge</th>
                                <th style="text-align: right; padding: 16px 20px; font-weight: 600; color: #374151; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Profit</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        
        # Render each row
        for idx, rec in enumerate(records, 1):
            html += self._render_client_row(idx, rec)
            
        html += f"""
                        </tbody>
                    </table>
                </div>
                
                <!-- Table Footer -->
                <div style="padding: 16px 24px; background-color: #f9fafb; border-top: 2px solid #e5e7eb; text-align: center;">
                    <span style="color: #6b7280; font-size: 12px;">
                        📅 Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} • Système Kal3iya
                    </span>
                </div>
            </div>
        </div>
        """
        return html

    def _render_profit_product(self):
        """Render Product Profitability Dashboard"""
        # 1. Fetch Data from SQL View
        records = self.env['dashboard.profit.product'].search([], order='profit desc')
        
        if not records:
            return self._render_empty_state("produits")
        
        # 2. Calculate KPIs
        total_profit = sum(r.profit for r in records)
        total_tonnage = sum(r.tonnage_sold for r in records)
        total_ventes = sum(r.mt_vente for r in records)
        best_product = records[0].product_id.name if records else "N/A"
        avg_margin = sum(r.profit_margin for r in records) / len(records) if records else 0
        
        # 3. Build Modern HTML
        html = f"""
        <div style="font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 24px; background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); min-height: 100vh;">
            
            <!-- Header -->
            <div style="margin-bottom: 32px;">
                <h2 style="color: white; font-size: 28px; font-weight: 700; margin: 0 0 8px 0; text-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    📦 Tableau de Bord - Rentabilité par Produit
                </h2>
                <p style="color: rgba(255,255,255,0.9); margin: 0; font-size: 14px;">
                    Performance détaillée des produits • {len(records)} produits analysés
                </p>
            </div>
            
            <!-- KPIs Grid -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; margin-bottom: 32px;">
                {self._render_kpi_card("Profit Total", self._format_currency(total_profit), "💰", "#10b981", "#059669", True)}
                {self._render_kpi_card("CA Total", self._format_currency(total_ventes), "💵", "#3b82f6", "#2563eb", True)}
                {self._render_kpi_card("Tonnage Total", f"{total_tonnage:,.0f} Kg", "📦", "#8b5cf6", "#7c3aed", False)}
                {self._render_kpi_card("Top Produit", best_product, "🏆", "#ef4444", "#dc2626", False)}
            </div>
            
            <!-- Stats Bar -->
            <div style="background: rgba(255,255,255,0.95); border-radius: 12px; padding: 16px 24px; margin-bottom: 32px; box-shadow: 0 4px 6px rgba(0,0,0,0.07); display: flex; justify-content: space-around; flex-wrap: wrap; gap: 20px;">
                <div style="text-align: center;">
                    <div style="font-size: 24px; font-weight: 700; color: #111827;">{len(records)}</div>
                    <div style="font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">Produits</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 24px; font-weight: 700; color: #f59e0b;">{avg_margin:.1f}%</div>
                    <div style="font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">Marge Moy.</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 24px; font-weight: 700; color: #10b981;">{len([r for r in records if r.profit > 0])}</div>
                    <div style="font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">Rentables</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 24px; font-weight: 700; color: #ef4444;">{len([r for r in records if r.profit < 0])}</div>
                    <div style="font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">Déficitaires</div>
                </div>
            </div>
            
            <!-- Table Section -->
            <div style="background: white; border-radius: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.07), 0 10px 20px rgba(0,0,0,0.1); overflow: hidden;">
                
                <!-- Table Header -->
                <div style="padding: 24px 24px 16px 24px; border-bottom: 2px solid #f3f4f6;">
                    <h3 style="margin: 0; font-size: 20px; font-weight: 700; color: #111827; display: flex; align-items: center; gap: 8px;">
                        <span>📊</span> Classement de Rentabilité par Produit
                    </h3>
                    <p style="margin: 4px 0 0 0; color: #6b7280; font-size: 13px;">
                        Trié par contribution au profit • Toutes ventes confondues
                    </p>
                </div>
                
                <!-- Table -->
                <div style="overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                        <thead>
                            <tr style="background: linear-gradient(180deg, #f9fafb 0%, #f3f4f6 100%); border-bottom: 2px solid #e5e7eb;">
                                <th style="text-align: center; padding: 16px 20px; font-weight: 600; color: #374151; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Rang</th>
                                <th style="text-align: left; padding: 16px 20px; font-weight: 600; color: #374151; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Produit</th>
                                <th style="text-align: right; padding: 16px 20px; font-weight: 600; color: #374151; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Tonnage</th>
                                <th style="text-align: right; padding: 16px 20px; font-weight: 600; color: #374151; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">CA</th>
                                <th style="text-align: right; padding: 16px 20px; font-weight: 600; color: #374151; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Coûts</th>
                                <th style="text-align: right; padding: 16px 20px; font-weight: 600; color: #374151; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Marge</th>
                                <th style="text-align: right; padding: 16px 20px; font-weight: 600; color: #374151; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Profit</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        
        # Render each row
        for idx, rec in enumerate(records, 1):
            html += self._render_product_row(idx, rec)
            
        html += f"""
                        </tbody>
                    </table>
                </div>
                
                <!-- Table Footer -->
                <div style="padding: 16px 24px; background-color: #f9fafb; border-top: 2px solid #e5e7eb; text-align: center;">
                    <span style="color: #6b7280; font-size: 12px;">
                        📅 Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} • Système Kal3iya
                    </span>
                </div>
            </div>
        </div>
        """
        return html

    # --------------------------------------------------------
    # HELPERS - RENDERING COMPONENTS
    # --------------------------------------------------------
    def _render_kpi_card(self, title, value, icon, color1, color2, is_currency):
        """Render a modern KPI card"""
        font_size = '28px' if is_currency else '20px'
        font_weight = '700' if is_currency else '600'
        
        return f"""
        <div style="background: white; border-radius: 16px; padding: 24px; box-shadow: 0 4px 6px rgba(0,0,0,0.07), 0 10px 20px rgba(0,0,0,0.1); position: relative; overflow: hidden;">
            <div style="position: absolute; top: -20px; right: -20px; width: 80px; height: 80px; background: linear-gradient(135deg, {color1}, {color2}); border-radius: 50%; opacity: 0.1;"></div>
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                <span style="color: #6b7280; font-size: 13px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;">{title}</span>
                <span style="font-size: 24px;">{icon}</span>
            </div>
            <div style="font-size: {font_size}; font-weight: {font_weight}; color: {color1}; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{value}">
                {value}
            </div>
            <div style="height: 3px; width: 40px; background: linear-gradient(90deg, {color1}, {color2}); border-radius: 2px;"></div>
        </div>
        """

    def _render_client_row(self, idx, rec):
        """Render a table row for client"""
        profit_color = "#10b981" if rec.profit >= 0 else "#ef4444"
        profit_bg = "rgba(16, 185, 129, 0.1)" if rec.profit >= 0 else "rgba(239, 68, 68, 0.1)"
        bg_color = "#fafafa" if idx % 2 == 0 else "white"
        
        rank_icon = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"#{idx}"
        margin_width = min(abs(rec.profit_margin), 100)
        margin_bar_color = "#10b981" if rec.profit_margin >= 0 else "#ef4444"
        
        client_name = rec.client_id.name or 'Inconnu'
        
        return f"""
        <tr style="border-bottom: 1px solid #f3f4f6; background-color: {bg_color}; transition: background-color 0.15s;" onmouseover="this.style.backgroundColor='#f9fafb'" onmouseout="this.style.backgroundColor='{bg_color}'">
            <td style="padding: 16px 20px; text-align: center; font-size: 18px; font-weight: 600;">{rank_icon}</td>
            <td style="padding: 16px 20px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #667eea, #764ba2); display: flex; align-items: center; justify-content: center; color: white; font-weight: 700; font-size: 14px; flex-shrink: 0;">
                        {client_name[0].upper()}
                    </div>
                    <span style="font-weight: 600; color: #111827;">{client_name}</span>
                </div>
            </td>
            <td style="padding: 16px 20px; text-align: right; color: #6b7280; font-weight: 500;">
                {rec.tonnage_sold:,.0f} <span style="font-size: 12px; color: #9ca3af;">Kg</span>
            </td>
            <td style="padding: 16px 20px; text-align: right; color: #111827; font-weight: 500;">
                {self._format_currency(rec.mt_vente)}
            </td>
            <td style="padding: 16px 20px; text-align: right; color: #6b7280; font-weight: 500;">
                {self._format_currency(rec.mt_achat)}
            </td>
            <td style="padding: 16px 20px; text-align: right;">
                <div style="display: flex; align-items: center; justify-content: flex-end; gap: 8px;">
                    <div style="width: 60px; height: 6px; background-color: #f3f4f6; border-radius: 3px; overflow: hidden;">
                        <div style="height: 100%; width: {margin_width}%; background-color: {margin_bar_color}; border-radius: 3px; transition: width 0.3s;"></div>
                    </div>
                    <span style="color: #6b7280; font-weight: 600; min-width: 45px;">{rec.profit_margin:.1f}%</span>
                </div>
            </td>
            <td style="padding: 16px 20px; text-align: right;">
                <div style="display: inline-block; padding: 6px 12px; background-color: {profit_bg}; border-radius: 8px;">
                    <span style="font-weight: 700; color: {profit_color};">
                        {self._format_currency(rec.profit)}
                    </span>
                </div>
            </td>
        </tr>
        """

    def _render_product_row(self, idx, rec):
        """Render a table row for product"""
        profit_color = "#10b981" if rec.profit >= 0 else "#ef4444"
        profit_bg = "rgba(16, 185, 129, 0.1)" if rec.profit >= 0 else "rgba(239, 68, 68, 0.1)"
        bg_color = "#fafafa" if idx % 2 == 0 else "white"
        
        rank_icon = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"#{idx}"
        margin_width = min(abs(rec.profit_margin), 100)
        margin_bar_color = "#10b981" if rec.profit_margin >= 0 else "#ef4444"
        
        product_name = rec.product_id.name or 'Inconnu'
        
        return f"""
        <tr style="border-bottom: 1px solid #f3f4f6; background-color: {bg_color}; transition: background-color 0.15s;" onmouseover="this.style.backgroundColor='#f9fafb'" onmouseout="this.style.backgroundColor='{bg_color}'">
            <td style="padding: 16px 20px; text-align: center; font-size: 18px; font-weight: 600;">{rank_icon}</td>
            <td style="padding: 16px 20px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #f59e0b, #d97706); display: flex; align-items: center; justify-content: center; color: white; font-weight: 700; font-size: 14px; flex-shrink: 0;">
                        {product_name[0].upper()}
                    </div>
                    <span style="font-weight: 600; color: #111827;">{product_name}</span>
                </div>
            </td>
            <td style="padding: 16px 20px; text-align: right; color: #6b7280; font-weight: 500;">
                {rec.tonnage_sold:,.0f} <span style="font-size: 12px; color: #9ca3af;">Kg</span>
            </td>
            <td style="padding: 16px 20px; text-align: right; color: #111827; font-weight: 500;">
                {self._format_currency(rec.mt_vente)}
            </td>
            <td style="padding: 16px 20px; text-align: right; color: #6b7280; font-weight: 500;">
                {self._format_currency(rec.mt_achat)}
            </td>
            <td style="padding: 16px 20px; text-align: right;">
                <div style="display: flex; align-items: center; justify-content: flex-end; gap: 8px;">
                    <div style="width: 60px; height: 6px; background-color: #f3f4f6; border-radius: 3px; overflow: hidden;">
                        <div style="height: 100%; width: {margin_width}%; background-color: {margin_bar_color}; border-radius: 3px; transition: width 0.3s;"></div>
                    </div>
                    <span style="color: #6b7280; font-weight: 600; min-width: 45px;">{rec.profit_margin:.1f}%</span>
                </div>
            </td>
            <td style="padding: 16px 20px; text-align: right;">
                <div style="display: inline-block; padding: 6px 12px; background-color: {profit_bg}; border-radius: 8px;">
                    <span style="font-weight: 700; color: {profit_color};">
                        {self._format_currency(rec.profit)}
                    </span>
                </div>
            </td>
        </tr>
        """

    def _render_empty_state(self, entity_type):
        """Render empty state when no data"""
        return f"""
        <div style="font-family: 'Inter', sans-serif; padding: 60px 40px; text-align: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center;">
            <div style="background: white; border-radius: 20px; padding: 60px 40px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); max-width: 500px;">
                <div style="font-size: 80px; margin-bottom: 20px;">📊</div>
                <h3 style="color: #374151; margin: 0 0 12px 0; font-size: 24px; font-weight: 700;">Aucune donnée disponible</h3>
                <p style="color: #6b7280; margin: 0; font-size: 15px; line-height: 1.6;">
                    Aucun {entity_type} trouvé dans votre base de données.<br/>
                    Commencez par créer des sorties de stock pour visualiser les statistiques.
                </p>
            </div>
        </div>
        """

    def _format_currency(self, amount):
        """Format currency with MAD"""
        return f"{amount:,.2f} Dh"


# -------------------------------------------------------------------------
#  SQL VIEW MODELS (Source de données)
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
                min(id) as id,
                client_id,
                sum(tonnage_sold) as tonnage_sold,
                sum(mt_vente) as mt_vente,
                sum(mt_achat) as mt_achat,
                sum(profit) as profit,
                CASE
                    WHEN sum(mt_vente) != 0
                    THEN (sum(profit) / sum(mt_vente)) * 100
                    ELSE 0
                END as profit_margin
            FROM (
                -- SALES (Sorties)
                SELECT
                    s.id,
                    s.client_id,
                    s.tonnage as tonnage_sold,
                    COALESCE(s.mt_vente_final, s.mt_vente) as mt_vente,
                    s.mt_achat,
                    (COALESCE(s.mt_vente_final, s.mt_vente) - s.mt_achat) as profit
                FROM kal3iyasortie s
                WHERE s.client_id IS NOT NULL

                UNION ALL

                -- RETURNS (Entrées type 'retour')
                SELECT
                    e.id * -1 as id, -- Negative ID to avoid collision
                    e.client_id,
                    -e.tonnage as tonnage_sold,
                    -(e.selling_price * e.tonnage) as mt_vente,
                    -(e.price * e.tonnage) as mt_achat,
                    -((e.selling_price * e.tonnage) - (e.price * e.tonnage)) as profit
                FROM kal3iyaentry e
                WHERE e.state = 'retour' AND e.client_id IS NOT NULL
            ) combined
            GROUP BY client_id
            HAVING sum(mt_vente) != 0 OR sum(profit) != 0
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
                    min(id) as id,
                    product_id,
                    sum(tonnage_sold) as tonnage_sold,
                    sum(mt_vente) as mt_vente,
                    sum(mt_achat) as mt_achat,
                    sum(profit) as profit,
                    CASE 
                        WHEN sum(mt_vente) != 0 
                        THEN (sum(profit) / sum(mt_vente)) * 100 
                        ELSE 0 
                    END as profit_margin
                FROM (
                    -- SALES
                    SELECT
                        s.id,
                        s.product_id,
                        s.tonnage as tonnage_sold,
                        COALESCE(s.mt_vente_final, s.mt_vente) as mt_vente,
                        s.mt_achat,
                        (COALESCE(s.mt_vente_final, s.mt_vente) - s.mt_achat) as profit
                    FROM kal3iyasortie s
                    WHERE s.product_id IS NOT NULL

                    UNION ALL

                    -- RETURNS
                    SELECT
                        e.id * -1 as id,
                        e.product_id,
                        -e.tonnage as tonnage_sold,
                        -(e.selling_price * e.tonnage) as mt_vente,
                        -(e.price * e.tonnage) as mt_achat,
                        -((e.selling_price * e.tonnage) - (e.price * e.tonnage)) as profit
                    FROM kal3iyaentry e
                    WHERE e.state = 'retour' AND e.product_id IS NOT NULL
                ) combined
                GROUP BY product_id
                HAVING sum(mt_vente) != 0 OR sum(profit) != 0
            )
        """ % self._table)