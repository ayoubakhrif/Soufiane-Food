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
    
    # Dates
    date_contract = fields.Date(string='Date Contrat', readonly=True)
    date_booking = fields.Date(string='Date Booking', readonly=True)
    date_docs_received = fields.Date(string='Docs Reçus', readonly=True)
    date_docs_confirmed = fields.Date(string='Docs Confirmés', readonly=True)
    eta_dhl = fields.Date(string='Date DHL (ETA)', readonly=True)
    bad_date = fields.Date(string='Date BAD', readonly=True)
    exit_date = fields.Date(string='Date Sortie (Full)', readonly=True)
    
    # Phase (Computed in SQL)
    phase = fields.Selection([
        ('1_contract', 'Contrat Signé'),
        ('2_created', 'Dossier Créé'),
        ('3_booking', 'Booking'),
        ('4_docs_rec', 'Docs Reçus'),
        ('5_docs_conf', 'Docs Confirmés'),
        ('6_transit', 'En Transit (DHL)'),
        ('7_customs', 'Douane (BAD)'),
        ('8_delivered', 'Livré (Sortie)'),
        ('9_closed', 'Clôturé'),
    ], string='Phase Actuelle', readonly=True)

    # HTML Visualization
    lifecycle_html = fields.Html(compute='_compute_lifecycle_html', string='Lifecycle Visualization')

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
            
            # 2. Création (Always done if record exists)
            s2_done = True
            steps.append({
                'label': 'Création du dossier',
                'date': "Fait",
                'status': 'done',
                'icon': 'fa-folder-plus'
            })
            
            # 3. Booking
            s3_done = bool(rec.date_booking)
            s3_status = 'done' if s3_done else ('current' if s1_done else 'pending')
            steps.append({
                'label': 'Booking',
                'date': fmt(rec.date_booking),
                'status': s3_status,
                'icon': 'fa-calendar-check'
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
                s4_status = 'current' if s3_done else 'pending'
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

            # 8. Clôture
            is_closed = (rec.phase == '9_closed')
            steps.append({
                'label': 'Clôture',
                'date': "Clôturé" if is_closed else "Non clôturé",
                'status': 'done' if is_closed else ('current' if s7_done else 'pending'),
                'icon': 'fa-check-circle'
            })
            
            # Generating HTML (Improved UI)
            html = f"""
            <style>
                .dlm-wrapper {{
                    font-family: 'Inter', 'Roboto', sans-serif;
                    background: #f5f7fa;
                    padding: 30px;
                    border-radius: 12px;
                }}

                .dlm-header {{
                    background: linear-gradient(135deg, #2c3e50, #34495e);
                    color: #fff;
                    padding: 25px;
                    border-radius: 12px;
                    margin-bottom: 40px;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                }}

                .dlm-header h1 {{
                    margin: 0;
                    font-size: 26px;
                    font-weight: 600;
                }}

                .dlm-meta {{
                    margin-top: 8px;
                    font-size: 14px;
                    opacity: 0.9;
                }}

                .dlm-badge {{
                    background: #1abc9c;
                    color: white;
                    padding: 6px 14px;
                    border-radius: 20px;
                    font-size: 13px;
                    font-weight: 500;
                    display: inline-block;
                    margin-top: 10px;
                }}

                .dlm-timeline {{
                    display: flex;
                    justify-content: space-between;
                    position: relative;
                    margin-top: 20px;
                    padding: 0 20px;
                }}

                /* Line background */
                .dlm-timeline::before {{
                    content: '';
                    position: absolute;
                    top: 25px; /* Centers line with circle */
                    left: 0;
                    right: 0;
                    height: 4px;
                    background: #e0e0e0;
                    z-index: 1;
                    border-radius: 2px;
                }}

                /* Progress bar based on completion - tricky in static HTML without calc, 
                   so we'll rely on colored steps. */

                .dlm-step {{
                    position: relative;
                    z-index: 2;
                    text-align: center;
                    width: 12%; /* Distribute space */
                }}

                .dlm-circle {{
                    width: 50px;
                    height: 50px;
                    background: #fff;
                    border: 4px solid #e0e0e0;
                    border-radius: 50%;
                    display: flex; /* Centering icon */
                    align-items: center;
                    justify-content: center;
                    margin: 0 auto;
                    transition: all 0.3s ease;
                }}

                .dlm-icon {{
                    font-size: 18px;
                    color: #bdc3c7;
                }}

                .dlm-content {{
                    margin-top: 15px;
                }}

                .dlm-label {{
                    font-size: 13px;
                    font-weight: 700;
                    color: #7f8c8d;
                    margin-bottom: 4px;
                }}

                .dlm-date {{
                    font-size: 12px;
                    color: #95a5a6;
                }}

                /* States */
                .dlm-step.done .dlm-circle {{
                    border-color: #27ae60;
                    background: #27ae60;
                }}
                .dlm-step.done .dlm-icon {{
                    color: #fff;
                }}
                .dlm-step.done .dlm-label {{
                    color: #2c3e50;
                }}

                .dlm-step.current .dlm-circle {{
                    border-color: #f39c12;
                    background: #fff;
                }}
                .dlm-step.current .dlm-icon {{
                    color: #f39c12;
                }}
                .dlm-step.current .dlm-label {{
                    color: #f39c12;
                }}

            </style>
            
            <div class="dlm-wrapper">
                <div class="dlm-header">
                    <h1>{rec.bl_number}</h1>
                    <div class="dlm-meta">
                        <i class="fa fa-building"></i> {rec.company_id.name or '-'} &nbsp;|&nbsp; 
                        <i class="fa fa-industry"></i> {rec.supplier_id.name or '-'}
                    </div>
                    <div class="dlm-badge">
                        {dict(self._fields['phase'].selection).get(rec.phase, '')}
                    </div>
                </div>
                
                <div class="dlm-timeline">
            """
            
            for step in steps:
                html += f"""
                    <div class="dlm-step {step['status']}">
                        <div class="dlm-circle">
                            <i class="fa {step['icon']} dlm-icon"></i>
                        </div>
                        <div class="dlm-content">
                            <div class="dlm-label">{step['label']}</div>
                            <div class="dlm-date">{step['date']}</div>
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
                    c.date as date_contract,
                    l.date_booking as date_booking,
                    l.date_docs_received as date_docs_received,
                    l.date_docs_confirmed as date_docs_confirmed,
                    l.eta_dhl as eta_dhl,
                    l.bad_date as bad_date,
                    l.exit_date as exit_date,
                    
                    CASE
                        WHEN l.status = 'closed' THEN '9_closed'
                        WHEN l.exit_date IS NOT NULL THEN '8_delivered'
                        WHEN l.bad_date IS NOT NULL THEN '7_customs'
                        WHEN l.eta_dhl IS NOT NULL THEN '6_transit'
                        WHEN l.date_docs_confirmed IS NOT NULL THEN '5_docs_conf'
                        WHEN l.date_docs_received IS NOT NULL THEN '4_docs_rec'
                        WHEN l.date_booking IS NOT NULL THEN '3_booking'
                        WHEN l.contract_id IS NOT NULL THEN '1_contract'
                        ELSE '2_created'
                    END as phase
                    
                FROM logistique_entry l
                LEFT JOIN achat_contract c ON (l.contract_id = c.id)
            )
        """ % self._table)
