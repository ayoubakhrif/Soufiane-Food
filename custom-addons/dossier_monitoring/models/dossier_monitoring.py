from odoo import models, fields, tools

class DossierMonitoring(models.Model):
    _name = 'dossier.monitoring'
    _description = 'Dossier Lifecycle Monitoring'
    _auto = False
    _rec_name = 'bl_number'
    _order = 'id desc'

    # Source Fields
    dossier_id = fields.Many2one('logistique.entry', string='Dossier', readonly=True)
    bl_number = fields.Char(string='BL Number', readonly=True)
    contract_id = fields.Many2one('achat.contract', string='Contract', readonly=True)
    supplier_id = fields.Many2one('logistique.supplier', string='Supplier', readonly=True)
    company_id = fields.Many2one('logistique.ste', string='Company', readonly=True)
    
    # Dates
    date_contract = fields.Date(string='Contract Date', readonly=True)
    date_booking = fields.Date(string='Booking Date', readonly=True)
    date_docs_received = fields.Date(string='Docs Received', readonly=True)
    date_docs_confirmed = fields.Date(string='Docs Confirmed', readonly=True)
    eta_dhl = fields.Date(string='DHL Date (ETA)', readonly=True)
    bad_date = fields.Date(string='BAD Date', readonly=True)
    exit_date = fields.Date(string='Full Exit Date', readonly=True)
    
    # Phase (Computed in SQL)
    phase = fields.Selection([
        ('1_contract', 'Contract Signed'),
        ('2_created', 'Dossier Created'),
        ('3_booking', 'Booking'),
        ('4_docs_rec', 'Docs Received'),
        ('5_docs_conf', 'Docs Confirmed'),
        ('6_transit', 'In Transit (DHL)'),
        ('7_customs', 'Customs (BAD)'),
        ('8_delivered', 'Delivered (Exit)'),
        ('9_closed', 'Closed'),
    ], string='Current Phase', readonly=True)

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
