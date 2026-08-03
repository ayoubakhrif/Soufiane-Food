from odoo import models, fields, api, tools

class FinanceLogisticsReconciliation(models.Model):
    _name = 'finance.logistics.reconciliation'
    _description = 'Rapprochement Finance-Logistique'
    _auto = False
    _order = 'date_operation desc'

    # Finance Side
    finance_cheque_id = fields.Many2one('finance.cheque.physical', string='Chèque Finance', readonly=True)
    chq_number = fields.Char(string='N° Chèque', readonly=True)
    finance_amount = fields.Float(string='Montant Finance', readonly=True)
    ste_id = fields.Many2one('finance.ste', string='Société', readonly=True)
    benif_id = fields.Many2one('finance.benif', string='Bénéficiaire', readonly=True)
    date_operation = fields.Date(string='Date Opération', readonly=True)

    # Logistics Side
    logistics_cheque_id = fields.Many2one('logistique.dossier.cheque', string='Chèque Logistique (Dernier)', readonly=True)
    logistics_amount = fields.Float(string='Montant Logistique (Total)', readonly=True)
    dossier_id = fields.Many2one('logistique.dossier', string='Dossier', readonly=True)
    
    # Analysis
    difference = fields.Float(string='Différence', readonly=True)
    state = fields.Selection([
        ('matches', 'Conforme'),
        ('mismatch', 'Non Conforme'),
        ('missing', 'Non Trouvé'),
    ], string='État', readonly=True)
    chq_state = fields.Selection([
        ('reserve', 'Réserve'),
        ('actif', 'Actif'),
        ('annule', 'Annulé'),
        ('bureau', 'Bureau'),
    ], string='État Chèque', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW finance_logistics_reconciliation AS (
                SELECT
                    fcp.id as id,
                    
                    -- Finance Info
                    fcp.id as finance_cheque_id,
                    fcp.name as chq_number,
                    fcp.amount_total as finance_amount,
                    fcp.ste_id as ste_id,
                    fcp.benif_id as benif_id,
                    fcp.date_emission as date_operation,
                    fcp.chq_state as chq_state,
                    
                    -- Logistics Info (Aggregated)
                    MAX(ldc.id) as logistics_cheque_id,
                    SUM(ldc.amount) as logistics_amount,
                    MAX(ldc.dossier_id) as dossier_id,
                    
                    -- Analysis
                    (fcp.amount_total - COALESCE(SUM(ldc.amount), 0)) as difference,
                    
                    CASE
                        WHEN COUNT(ldc.id) = 0 THEN 'missing'
                        WHEN ABS(fcp.amount_total - SUM(ldc.amount)) > 0.01 THEN 'mismatch'
                        ELSE 'matches'
                    END as state
                    
                FROM
                    finance_cheque_physical fcp
                -- Join Finance Company
                JOIN
                    finance_ste fste ON fcp.ste_id = fste.id
                -- Join Beneficiary (for filtering)
                JOIN
                    finance_benif fb ON fcp.benif_id = fb.id
                
                -- Left Join Logistics Cheques
                LEFT JOIN
                    logistique_dossier_cheque ldc ON (
                        ldc.cheque_serie = fcp.name
                        AND 
                        EXISTS (
                            SELECT 1 
                            FROM logistique_ste lste
                            WHERE lste.id = COALESCE(
                                (SELECT ste_id FROM logistique_entry WHERE id = ldc.entry_id),
                                ldc.ste_id
                            )
                            AND (
                                (fste.core_ste_id IS NOT NULL AND lste.core_ste_id = fste.core_ste_id)
                                OR 
                                (fste.name = lste.name)
                            )
                        )
                    )
                
                WHERE
                    fb.type = 'import'
                    AND fcp.active = true
                GROUP BY
                    fcp.id,
                    fcp.name,
                    fcp.amount_total,
                    fcp.ste_id,
                    fcp.benif_id,
                    fcp.date_emission,
                    fste.core_ste_id,
                    fste.name
            )
        """)

    def unlink(self):
        """Archive the underlying finance.cheque.physical records instead of deleting.
        The view IDs map 1-to-1 with finance_cheque_physical IDs (fcp.id as id).
        """
        cheques = self.env['finance.cheque.physical'].sudo().browse(self.ids)
        return cheques.write({'active': False})

    def action_mark_no_problem(self):
        """Mark this reconciliation record as 'no problem' by archiving the underlying cheque.
        The record will disappear from the rapprochement view.
        """
        cheques = self.env['finance.cheque.physical'].sudo().browse(self.ids)
        cheques.write({'active': False})
        return {'type': 'ir.actions.act_window_close'}
