from odoo import models, fields, api
import json

class TresorerieChqAITraining(models.Model):
    _name = 'tresorerie_chq.ai.training'
    _description = "Données d'entraînement IA (Chèques/Effets)"
    _order = 'create_date desc'

    name = fields.Char(string='Référence', compute='_compute_name', store=True)
    paiement_id = fields.Many2one('tresorerie_chq.paiement', string='Paiement Source', readonly=True)
    document_type = fields.Selection([
        ('cheque', 'Chèque'),
        ('effet', 'Effet'),
    ], string='Type de document', readonly=True)

    scan_document = fields.Binary(string='Scan Document', related='paiement_id.scan_document', readonly=True)
    scan_document_name = fields.Char(string='Nom Scan', related='paiement_id.scan_document_name', readonly=True)

    ai_prediction = fields.Text(string='Prédiction IA (Brut)', readonly=True)
    validated_data = fields.Text(string='Données Validées (Vérité)', readonly=True)

    is_corrected = fields.Boolean(
        string='A été corrigé par utilisateur',
        compute='_compute_is_corrected',
        store=True,
        help="Coché si les données validées diffèrent de la prédiction IA."
    )

    @api.depends('paiement_id')
    def _compute_name(self):
        for rec in self:
            rec.name = f"Data-{rec.id or 'New'}-{rec.document_type}-{rec.paiement_id.id if rec.paiement_id else ''}"

    @api.depends('ai_prediction', 'validated_data')
    def _compute_is_corrected(self):
        for rec in self:
            if not rec.ai_prediction or not rec.validated_data:
                rec.is_corrected = False
                continue
            
            try:
                pred_json = json.loads(rec.ai_prediction)
                val_json = json.loads(rec.validated_data)
                
                # Check for differences in keys we care about
                corrected = False
                for key in ['numero', 'montant', 'date_echeance', 'banque', 'porteur']:
                    # Normalize string values for comparison
                    val_pred = str(pred_json.get(key) or '').strip().lower()
                    val_true = str(val_json.get(key) or '').strip().lower()
                    if val_pred != val_true:
                        corrected = True
                        break
                
                rec.is_corrected = corrected
            except Exception:
                rec.is_corrected = True # if JSON is invalid, assume it was corrected
