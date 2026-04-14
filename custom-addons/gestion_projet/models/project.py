from odoo import models, fields, api

class ProjectManagement(models.Model):
    _name = 'project.management'
    _description = 'Project Management'

    name = fields.Char(string='Project Name', required=True)
    manager_id = fields.Many2one('core.employee', string='Manager')
    task_ids = fields.One2many('project.task.line', 'project_id', string='Tasks Notebook')

    def action_generate_report(self):
        self.ensure_one()
        return self.env.ref('gestion_projet.action_report_project_management').report_action(self)

class ProjectTaskLine(models.Model):
    _name = 'project.task.line'
    _description = 'Project Task Line'

    name = fields.Char(string='Task Name')
    manager_id = fields.Many2one('core.employee', string='Task Manager')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    complexity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], string='Complexity')
    project_id = fields.Many2one('project.management', string='Project', required=True, ondelete='cascade')
