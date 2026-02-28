from odoo import models, fields, tools

class DossierMonitoring(models.Model):
    _name = 'dossier.monitoring'
    _description = 'Dossier Lifecycle Monitoring'
    _auto = False
    _rec_name = 'bl_number'
    _order = 'id desc'

    # Source Fields
    dossier_id = fields.Many2one('logistique.entry', string='Dossier', readonly=True)
    bl_number = fields.Char(string='Numéro BL', readonly=True)
    contract_id = fields.Many2one('achat.contract', string='Contrat', readonly=True)
    supplier_id = fields.Many2one('logistique.supplier', string='Fournisseur', readonly=True)
    company_id = fields.Many2one('logistique.ste', string='Société', readonly=True)
    article_id = fields.Many2one('company.article', string='Article', readonly=True)
    container_count = fields.Integer(string='Nb Conteneurs', readonly=True)
    
    # Dates
    date_contract = fields.Date(string='Date Contrat', readonly=True)
    date_booking = fields.Date(string='Date Booking', readonly=True)
    date_docs_received = fields.Date(string='Docs Reçus', readonly=True)
    date_docs_confirmed = fields.Date(string='Docs Confirmés', readonly=True)
    eta_dhl = fields.Date(string='Date DHL (ETA)', readonly=True)
    bad_date = fields.Date(string='Date BAD', readonly=True)
    exit_date = fields.Date(string='Date Sortie (Full)', readonly=True)
    entry_date = fields.Date(string='Date Vide (Clôture)', readonly=True)
    
    # Phase (Computed in SQL)
    phase = fields.Selection([
        ('1_contract', 'Contrat Signé'),
        ('2_booking', 'Booking'),
        ('3_created', 'Dossier Créé'),
        ('4_docs_rec', 'Docs Reçus'),
        ('5_docs_conf', 'Docs Confirmés'),
        ('6_transit', 'En Transit (DHL)'),
        ('7_customs', 'Douane (BAD)'),
        ('8_delivered', 'Livré (Sortie)'),
        ('9_closed', 'Clôturé'),
    ], string='Phase Actuelle', readonly=True)

    # HTML Visualization
    lifecycle_html = fields.Html(
        compute='_compute_lifecycle_html',
        string='Lifecycle Visualization',
        sanitize=False
    )

    def _compute_lifecycle_html(self):
        for rec in self:
            # helper to format date
            def fmt(d):
                return d.strftime('%d/%m/%Y') if d else "Non renseigné"

            # Logic for steps
            # Structure: (Label, DateValue, IsDone, Icon)
            # We determine status dynamically based on sequence
            
            steps = []
            
            # 1. Contrat
            s1_done = bool(rec.contract_id)
            steps.append({
                'label': 'Contrat signé',
                'date': fmt(rec.date_contract),
                'status': 'done' if s1_done else 'pending',
                'icon': 'fa-file-signature'
            })
            
            # 2. Booking (Now before Creation)
            s2_done = bool(rec.date_booking)
            s2_status = 'done' if s2_done else ('current' if s1_done else 'pending')
            steps.append({
                'label': 'Booking',
                'date': fmt(rec.date_booking),
                'status': s2_status,
                'icon': 'fa-calendar-check'
            })

            # 3. Création (Always done if record exists)
            s3_done = True
            steps.append({
                'label': 'Création du dossier',
                'date': "Fait",
                'status': 'done',
                'icon': 'fa-folder-plus'
            })
            
            # 4. Docs
            s4_done = bool(rec.date_docs_confirmed)
            # Partial: Received but not confirmed
            if s4_done:
                s4_status = 'done'
                s4_date = fmt(rec.date_docs_confirmed)
            elif rec.date_docs_received:
                s4_status = 'current'
                s4_date = "Reçu: " + fmt(rec.date_docs_received)
            else:
                s4_status = 'current' if s2_done else 'pending'
                s4_date = "Non renseigné"
                
            steps.append({
                'label': 'Réception / Validation Docs',
                'date': s4_date,
                'status': s4_status,
                'icon': 'fa-file-alt'
            })
            
            # 5. Transit
            s5_done = bool(rec.exit_date) or bool(rec.bad_date) # If arrived/customs, transit is done
            # Or if just ETA is passed? Let's use ETA presence
            if s5_done:
                s5_status = 'done'
            elif rec.eta_dhl:
                s5_status = 'current'
            else:
                s5_status = 'current' if s4_done else 'pending'
            
            steps.append({
                'label': 'Transit (DHL)',
                'date': fmt(rec.eta_dhl),
                'status': s5_status,
                'icon': 'fa-ship'
            })

            # 6. Douane (BAD)
            s6_done = bool(rec.bad_date)
            steps.append({
                'label': 'Douane (BAD)',
                'date': fmt(rec.bad_date),
                'status': 'done' if s6_done else ('current' if (rec.eta_dhl or s5_done) else 'pending'),
                'icon': 'fa-stamp'
            })

            # 7. Livraison (Exit)
            s7_done = bool(rec.exit_date)
            steps.append({
                'label': 'Livraison',
                'date': fmt(rec.exit_date),
                'status': 'done' if s7_done else ('current' if s6_done else 'pending'),
                'icon': 'fa-truck'
            })

            # 8. Clôture (Driven by Empty Container Date)
            is_closed = bool(rec.entry_date)
            steps.append({
                'label': 'Clôture (Vide)',
                'date': fmt(rec.entry_date) if is_closed else "Non clôturé",
                'status': 'done' if is_closed else ('current' if s7_done else 'pending'),
                'icon': 'fa-check-circle'
            })
            
            # Generators Containers HTML
            container_html = ""
            containers = rec.dossier_id.container_ids
            if containers:
                container_html = """
                <div style="margin-top: 25px; border-top: 1px solid rgba(0,0,0,0.05); padding-top: 20px;">
                    <div style="font-size: 14px; color: #5a6c7d; margin-bottom: 12px; font-weight: 600;">
                        <i class="fa fa-boxes" style="color: #667eea; margin-right: 8px;"></i> LISTE DES CONTENEURS ({})
                    </div>
                    <div style="display: flex; flex-wrap: wrap; gap: 10px;">
                """.format(len(containers))
                
                for c in containers:
                    container_html += f"""
                    <span style="
                        background: #f1f5f9; 
                        color: #475569; 
                        padding: 8px 16px; 
                        border-radius: 8px; 
                        font-family: monospace; 
                        font-size: 14px; 
                        font-weight: 600; 
                        border: 1px solid #cbd5e1;">
                        {c.name}
                    </span>
                    """
                container_html += "</div></div>"

            # Generating HTML (Improved UI with Better Colors)
            html = f"""
            <style>
            /* ====== GLOBAL ====== */
            .dlm-wrapper {{
                font-family: 'Segoe UI', 'Roboto', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 40px;
                border-radius: 20px;
            }}

            /* ====== HEADER ====== */
            .dlm-header {{
                background: #ffffff;
                padding: 30px 35px;
                border-radius: 16px;
                margin-bottom: 30px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.15);
            }}

            .dlm-header-top {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 25px;
            }}

            .dlm-title {{
                font-size: 32px;
                font-weight: 900;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }}

            .dlm-phase-badge {{
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                color: #fff;
                padding: 12px 24px;
                border-radius: 50px;
                font-size: 15px;
                font-weight: 700;
                box-shadow: 0 6px 20px rgba(245, 87, 108, 0.4);
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}

            .dlm-meta {{
                font-size: 15px;
                color: #5a6c7d;
                margin-bottom: 20px;
            }}

            .dlm-meta i {{
                color: #667eea;
                margin-right: 8px;
            }}

            /* ====== KPI STRIP ====== */
            .dlm-kpis {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 20px;
            }}

            .dlm-kpi {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 20px;
                border-radius: 16px;
                text-align: center;
                box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
            }}

            .dlm-kpi-value {{
                display: block;
                font-size: 20px;
                font-weight: 800;
                color: #ffffff;
                margin-bottom: 8px;
            }}

            .dlm-kpi-label {{
                font-size: 13px;
                color: rgba(255, 255, 255, 0.9);
                text-transform: uppercase;
                letter-spacing: 1px;
                font-weight: 600;
            }}

            /* ====== TIMELINE ====== */
            .dlm-timeline {{
                position: relative;
                padding: 20px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 16px;
                backdrop-filter: blur(10px);
            }}

            .dlm-timeline::before {{
                content: '';
                position: absolute;
                left: 50px;
                top: 30px;
                bottom: 30px;
                width: 4px;
                background: rgba(255, 255, 255, 0.3);
                border-radius: 2px;
            }}

            .dlm-item {{
                display: flex;
                align-items: center;
                margin-bottom: 20px;
                position: relative;
                padding-left: 20px;
            }}

            .dlm-icon {{
                width: 60px;
                height: 60px;
                border-radius: 50%;
                background: #95a5a6;
                color: #fff;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 22px;
                z-index: 2;
                box-shadow: 0 8px 25px rgba(0,0,0,0.2);
                flex-shrink: 0;
                border: 5px solid rgba(255, 255, 255, 0.2);
            }}

            .dlm-item.done .dlm-icon {{
                background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
                animation: pulse-done 2s infinite;
            }}

            .dlm-item.current .dlm-icon {{
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                animation: pulse-current 1.5s infinite;
            }}

            .dlm-item.pending .dlm-icon {{
                background: linear-gradient(135deg, #868f96 0%, #596164 100%);
                opacity: 0.6;
            }}

            @keyframes pulse-done {{
                0%, 100% {{
                    box-shadow: 0 8px 25px rgba(56, 239, 125, 0.4);
                }}
                50% {{
                    box-shadow: 0 12px 35px rgba(56, 239, 125, 0.7);
                }}
            }}

            @keyframes pulse-current {{
                0%, 100% {{
                    box-shadow: 0 8px 25px rgba(245, 87, 108, 0.4);
                }}
                50% {{
                    box-shadow: 0 12px 35px rgba(245, 87, 108, 0.8);
                }}
            }}

            .dlm-content {{
                background: #ffffff;
                margin-left: 25px;
                padding: 20px 28px;
                border-radius: 16px;
                box-shadow: 0 8px 30px rgba(0,0,0,0.12);
                flex: 1;
                border-left: 5px solid transparent;
            }}

            .dlm-item.done .dlm-content {{
                border-left-color: #38ef7d;
            }}

            .dlm-item.current .dlm-content {{
                border-left-color: #f5576c;
                background: linear-gradient(to right, #fff5f7, #ffffff);
            }}

            .dlm-item.pending .dlm-content {{
                border-left-color: #95a5a6;
                opacity: 0.7;
            }}

            .dlm-label {{
                font-size: 18px;
                font-weight: 800;
                color: #2c3e50;
                margin-bottom: 8px;
            }}

            .dlm-date {{
                font-size: 14px;
                color: #7f8c8d;
                font-weight: 600;
            }}

            .dlm-item.done .dlm-date {{
                color: #27ae60;
            }}

            .dlm-item.current .dlm-date {{
                color: #e74c3c;
            }}

            /* Status badges */
            .dlm-status-badge {{
                display: inline-block;
                padding: 6px 14px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-top: 8px;
            }}

            .dlm-item.done .dlm-status-badge {{
                background: #d4edda;
                color: #155724;
            }}

            .dlm-item.current .dlm-status-badge {{
                background: #fff3cd;
                color: #856404;
            }}

            .dlm-item.pending .dlm-status-badge {{
                background: #e2e3e5;
                color: #6c757d;
            }}
            </style>

            <div class="dlm-wrapper">

                <div class="dlm-header">
                    <div class="dlm-header-top">
                        <div class="dlm-title">{rec.bl_number}</div>
                        <div class="dlm-phase-badge">
                            {dict(self._fields['phase'].selection).get(rec.phase, '')}
                        </div>
                    </div>

                    <div class="dlm-meta">
                        <i class="fa fa-cube"></i> <strong>{rec.article_id.name or '-'}</strong> &nbsp;&nbsp;&nbsp;
                        <i class="fa fa-building"></i> <strong>{rec.company_id.name or '-'}</strong> &nbsp;&nbsp;&nbsp;
                        <i class="fa fa-industry"></i> <strong>{rec.supplier_id.name or '-'}</strong>
                    </div>

                    <div class="dlm-kpis">
                        <div class="dlm-kpi">
                            <span class="dlm-kpi-value">{fmt(rec.date_contract)}</span>
                            <span class="dlm-kpi-label">Date Contrat</span>
                        </div>
                        <div class="dlm-kpi">
                            <span class="dlm-kpi-value">{fmt(rec.eta_dhl)}</span>
                            <span class="dlm-kpi-label">ETA DHL</span>
                        </div>
                        <div class="dlm-kpi">
                            <span class="dlm-kpi-value">{fmt(rec.exit_date)}</span>
                            <span class="dlm-kpi-label">Date Livraison</span>
                        </div>
                    </div>

                    {container_html}
                </div>

                <div class="dlm-timeline">
            """

            # Get status labels
            status_labels = {
                'done': '✓ COMPLÉTÉ',
                'current': '⚡ EN COURS',
                'pending': '⏳ EN ATTENTE'
            }
            
            for step in steps:
                html += f"""
                <div class="dlm-item {step['status']}">
                    <div class="dlm-icon">
                        <i class="fa {step['icon']}"></i>
                    </div>
                    <div class="dlm-content">
                        <div class="dlm-label">{step['label']}</div>
                        <div class="dlm-date">{step['date']}</div>
                        <span class="dlm-status-badge">{status_labels[step['status']]}</span>
                    </div>
                </div>
                """
                
            html += """
                </div>
            </div>
            """
            
            rec.lifecycle_html = html

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    l.id as id,
                    l.id as dossier_id,
                    l.bl_number as bl_number,
                    l.contract_id as contract_id,
                    l.supplier_id as supplier_id,
                    l.ste_id as company_id,
                    l.article_id as article_id,
                    l.container_count as container_count,
                    c.date as date_contract,
                    l.date_booking as date_booking,
                    l.date_docs_received as date_docs_received,
                    l.date_docs_confirmed as date_docs_confirmed,
                    l.eta_dhl as eta_dhl,
                    l.bad_date as bad_date,
                    l.exit_date as exit_date,
                    l.entry_date as entry_date,
                    
                    CASE
                        WHEN l.entry_date IS NOT NULL THEN '9_closed'
                        WHEN l.exit_date IS NOT NULL THEN '8_delivered'
                        WHEN l.bad_date IS NOT NULL THEN '7_customs'
                        WHEN l.eta_dhl IS NOT NULL THEN '6_transit'
                        WHEN l.date_docs_confirmed IS NOT NULL THEN '5_docs_conf'
                        WHEN l.date_docs_received IS NOT NULL THEN '4_docs_rec'
                        WHEN l.date_booking IS NOT NULL THEN '2_booking'
                        WHEN l.contract_id IS NOT NULL THEN '1_contract'
                        ELSE '3_created'
                    END as phase
                    
                FROM logistique_entry l
                LEFT JOIN achat_contract c ON (l.contract_id = c.id)
            )
        """ % self._table)
