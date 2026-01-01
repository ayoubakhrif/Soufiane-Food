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
        compute="_compute_content_html",
        sanitize=False,
        readonly=True
    )

    @api.depends('dashboard_type')
    def _compute_content_html(self):
        for rec in self:
            if rec.dashboard_type == 'profit_client':
                rec.content_html = rec._render_profit_client()
            elif rec.dashboard_type == 'profit_product':
                rec.content_html = rec._render_profit_product()
            else:
                rec.content_html = ""


    @api.model
    def create(self, vals):
        rec = super().create(vals)
        # Compute content on creation
        rec.action_reload_dashboard()
        return rec

    # --------------------------------------------------------
    # MAIN ACTIONS
    # --------------------------------------------------------
    def action_reload_dashboard(self):
        self.ensure_one()
        
        # 1. Flush to ensure we have latest DB state
        self.env.cr.flush()

        # 2. Compute HTML content dynamically based on type
        html_content = ""
        if self.dashboard_type == 'profit_client':
            html_content = self._render_profit_client()
        elif self.dashboard_type == 'profit_product':
            html_content = self._render_profit_product()
        else:
            html_content = "<div class='alert alert-info'>Sélectionnez un type de dashboard.</div>"

        # 3. Write updates (sudo to bypass any readonly restrictions if needed, 
        # though this is a computed-like behavior, we store it for the view)
        self.sudo().write({
            'content_html': html_content,
            'last_refresh': fields.Datetime.now()
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'management.dashboard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # --------------------------------------------------------
    # PYTHON AGGREGATION LOGIC
    # --------------------------------------------------------
    def _render_profit_client(self):
        """
        Compute Client Profitability dynamically in Python.
        Sources:
          - kal3iyasortie (Sales)
          - kal3iyaentry (Returns, state='retour')
        """
        # Fetch Data
        sorties = self.env['kal3iyasortie'].search([('client_id', '!=', False)])
        retours = self.env['kal3iyaentry'].search([('state', '=', 'retour'), ('client_id', '!=', False)])

        if not sorties and not retours:
            return self._render_empty_state("clients")

        # Aggregation Structure: {client_id: {data...}}
        data = {}

        # 1. Process Sales (Sorties)
        for s in sorties:
            cid = s.client_id.id
            if cid not in data:
                data[cid] = {
                    'client': s.client_id,
                    'tonnage_sold': 0.0,
                    'mt_vente': 0.0,
                    'mt_achat': 0.0,
                    'profit': 0.0
                }
            
            # Use final values if present, else standard
            mt_vente = s.mt_vente_final if s.mt_vente_final else s.mt_vente
            mt_achat = s.mt_achat
            profit = mt_vente - mt_achat

            data[cid]['tonnage_sold'] += s.tonnage
            data[cid]['mt_vente'] += mt_vente
            data[cid]['mt_achat'] += mt_achat
            data[cid]['profit'] += profit

        # 2. Process Returns (Retours)
        # Returns reduce Sales, reduce Cost, reduce Profit
        for r in retours:
            cid = r.client_id.id
            if cid not in data:
                # Should normally exist if they bought something, but handle edge case
                data[cid] = {
                    'client': r.client_id,
                    'tonnage_sold': 0.0,
                    'mt_vente': 0.0,
                    'mt_achat': 0.0,
                    'profit': 0.0
                }

            # Return calculations
            r_mt_vente = r.selling_price * r.tonnage
            r_mt_achat = r.price * r.tonnage
            r_profit = r_mt_vente - r_mt_achat

            # Subtract from totals
            data[cid]['tonnage_sold'] -= r.tonnage
            data[cid]['mt_vente'] -= r_mt_vente
            data[cid]['mt_achat'] -= r_mt_achat
            data[cid]['profit'] -= r_profit

        # 3. Convert to List and Calculate Margins
        records = []
        for cid, vals in data.items():
            # Skip if no activity (net zero)
            if vals['mt_vente'] == 0 and vals['profit'] == 0:
                continue
                
            vals['profit_margin'] = (vals['profit'] / vals['mt_vente'] * 100) if vals['mt_vente'] != 0 else 0
            records.append(vals)

        # 4. Sort by Profit Descending
        records.sort(key=lambda x: x['profit'], reverse=True)

        if not records:
             return self._render_empty_state("clients")

        return self._generate_html_report(records, "client")

    def _render_profit_product(self):
        """
        Compute Product Profitability dynamically in Python.
        """
        sorties = self.env['kal3iyasortie'].search([('product_id', '!=', False)])
        retours = self.env['kal3iyaentry'].search([('state', '=', 'retour'), ('product_id', '!=', False)])

        if not sorties and not retours:
            return self._render_empty_state("produits")

        data = {}

        # 1. Process Sales (Sorties)
        for s in sorties:
            pid = s.product_id.id
            if pid not in data:
                data[pid] = {
                    'product': s.product_id,
                    'tonnage_sold': 0.0,
                    'mt_vente': 0.0,
                    'mt_achat': 0.0,
                    'profit': 0.0
                }
            
            mt_vente = s.mt_vente_final if s.mt_vente_final else s.mt_vente
            mt_achat = s.mt_achat
            profit = mt_vente - mt_achat

            data[pid]['tonnage_sold'] += s.tonnage
            data[pid]['mt_vente'] += mt_vente
            data[pid]['mt_achat'] += mt_achat
            data[pid]['profit'] += profit

        # 2. Process Returns (Retours)
        for r in retours:
            pid = r.product_id.id
            if pid not in data:
                data[pid] = {
                    'product': r.product_id,
                    'tonnage_sold': 0.0,
                    'mt_vente': 0.0,
                    'mt_achat': 0.0,
                    'profit': 0.0
                }

            r_mt_vente = r.selling_price * r.tonnage
            r_mt_achat = r.price * r.tonnage
            r_profit = r_mt_vente - r_mt_achat

            data[pid]['tonnage_sold'] -= r.tonnage
            data[pid]['mt_vente'] -= r_mt_vente
            data[pid]['mt_achat'] -= r_mt_achat
            data[pid]['profit'] -= r_profit

        # 3. Convert & Calc Margins
        records = []
        for pid, vals in data.items():
            if vals['mt_vente'] == 0 and vals['profit'] == 0:
                continue

            vals['profit_margin'] = (vals['profit'] / vals['mt_vente'] * 100) if vals['mt_vente'] != 0 else 0
            records.append(vals)

        # 4. Sort
        records.sort(key=lambda x: x['profit'], reverse=True)
        
        if not records:
             return self._render_empty_state("produits")

        return self._generate_html_report(records, "product")

    # --------------------------------------------------------
    # HTML GENERATION (Generic)
    # --------------------------------------------------------
    def _generate_html_report(self, records, report_type):
        """
        Generate HTML for both Client and Product reports using the prepared data list.
        records: list of dicts {'client'/'product', 'profit', 'mt_vente', etc.}
        report_type: 'client' or 'product'
        """
        is_client = (report_type == 'client')
        
        # Calculate Global KPIs
        total_profit = sum(r['profit'] for r in records)
        total_tonnage = sum(r['tonnage_sold'] for r in records)
        total_ventes = sum(r['mt_vente'] for r in records)
        
        best_name = "N/A"
        if records:
            obj = records[0]['client'] if is_client else records[0]['product']
            best_name = obj.name

        avg_margin = sum(r['profit_margin'] for r in records) / len(records) if records else 0

        # Title & Colors
        if is_client:
            title = "📈 Tableau de Bord - Rentabilité par Client"
            bg_gradient = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
            entity_label = "Clients"
        else:
            title = "📦 Tableau de Bord - Rentabilité par Produit"
            bg_gradient = "linear-gradient(135deg, #f59e0b 0%, #d97706 100%)"
            entity_label = "Produits"

        # HTML Construction
        html = f"""
        <div style="font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 24px; background: {bg_gradient}; min-height: 100vh;">
            
            <!-- Header -->
            <div style="margin-bottom: 32px;">
                <h2 style="color: white; font-size: 28px; font-weight: 700; margin: 0 0 8px 0; text-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    {title}
                </h2>
                <p style="color: rgba(255,255,255,0.9); margin: 0; font-size: 14px;">
                    Analyse temps réel • {len(records)} {entity_label.lower()} analysés
                </p>
            </div>
            
            <!-- KPIs Grid -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; margin-bottom: 32px;">
                {self._render_kpi_card("Profit Total", self._format_currency(total_profit), "💰", "#10b981", "#059669", True)}
                {self._render_kpi_card("CA Total", self._format_currency(total_ventes), "💵", "#3b82f6", "#2563eb", True)}
                {self._render_kpi_card("Tonnage Total", f"{total_tonnage:,.0f} Kg", "📦", "#8b5cf6", "#7c3aed", False)}
                {self._render_kpi_card(f"Meilleur {entity_label[:-1]}", best_name, "🏆", "#ef4444", "#dc2626", False)}
            </div>
            
            <!-- Stats Bar -->
            <div style="background: rgba(255,255,255,0.95); border-radius: 12px; padding: 16px 24px; margin-bottom: 32px; box-shadow: 0 4px 6px rgba(0,0,0,0.07); display: flex; justify-content: space-around; flex-wrap: wrap; gap: 20px;">
                <div style="text-align: center;">
                    <div style="font-size: 24px; font-weight: 700; color: #111827;">{len(records)}</div>
                    <div style="font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">{entity_label}</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 24px; font-weight: 700; color: #f59e0b;">{avg_margin:.1f}%</div>
                    <div style="font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">Marge Moy.</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 24px; font-weight: 700; color: #10b981;">{len([r for r in records if r['profit'] > 0])}</div>
                    <div style="font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">Rentables</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 24px; font-weight: 700; color: #ef4444;">{len([r for r in records if r['profit'] < 0])}</div>
                    <div style="font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">Déficitaires</div>
                </div>
            </div>
            
            <!-- Table Section -->
            <div style="background: white; border-radius: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.07), 0 10px 20px rgba(0,0,0,0.1); overflow: hidden;">
                
                <!-- Table Header -->
                <div style="padding: 24px 24px 16px 24px; border-bottom: 2px solid #f3f4f6;">
                    <h3 style="margin: 0; font-size: 20px; font-weight: 700; color: #111827; display: flex; align-items: center; gap: 8px;">
                        <span>📊</span> Classement de Rentabilité
                    </h3>
                    <p style="margin: 4px 0 0 0; color: #6b7280; font-size: 13px;">
                        Trié par contribution au profit
                    </p>
                </div>
                
                <!-- Table -->
                <div style="overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                        <thead>
                            <tr style="background: linear-gradient(180deg, #f9fafb 0%, #f3f4f6 100%); border-bottom: 2px solid #e5e7eb;">
                                <th style="text-align: center; padding: 16px 20px; font-weight: 600; color: #374151; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Rang</th>
                                <th style="text-align: left; padding: 16px 20px; font-weight: 600; color: #374151; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">{entity_label[:-1]}</th>
                                <th style="text-align: right; padding: 16px 20px; font-weight: 600; color: #374151; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Tonnage</th>
                                <th style="text-align: right; padding: 16px 20px; font-weight: 600; color: #374151; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">CA</th>
                                <th style="text-align: right; padding: 16px 20px; font-weight: 600; color: #374151; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Coûts</th>
                                <th style="text-align: right; padding: 16px 20px; font-weight: 600; color: #374151; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Marge</th>
                                <th style="text-align: right; padding: 16px 20px; font-weight: 600; color: #374151; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Profit</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        
        for idx, rec in enumerate(records, 1):
            html += self._render_row(idx, rec, is_client)
            
        html += f"""
                        </tbody>
                    </table>
                </div>
                
                <!-- Table Footer -->
                <div style="padding: 16px 24px; background-color: #f9fafb; border-top: 2px solid #e5e7eb; text-align: center;">
                    <span style="color: #6b7280; font-size: 12px;">
                        📅 Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')} • Données temps réel
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

    def _render_row(self, idx, rec, is_client):
        """Render a table row"""
        profit = rec['profit']
        profit_margin = rec['profit_margin']
        
        profit_color = "#10b981" if profit >= 0 else "#ef4444"
        profit_bg = "rgba(16, 185, 129, 0.1)" if profit >= 0 else "rgba(239, 68, 68, 0.1)"
        bg_color = "#fafafa" if idx % 2 == 0 else "white"
        
        rank_icon = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"#{idx}"
        margin_width = min(abs(profit_margin), 100)
        margin_bar_color = "#10b981" if profit_margin >= 0 else "#ef4444"
        
        obj = rec['client'] if is_client else rec['product']
        name = obj.name or 'Inconnu'
        
        # Avatar color based on type
        grad_start = "#667eea" if is_client else "#f59e0b"
        grad_end = "#764ba2" if is_client else "#d97706"

        return f"""
        <tr style="border-bottom: 1px solid #f3f4f6; background-color: {bg_color}; transition: background-color 0.15s;" onmouseover="this.style.backgroundColor='#f9fafb'" onmouseout="this.style.backgroundColor='{bg_color}'">
            <td style="padding: 16px 20px; text-align: center; font-size: 18px; font-weight: 600;">{rank_icon}</td>
            <td style="padding: 16px 20px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, {grad_start}, {grad_end}); display: flex; align-items: center; justify-content: center; color: white; font-weight: 700; font-size: 14px; flex-shrink: 0;">
                        {name[0].upper()}
                    </div>
                    <span style="font-weight: 600; color: #111827;">{name}</span>
                </div>
            </td>
            <td style="padding: 16px 20px; text-align: right; color: #6b7280; font-weight: 500;">
                {rec['tonnage_sold']:,.0f} <span style="font-size: 12px; color: #9ca3af;">Kg</span>
            </td>
            <td style="padding: 16px 20px; text-align: right; color: #111827; font-weight: 500;">
                {self._format_currency(rec['mt_vente'])}
            </td>
            <td style="padding: 16px 20px; text-align: right; color: #6b7280; font-weight: 500;">
                {self._format_currency(rec['mt_achat'])}
            </td>
            <td style="padding: 16px 20px; text-align: right;">
                <div style="display: flex; align-items: center; justify-content: flex-end; gap: 8px;">
                    <div style="width: 60px; height: 6px; background-color: #f3f4f6; border-radius: 3px; overflow: hidden;">
                        <div style="height: 100%; width: {margin_width}%; background-color: {margin_bar_color}; border-radius: 3px; transition: width 0.3s;"></div>
                    </div>
                    <span style="color: #6b7280; font-weight: 600; min-width: 45px;">{profit_margin:.1f}%</span>
                </div>
            </td>
            <td style="padding: 16px 20px; text-align: right;">
                <div style="display: inline-block; padding: 6px 12px; background-color: {profit_bg}; border-radius: 8px;">
                    <span style="font-weight: 700; color: {profit_color};">
                        {self._format_currency(profit)}
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