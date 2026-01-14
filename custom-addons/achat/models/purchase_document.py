import base64
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class PurchaseEntryDocument(models.Model):
    _name = 'logistique.entry.document'
    _description = 'Document Logistique'
    _rec_name = 'document_type'

    entry_id = fields.Many2one('logistique.entry', string='Dossier', required=True, ondelete='cascade')
    
    document_type = fields.Selection([
        ('invoice', 'Commercial Invoice'),
        ('packing', 'Packing List'),
        ('bl', 'Bill of Lading'),
        ('origin', 'Certificate of Origin'),
        ('fito', 'Fito sanitaire'),
        ('health', 'Health Certificate'),
        ('fumigation', 'Fumigation Certificate'),
        ('other', 'Other certificates'),
    ], string='Document Type', required=True)
    
    
    file = fields.Binary(string='Fichier', required=True, attachment=True)
    file_name = fields.Char(string='Nom du fichier')

    @api.constrains('file')
    def _check_file_size(self):
        """Limit file size to 5MB"""
        MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB in bytes
        for rec in self:
            if rec.file:
                # Binary field is stored as base64, decode to get actual size
                file_size = len(base64.b64decode(rec.file))
                if file_size > MAX_FILE_SIZE:
                    raise ValidationError(
                        f"La taille du fichier ({file_size / (1024*1024):.2f} MB) dépasse la limite autorisée de 5 MB."
                    )

    @api.model
    def create(self, vals):
        res = super(PurchaseEntryDocument, self).create(vals)
        res._update_parent_checklist()
        return res

    def write(self, vals):
        res = super(PurchaseEntryDocument, self).write(vals)
        self._update_parent_checklist()
        return res

    def unlink(self):
        # Store parent to update after deletion
        parents = self.mapped('entry_id')
        res = super(PurchaseEntryDocument, self).unlink()
        for parent in parents:
            self.env['logistique.entry.document']._update_checklist_for_entry(parent)
        return res

    def _update_parent_checklist(self):
        for rec in self:
            rec._update_checklist_for_entry(rec.entry_id)

    @api.model
    def _update_checklist_for_entry(self, entry):
        if not entry:
            return
            
        # Map document types to checklist fields
        type_field_map = {
            'invoice': 'doc_invoice',
            'packing': 'doc_packing',
            'bl': 'doc_bl',
            'origin': 'doc_origin',
            'fito': 'doc_fito',
            'health': 'doc_health',
            'fumigation': 'doc_fumigation',
        }
        
        # Check existing documents for this entry
        existing_types = self.search([('entry_id', '=', entry.id)]).mapped('document_type')
        
        for doc_type, field_name in type_field_map.items():
            # If document exists and field is 'absent', set to 'present'
            # If document does not exist and field is 'present', set to 'absent'
            # Do NOT touch 'confirmed' status
            
            current_status = getattr(entry, field_name)
            
            if doc_type in existing_types:
                if current_status == 'absent':
                    setattr(entry, field_name, 'present')
            else:
                if current_status == 'present':
                    setattr(entry, field_name, 'absent')
