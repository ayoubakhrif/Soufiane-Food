from odoo import models, fields, api
from datetime import date

class EcoleStudent(models.Model):
    _name = 'ecole.student'
    _description = 'Etudiant'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    first_name = fields.Char(string='Prénom', required=True, tracking=True)
    last_name = fields.Char(string='Nom', required=True, tracking=True)
    date_of_birth = fields.Date(string='Date de naissance', tracking=True)
    age = fields.Integer(string='Age', compute='_compute_age', store=True)
    photo = fields.Binary(string='Photo', attachment=True)
    current_class_id = fields.Many2one('ecole.class', string='Classe', tracking=True)
    academic_year = fields.Char(string='Academic Year', tracking=True, help="e.g. 2025-2026")
    status = fields.Selection([
        ('active', 'Actif'),
        ('suspended', 'Quitté')
    ], string='Status', default='active', tracking=True)
    parent_id = fields.Many2one('ecole.parent', string='Parent/Tuteur', required=True, tracking=True)
    gender = fields.Selection([
        ('male', 'Homme'),
        ('female', 'Femme')
    ], string='Sexe', tracking=True)
    phone_number = fields.Char(string='Numéro de téléphone', size=10, tracking=True)


    @api.depends('date_of_birth')
    def _compute_age(self):
        today = date.today()
        for rec in self:
            if rec.date_of_birth:
                rec.age = today.year - rec.date_of_birth.year - ((today.month, today.day) < (rec.date_of_birth.month, rec.date_of_birth.day))
            else:
                rec.age = 0