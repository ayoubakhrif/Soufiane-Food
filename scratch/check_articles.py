from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)

def check_articles(env):
    articles = env['logistique.article'].search([('name', 'ilike', 'cashew')])
    for art in articles:
        print(f"ID: {art.id}, Name: {art.name}, Traduction: {art.traduction}")

# Since I can't run this directly in the Odoo environment from here, 
# I will try to find where else 'traduction' might be defined.
