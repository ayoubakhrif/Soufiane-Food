from odoo import models, fields

class AchatAITemplate(models.Model):
    _name = 'achat.ai.template'
    _description = 'Modèle Extraction IA'
    _order = 'id desc'

    name = fields.Char(string='Nom du Modèle', required=True)
    
    document_type = fields.Selection([
        ('invoice', 'Facture'),
        ('bl', 'Bill of Lading (BL)'),
        ('packing_list', 'Packing List'),
        ('health_certificate', 'Certificat Sanitaire'),
        ('origin_certificate', 'Certificat d\'Origine'),
        ('other', 'Autre')
    ], string='Type de document', required=True)

    # Optional linkages for smart targeting
    supplier_id = fields.Many2one('logistique.supplier', string='Fournisseur', help="Ce modèle s'appliquera aux documents de ce fournisseur.")
    ste_id = fields.Many2one('logistique.ste', string='Compagnie / Société', help="Ce modèle s'appliquera aux documents de cette compagnie.")
    origin_id = fields.Many2one('achat.origin', string='Origine', help="Ce modèle s'appliquera aux documents de cette origine.")

    instruction_filename = fields.Char(string='Nom du fichier')
    instruction_file = fields.Binary(
        string='Fichier de référence (PDF/Image annoté)',
        help="Uploadez le PDF ou l'image contenant les annotations pour guider l'IA."
    )

    instructions = fields.Text(
        string='Instructions textuelles (Prompt)',
        help="Instructions écrites complémentaires. Ex: 'Le poids net est souvent écrit en lbs, convertis-le en kg.'",
        default="Veuillez utiliser le document annoté ci-joint comme modèle pour identifier l'emplacement et le format des informations à extraire dans ce type de document."
    )
