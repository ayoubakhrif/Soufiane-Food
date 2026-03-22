from odoo import models, fields, api, tools


class SurestarieMagasinageReport(models.Model):
    _name = "surestarie.magasinage.report"
    _description = "Rapport Surestarie et Magasinage"
    _auto = False
    _order = 'bad_date desc'

    bad_date = fields.Date(string="Date BAD", readonly=True)
    week = fields.Char(string="Semaine", readonly=True)
    bl_number = fields.Char(string="Numéro BL", readonly=True)
    
    article_name = fields.Char(string="Article", readonly=True)
    supplier_id = fields.Many2one('logistique.supplier', string="Fournisseur", readonly=True)
    
    status = fields.Selection([
        ('in_progress', 'En cours'),
        ('get_out', 'Gate Out'),
        ('closed', 'Clotured'),
    ], string='Status', readonly=True)

    # Cleaned up fields - No more averages in SQL view
    container_count = fields.Integer(string="Nb Conteneurs", readonly=True)
    surestarie_amount = fields.Float(string="Montant Surestarie", readonly=True)
    magasinage_amount = fields.Float(string="Montant Magasinage", readonly=True)
    total_charges = fields.Float(string="Total Charges (Brut)", readonly=True)

    # Claims
    claims_amount = fields.Float(string="Réclamations (Remboursé)", readonly=True)
    total_charges_net = fields.Float(string="Total Charges Nettes", readonly=True)
    
    # Average fields for Pivot display (calculated in read_group)
    average_cost = fields.Float(string="Coût Brut / Conteneur", readonly=True)
    average_surestarie = fields.Float(string="Surestarie / Conteneur", readonly=True)
    average_magasinage = fields.Float(string="Magasinage / Conteneur", readonly=True)
    average_cost_net = fields.Float(string="Coût Net / Conteneur", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    le.id,
                    le.bad_date,
                    le.week,
                    le.bl_number,
                    COALESCE(aa.name, la.name, 'Sans Article') as article_name,
                    le.supplier_id,
                    le.status,
                    
                    -- Direct fields from logistique.entry
                    le.container_count as container_count,
                    le.surestarie_amount as surestarie_amount,
                    le.magasinage_amount as magasinage_amount,

                    -- Total Charges (Brut)
                    (le.surestarie_amount + le.magasinage_amount) as total_charges,

                    -- Claims amount (closed only)
                    COALESCE(cl.claims_total, 0.0) as claims_amount,

                    -- Total Charges Nettes
                    (le.surestarie_amount + le.magasinage_amount) - COALESCE(cl.claims_total, 0.0) as total_charges_net,
                    
                    -- Placeholders for averages (calculated in Python via read_group)
                    0.0 as average_cost,
                    0.0 as average_surestarie,
                    0.0 as average_magasinage,
                    0.0 as average_cost_net

                FROM
                    logistique_entry le
                LEFT JOIN achat_article aa ON aa.id = le.achat_article_id
                LEFT JOIN logistique_article la ON la.id = le.article_id
                LEFT JOIN (
                    SELECT
                        bl_id,
                        SUM(amount_due) as claims_total
                    FROM
                        claims_dhl_delay
                    WHERE
                        state = 'closed'
                    GROUP BY
                        bl_id
                ) cl ON cl.bl_id = le.id
                WHERE
                    (le.surestarie_amount != 0 OR le.magasinage_amount != 0)
            )
        """ % self._table)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super(SurestarieMagasinageReport, self).read_group(domain, fields, groupby, offset, limit, orderby, lazy)
        
        for line in res:
            # Get aggregated totals
            container_count = line.get('container_count', 0)
            total_charges = line.get('total_charges', 0.0)
            total_charges_net = line.get('total_charges_net', 0.0)
            surestarie_amount = line.get('surestarie_amount', 0.0)
            magasinage_amount = line.get('magasinage_amount', 0.0)

            # Calculate Weighted Averages
            if container_count > 0:
                line['average_cost'] = total_charges / container_count
                line['average_surestarie'] = surestarie_amount / container_count
                line['average_magasinage'] = magasinage_amount / container_count
                line['average_cost_net'] = total_charges_net / container_count
            else:
                line['average_cost'] = 0.0
                line['average_surestarie'] = 0.0
                line['average_magasinage'] = 0.0
                line['average_cost_net'] = 0.0
                
        return res