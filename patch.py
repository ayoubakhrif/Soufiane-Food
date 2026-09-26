import codecs
import re

with codecs.open('custom-addons/kal3iya_stock/models/kal3iya_stock_stock_exit.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r'agent_id = fields\.Many2one\(.*?\)', r'\g<0>\n    order_reference = fields.Char(string=\'Ref. Commande Groupee\')', content)
content = content.replace("('done', 'Confirmé')", "('done', 'Confirmé (En route)'),\n        ('delivered', 'Livré')")
content = content.replace("if rec.state == 'done':", "if rec.state in ['done', 'delivered']:")

content += '''
    def action_deliver(self):
        for rec in self:
            if rec.state == 'done':
                rec.state = 'delivered'
'''

with codecs.open('custom-addons/kal3iya_stock/models/kal3iya_stock_stock_exit.py', 'w', encoding='utf-8') as f:
    f.write(content)
