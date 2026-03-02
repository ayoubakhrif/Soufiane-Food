from odoo import models, fields, api

class CasaProduct(models.Model):
    _name = 'casa.product'
    _description = 'Produits Casa'
    _order = 'id desc'

    name = fields.Char(string='Nom', required=True)
    article_id = fields.Many2one('company.article', string='Article (Company)', required=True)
    image_1920 = fields.Image(related='article_id.image', string='Image', store=True, readonly=True)

    @api.constrains('name')
    def _check_name_clash(self):
        import re
        from odoo.exceptions import ValidationError
        
        for record in self:
            if not record.name:
                continue
                
            n1 = ' '.join(record.name.lower().split())
            kg_pattern = r'\s*\d+([\.,]\d+)?\s*k?g$'
            
            m1 = re.search(kg_pattern, n1)
            base1 = n1[:m1.start()].strip() if m1 else n1
            suf1 = m1.group().replace(' ', '') if m1 else ''
            
            domain = [('id', '!=', record.id)]
            existing_products = self.search(domain)
            
            for p in existing_products:
                if not p.name:
                    continue
                    
                n2 = ' '.join(p.name.lower().split())
                
                if n1 == n2:
                    raise ValidationError(f"Le produit '{record.name}' existe déjà sous le nom '{p.name}'.")
                    
                m2 = re.search(kg_pattern, n2)
                base2 = n2[:m2.start()].strip() if m2 else n2
                suf2 = m2.group().replace(' ', '') if m2 else ''
                
                if base1 == base2:
                    if suf1 == suf2:
                        raise ValidationError(f"Le produit '{record.name}' a les mêmes caractéristiques que le produit '{p.name}'.")
                    else:
                        continue # Allowed: same base, different suffix
                        
                b_short, b_long = (base1, base2) if len(base1) < len(base2) else (base2, base1)
                pattern = r'(?:^|\W)' + re.escape(b_short) + r'(?:$|\W)'
                if re.search(pattern, b_long):
                    raise ValidationError(f"Le nom '{record.name}' contient une partie identique au produit existant '{p.name}'.")
