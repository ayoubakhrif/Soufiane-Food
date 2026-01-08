from odoo import models, fields, api

class LogisticsEntryDocument(models.Model):
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
    ], string='Document Type', required=True)
    
    attachment_id = fields.Many2one('ir.attachment', string='Fichier', required=True, domain="[('res_model', '=', 'logistique.entry.document')]")

    @api.model
    def create(self, vals):
        res = super(LogisticsEntryDocument, self).create(vals)
        res._update_parent_checklist()
        return res

    def write(self, vals):
        res = super(LogisticsEntryDocument, self).write(vals)
        self._update_parent_checklist()
        return res

    def unlink(self):
        # Store parent to update after deletion
        parents = self.mapped('entry_id')
        res = super(LogisticsEntryDocument, self).unlink()
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
