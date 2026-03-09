from odoo import models, fields, api, _
from datetime import date

class SurestarieMagasinageDashboard(models.Model):
    _name = "surestarie.magasinage.dashboard"
    _description = "Surestarie & Magasinage KPI Dashboard"

    name = fields.Char(string="Name", default="Tableau de Bord")
    content_html = fields.Html(compute='_compute_content_html')

    @api.depends('name')
    def _compute_content_html(self):
        for rec in self:
            # 1. Build Domain based on Amounts (No Year Filter)
            domain = [
                '|',
                ('surestarie_amount', '!=', 0),
                ('magasinage_amount', '!=', 0)
            ]
            
            # 2. Fetch Global Aggregates
            global_data = self.env['surestarie.magasinage.report'].read_group(
                domain,
                ['container_count', 'surestarie_amount', 'magasinage_amount', 'total_charges', 'claims_amount', 'total_charges_net'],
                []
            )

            if global_data:
                res = global_data[0]
                total_containers = res.get('container_count', 0)
                total_surestarie = res.get('surestarie_amount', 0.0)
                total_magasinage = res.get('magasinage_amount', 0.0)
                total_charges = res.get('total_charges', 0.0)
                total_claims = res.get('claims_amount', 0.0)
                total_charges_net = res.get('total_charges_net', 0.0)
            else:
                total_containers = 0
                total_surestarie = 0.0
                total_magasinage = 0.0
                total_charges = 0.0
                total_claims = 0.0
                total_charges_net = 0.0

            # Global Weighted Average (Net)
            if total_containers > 0:
                global_avg_cost_net = total_charges_net / total_containers
            else:
                global_avg_cost_net = 0.0

            # Format Global Values
            def fmt(val):
                return "{:,.2f}".format(val).replace(",", " ").replace(".", ",")

            formatted_surestarie = fmt(total_surestarie)
            formatted_magasinage = fmt(total_magasinage)
            formatted_charges = fmt(total_charges)
            formatted_claims = fmt(total_claims)
            formatted_charges_net = fmt(total_charges_net)
            formatted_avg_net = fmt(global_avg_cost_net)

            # 3. Helper Function for Detailed Sections (Product & Supplier)
            def get_detailed_data(groupby_field, name_field_model):
                groups = self.env['surestarie.magasinage.report'].read_group(
                    domain,
                    ['container_count', 'surestarie_amount', 'magasinage_amount', 'total_charges', 'claims_amount', 'total_charges_net'],
                    [groupby_field]
                )
                
                rows = []
                for group in groups:
                    g_containers = group.get('container_count', 0)
                    g_surestarie = group.get('surestarie_amount', 0.0)
                    g_magasinage = group.get('magasinage_amount', 0.0)
                    g_charges = group.get('total_charges', 0.0)
                    g_claims = group.get('claims_amount', 0.0)
                    g_charges_net = group.get('total_charges_net', 0.0)
                    
                    # Manual Weighted Average (Net)
                    if g_containers > 0:
                        g_weighted_avg = g_charges_net / g_containers
                    else:
                        g_weighted_avg = 0.0

                    # Get Name
                    group_val = group.get(groupby_field)
                    if isinstance(group_val, tuple):
                        name = group_val[1]
                    elif group_val:
                        name = str(group_val)
                    else:
                        name = "Indéfini"

                    rows.append({
                        'name': name,
                        'containers': g_containers,
                        'surestarie': g_surestarie,
                        'magasinage': g_magasinage,
                        'total_charges': g_charges,
                        'claims': g_claims,
                        'total_charges_net': g_charges_net,
                        'weighted_avg': g_weighted_avg
                    })
                
                # Sort by Moyenne Net DESC
                rows.sort(key=lambda x: x['weighted_avg'], reverse=True)
                
                # Ranking: Find Best (Lowest Avg) and Worst (Highest Avg)
                if rows:
                    best_row = min(rows, key=lambda x: x['weighted_avg'])
                    worst_row = max(rows, key=lambda x: x['weighted_avg'])
                    
                    for row in rows:
                        row['is_best'] = (row == best_row)
                        row['is_worst'] = (row == worst_row)
                
                return rows

            # 4. Fetch Detailed Data
            product_rows = get_detailed_data('article_id', 'logistique.article')
            supplier_rows = get_detailed_data('supplier_id', 'logistique.supplier')

            # 5. Build HTML Table Function
            def build_table_html(title, rows):
                tbody = ""
                for row in rows:
                    # Styling for Best/Worst
                    row_class = ""
                    badge = ""
                    if row.get('is_best') and len(rows) > 1:
                        row_class = "table-success"
                        badge = '<span class="badge badge-pill badge-success">Top</span>'
                    elif row.get('is_worst') and len(rows) > 1:
                        row_class = "table-danger"
                        badge = '<span class="badge badge-pill badge-danger">Flop</span>'
                    
                    fmt_sur = fmt(row['surestarie'])
                    fmt_mag = fmt(row['magasinage'])
                    fmt_tot = fmt(row['total_charges'])
                    fmt_cl = fmt(row['claims'])
                    fmt_net = fmt(row['total_charges_net'])
                    fmt_avg = fmt(row['weighted_avg'])
                    
                    tbody += f"""
                    <tr class="{row_class}">
                        <td>{row['name']} {badge}</td>
                        <td class="text-right">{row['containers']}</td>
                        <td class="text-right">{fmt_sur}</td>
                        <td class="text-right">{fmt_mag}</td>
                        <td class="text-right">{fmt_tot}</td>
                        <td class="text-right text-success">{fmt_cl}</td>
                        <td class="text-right font-weight-bold">{fmt_net}</td>
                        <td class="text-right font-weight-bold">{fmt_avg}</td>
                    </tr>
                    """
                
                return f"""
                <div class="col-md-12 mt-4">
                    <div class="card">
                        <div class="card-header"><h3>{title}</h3></div>
                        <div class="card-body p-0">
                            <table class="table table-bordered table-sm table-hover mb-0">
                                <thead class="thead-light">
                                    <tr>
                                        <th>Nom</th>
                                        <th class="text-right">Conteneurs</th>
                                        <th class="text-right">Surestarie</th>
                                        <th class="text-right">Magasinage</th>
                                        <th class="text-right">Total Brut</th>
                                        <th class="text-right">Claims</th>
                                        <th class="text-right">Total Net</th>
                                        <th class="text-right">Moyenne Net / Ctrl</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {tbody}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
                """

            # 6. Assemble Final HTML
            html = f"""
            <div class="o_dashboard_view container-fluid">
                <div class="row">
                    <div class="col-md-12 mb-4">
                        <h2 class="text-center">Performance Surestarie & Magasinage (Global)</h2>
                    </div>
                </div>
                
                <!-- Global KPIs -->
                <div class="row text-center">
                    <div class="col-md-2">
                        <div class="card bg-primary text-white mb-3">
                            <div class="card-header">Total Conteneurs</div>
                            <div class="card-body"><h3 class="card-title">{total_containers}</h3></div>
                        </div>
                    </div>
                    <div class="col-md-2">
                        <div class="card bg-warning text-white mb-3">
                            <div class="card-header">Surestarie</div>
                            <div class="card-body"><h3 class="card-title">{formatted_surestarie} MAD</h3></div>
                        </div>
                    </div>
                    <div class="col-md-2">
                        <div class="card bg-secondary text-white mb-3">
                            <div class="card-header">Magasinage</div>
                            <div class="card-body"><h3 class="card-title">{formatted_magasinage} MAD</h3></div>
                        </div>
                    </div>
                    <div class="col-md-2">
                        <div class="card bg-info text-white mb-3">
                            <div class="card-header">Charges Brutes</div>
                            <div class="card-body"><h3 class="card-title">{formatted_charges} MAD</h3></div>
                        </div>
                    </div>
                    <div class="col-md-2">
                        <div class="card border-success mb-3">
                            <div class="card-header text-success">Claims</div>
                            <div class="card-body"><h3 class="card-title text-success">- {formatted_claims} MAD</h3></div>
                        </div>
                    </div>
                    <div class="col-md-2">
                        <div class="card bg-danger text-white mb-3">
                            <div class="card-header">Charges Nettes</div>
                            <div class="card-body"><h3 class="card-title">{formatted_charges_net} MAD</h3></div>
                        </div>
                    </div>
                </div>
                
                <!-- Global Average (Net) -->
                <div class="row justify-content-center mt-2">
                    <div class="col-md-6">
                        <div class="card border-success mb-3">
                            <div class="card-header bg-success text-white text-center">
                                <h4>Coût Moyen Net par Conteneur (Pondéré)</h4>
                            </div>
                            <div class="card-body text-success text-center">
                                <h1 class="display-4 font-weight-bold">{formatted_avg_net} MAD</h1>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Detailed Tables -->
                <div class="row">
                    {build_table_html("Charges par Article (Trier par Moyenne Net)", product_rows)}
                    {build_table_html("Charges par Fournisseur (Trier par Moyenne Net)", supplier_rows)}
                </div>
            </div>
            """
            rec.content_html = html