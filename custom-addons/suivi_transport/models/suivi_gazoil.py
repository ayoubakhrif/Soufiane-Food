from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class SuiviGazoil(models.Model):
    _name = 'suivi.gazoil'
    _description = 'Suivi Gazoil'
    _order = 'date desc, id desc'

    name = fields.Char(string='Référence', required=True, copy=False, readonly=True, default='/')
    chauffeur_id = fields.Many2one('suivi.chauffeur', string='Chauffeur', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    
    montant = fields.Float(string='Montant Payé (MAD)', required=True)
    prix_litre = fields.Float(string='Prix par Litre (MAD)', required=True)
    litres = fields.Float(string='Nombre de Litres', compute='_compute_litres', store=True)
    
    kilometrage = fields.Float(string='Kilométrage Actuel', required=True)
    image_compteur = fields.Image(string='Photo Compteur', max_width=1024, max_height=1024)
    
    note = fields.Text(string='Remarques')

    @api.depends('montant', 'prix_litre')
    def _compute_litres(self):
        for rec in self:
            if rec.prix_litre > 0:
                rec.litres = rec.montant / rec.prix_litre
            else:
                rec.litres = 0.0

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('suivi.gazoil') or '/'
        rec = super(SuiviGazoil, self).create(vals)
        rec._cleanup_old_images()
        return rec

    def write(self, vals):
        res = super(SuiviGazoil, self).write(vals)
        if 'image_compteur' in vals or 'chauffeur_id' in vals or 'date' in vals:
            for rec in self:
                rec._cleanup_old_images()
        return res

    def _cleanup_old_images(self):
        """ Ne garde que les 10 dernières photos de compteurs pour ce chauffeur """
        for rec in self:
            if not rec.chauffeur_id:
                continue
            records_with_images = self.env['suivi.gazoil'].search([
                ('chauffeur_id', '=', rec.chauffeur_id.id),
                ('image_compteur', '!=', False)
            ], order='date desc, id desc')
            
            if len(records_with_images) > 10:
                old_records = records_with_images[10:]
                # Ecriture en SQL pour éviter les boucles infinies ou les problèmes de droits/déclencheurs
                for old in old_records:
                    self.env.cr.execute(
                        "UPDATE suivi_gazoil SET image_compteur = NULL WHERE id = %s",
                        (old.id,)
                    )

    @api.constrains('montant', 'prix_litre', 'kilometrage')
    def _check_positive_values(self):
        for rec in self:
            if rec.montant <= 0:
                raise ValidationError(_("Le montant doit être strictement positif."))
            if rec.prix_litre <= 0:
                raise ValidationError(_("Le prix par litre doit être strictement positif."))
            if rec.kilometrage < 0:
                raise ValidationError(_("Le kilométrage ne peut pas être négatif."))

    @api.constrains('chauffeur_id', 'date', 'kilometrage')
    def _check_kilometrage_progression(self):
        for rec in self:
            if not rec.chauffeur_id or not rec.date:
                continue
            
            # Record précédent (plus récent parmi ceux avant ou égaux à la date)
            past_record = self.env['suivi.gazoil'].search([
                ('chauffeur_id', '=', rec.chauffeur_id.id),
                ('id', '!=', rec.id),
                ('date', '<=', rec.date)
            ], order='date desc, id desc', limit=1)
            
            if past_record and rec.kilometrage < past_record.kilometrage:
                raise ValidationError(_(
                    "Le kilométrage (%(current)s) ne peut pas être inférieur au kilométrage d'un plein précédent (%(past)s le %(date)s)."
                ) % {
                    'current': rec.kilometrage,
                    'past': past_record.kilometrage,
                    'date': past_record.date.strftime('%d/%m/%Y')
                })

            # Record suivant (plus ancien parmi ceux après ou égaux à la date)
            future_record = self.env['suivi.gazoil'].search([
                ('chauffeur_id', '=', rec.chauffeur_id.id),
                ('id', '!=', rec.id),
                ('date', '>=', rec.date)
            ], order='date asc, id asc', limit=1)

            if future_record and rec.kilometrage > future_record.kilometrage:
                raise ValidationError(_(
                    "Le kilométrage (%(current)s) ne peut pas être supérieur au kilométrage d'un plein ultérieur (%(future)s le %(date)s)."
                ) % {
                    'current': rec.kilometrage,
                    'future': future_record.kilometrage,
                    'date': future_record.date.strftime('%d/%m/%Y')
                })
