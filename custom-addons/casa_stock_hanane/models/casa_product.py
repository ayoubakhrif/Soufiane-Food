from odoo import models, fields, api

class CasaProduct(models.Model):
    _name = 'casa_hanane.product'
    _description = 'Produits Casa (Hanane)'
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
                
                # Instead of blocking if one contains the other entirely as a word
                # Let's split words and see if every word of short is in long
                # but if long has extra significant words, it's a different product.
                # However, the user's specific case is:
                # n1 = gingembre 25kg -> base1 = gingembre
                # n2 = gingembre frais 13kg -> base2 = gingembre frais
                # Since base2 has 'frais', they are DIFFERENT products and should not clash.
                
                # Rule: they clash if the *bases* are exactly identical, 
                # or if one is just a plural/singular variation, 
                # but if one has extra words (like 'frais', 'sec', 'rouge'), they are different.
                
                # So we just check if bases are identical (already checked above).
                # To maintain the previous requirement blocking "Amande" and "Amande 22/11",
                # where "22/11" is not a kg suffix, we need to be careful.
                
                # The exact previous code blocked if b_short was found in b_long as an exact whole word.
                # If we want to allow "gingembre frais 13kg", it means "gingembre frais" != "gingembre".
                # To fix this, let's relax the subset matching:
                # If the bases are different, we only block if the extra part is NOT a descriptive word (like frais)
                # But to keep it simple and fix the user's case, if the bases are strictly different and both have a valid kg suffix, we don't clash.
                # If one doesn't have a kg suffix (like "Amande" vs "Amande 22/11"), it might still clash.
                
                # Let's only trigger subset clash if neither of them has a kg suffix,
                # OR if one is purely a substring of the other without adding letters to the words.
                
                # Actually, blocking "Amande" and "Amande 22/11" but allowing "Gingembre" vs "Gingembre frais" is tricky.
                # Let's redefine the clash: 
                # They clash if all words in b_short are in b_long, AND b_long's extra words are NOT alphanumeric words (e.g. they are just numbers/symbols like 22/11).
                # If b_long has extra alphabetical descriptive words (like 'frais'), they do NOT clash.
                
                words_short = set(re.findall(r'\b[a-z]+\b', b_short))
                words_long = set(re.findall(r'\b[a-z]+\b', b_long))
                
                # If b_long has alphabetical words that are NOT in b_short, it's a different descriptive product
                if words_long - words_short:
                    continue # Valid! It has extra descriptive words (like 'frais')
                    
                pattern = r'(?:^|\W)' + re.escape(b_short) + r'(?:$|\W)'
                if re.search(pattern, b_long):
                    raise ValidationError(f"Le nom '{record.name}' contient une partie identique au produit existant '{p.name}' sans ajout descriptif.")
    def action_generate_product_report(self):
        self.ensure_one()
        stock_records = self.env['casa_hanane.stock.stock'].search([
            ('product_id', '=', self.id),
            ('quantity', '>', 0)
        ])
        if not stock_records:
            from odoo.exceptions import UserError
            raise UserError("Aucun stock disponible pour ce produit.")
        return self.env.ref('casa_stock_hanane.action_report_casa_stock_product').report_action(stock_records)

    def action_generate_general_report(self):
        return self.env.ref('casa_stock_hanane.action_report_casa_stock_general').report_action(None)
