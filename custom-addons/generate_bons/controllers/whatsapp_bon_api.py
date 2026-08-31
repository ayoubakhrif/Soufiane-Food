import base64
import logging
from odoo import http, SUPERUSER_ID, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

class WhatsAppBonController(http.Controller):

    @http.route('/api/whatsapp/generate_bon', type='json', auth='none', methods=['POST'], csrf=False)
    def generate_bon(self, **kwargs):
        db_name = request.httprequest.args.get('db') or 'soufianefoods'
        request.session.db = db_name
        request.update_env(user=SUPERUSER_ID)

        # 1. Vérification du groupe WhatsApp
        group_id = kwargs.get('group_id', '')
        TARGET_GROUP_ID = '120363430689222541@g.us'
        
        if group_id != TARGET_GROUP_ID:
            return {'status': 'ignored'}

        message_text = kwargs.get('message', '').strip()
        if not message_text:
            return {'status': 'ignored'}

        try:
            lines = [line.strip() for line in message_text.split('\n') if line.strip()]
            company_code = None
            date_str = None
            article_lines = []
            
            parsing_articles = False
            
            for line in lines:
                line_upper = line.upper()
                if line_upper.startswith('SOCIETE:') or line_upper.startswith('SOCIÉTÉ:'):
                    company_code = line.split(':', 1)[1].strip()
                elif line_upper.startswith('DATE:'):
                    date_str = line.split(':', 1)[1].strip()
                elif line_upper.startswith('ARTICLES:'):
                    parsing_articles = True
                elif parsing_articles and line.startswith(('-', '*', '•', '·')):
                    import re
                    line_content = line[1:].strip()
                    
                    if '|' in line_content:
                        parts = [p.strip() for p in line_content.split('|')]
                        if len(parts) >= 2:
                            art_name = parts[0]
                            qte = float(parts[1].replace(',', '.'))
                            article_lines.append({
                                'name': art_name,
                                'qte': qte,
                                'pu': None
                            })
                    else:
                        match = re.match(r'^([\d\.,]+)\s+(.+)$', line_content)
                        if match:
                            qte_str = match.group(1).replace(',', '.')
                            qte = float(qte_str)
                            art_name = match.group(2).strip()
                            article_lines.append({
                                'name': art_name,
                                'qte': qte,
                                'pu': None
                            })

            if not company_code:
                return {'status': 'error', 'message': "❌ Erreur: Code société manquant (ex: SOCIETE: SN)."}
            if not article_lines:
                return {'status': 'error', 'message': "❌ Erreur: Aucun article trouvé. Utilisez le format: '- 100 Article' ou '- Article | 100'"}

            # Find company
            company = request.env['core.ste'].sudo().search([('code', '=ilike', company_code)], limit=1)
            if not company:
                company = request.env['core.ste'].sudo().search([('name', '=ilike', company_code)], limit=1)
            if not company:
                return {'status': 'error', 'message': f"❌ Erreur: Société '{company_code}' introuvable."}

            # Parse date if provided, otherwise today
            date_val = fields.Date.context_today(company)
            if date_str:
                try:
                    from datetime import datetime
                    for fmt in ('%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d'):
                        try:
                            date_val = datetime.strptime(date_str, fmt).date()
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass

            # Prepare order lines
            bon_lines = []
            for art in article_lines:
                domain = [
                    '|', 
                    ('name', '=ilike', art['name']), 
                    ('company_article_id.alias_ids.name', '=ilike', art['name'])
                ]
                article = request.env['bon.article'].sudo().search(domain, limit=1)
                
                if not article:
                    return {'status': 'error', 'message': f"❌ Erreur: Article '{art['name']}' introuvable dans les alias ni dans la base des articles Bons."}
                
                pu = art['pu'] if art['pu'] is not None else article.pu

                bon_lines.append((0, 0, {
                    'article_id': article.id,
                    'qte': art['qte'],
                    'pu': pu,
                }))

            # Create Bon
            bon = request.env['bon.generation'].sudo().create({
                'company_id': company.id,
                'date': date_val,
                'line_ids': bon_lines
            })

            # Generate PDF
            report_action = request.env['ir.actions.report'].sudo()
            pdf_content, _ = report_action._render_qweb_pdf('generate_bons.action_report_bon_generation', res_ids=bon.ids)
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

            return {
                'status': 'success',
                'message': f"✅ Bon Proforma *{bon.name}* généré avec succès pour {company.name} !",
                'pdf_base64': pdf_base64,
                'file_name': f"Facture_Proforma_{bon.name}.pdf"
            }

        except Exception as e:
            _logger.error(f"Erreur bot bon proforma: {str(e)}")
            return {'status': 'error', 'message': f"❌ Erreur lors de la génération: {str(e)}"}
