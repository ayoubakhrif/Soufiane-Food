import base64
import logging
import re
from odoo import http, SUPERUSER_ID, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

class WhatsAppBonController(http.Controller):

    @http.route('/api/whatsapp/generate_bon', type='json', auth='none', methods=['POST'], csrf=False)
    def generate_bon(self, **kwargs):
        db_name = request.httprequest.args.get('db') or 'soufianefoods'
        request.session.db = db_name
        request.update_env(user=SUPERUSER_ID)

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
            poids_fictif = None
            article_lines = []
            
            parsing_articles = False
            
            for line in lines:
                line_upper = line.upper()
                if line_upper.startswith('SOCIETE:') or line_upper.startswith('SOCIÉTÉ:'):
                    company_code = line.split(':', 1)[1].strip()
                elif line_upper.startswith('DATE:'):
                    date_str = line.split(':', 1)[1].strip()
                elif line_upper.startswith('POIDS FICTIF:'):
                    try:
                        poids_fictif_str = line.split(':', 1)[1].strip().lower().replace('kg', '').replace(',', '.').strip()
                        poids_fictif = float(poids_fictif_str)
                    except ValueError:
                        pass
                elif line_upper.startswith('ARTICLES:'):
                    parsing_articles = True
                elif parsing_articles and line.startswith(('-', '*', '•', '·')):
                    line_content = line[1:].strip()
                    art_name = ""
                    qte = 0.0
                    
                    if '|' in line_content:
                        parts = [p.strip() for p in line_content.split('|')]
                        if len(parts) >= 2:
                            art_name = parts[0]
                            qte = float(parts[1].replace(',', '.'))
                    else:
                        match = re.match(r'^([\d\.,]+)\s+(.+)$', line_content)
                        if match:
                            qte = float(match.group(1).replace(',', '.'))
                            art_name = match.group(2).strip()
                    
                    if art_name:
                        # Extract weight from string like "Amandes MK BUTTE PADRE 25kg"
                        weight = None
                        w_match = re.search(r'(?i)(.*?)\s+(\d+(?:\.\d+)?)\s*kg$', art_name)
                        if w_match:
                            art_name = w_match.group(1).strip()
                            weight = float(w_match.group(2))
                            
                        article_lines.append({
                            'name': art_name,
                            'qte': qte,
                            'weight': weight,
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

            bon_lines_real = []
            bon_lines_fictif = []
            
            real_total_weight = 0.0

            for art in article_lines:
                domain = [
                    '|', 
                    ('name', '=ilike', art['name']), 
                    ('company_article_id.alias_ids.name', '=ilike', art['name'])
                ]
                article = request.env['bon.article'].sudo().search(domain, limit=1)
                
                if not article:
                    return {'status': 'error', 'message': f"❌ Erreur: Article '{art['name']}' introuvable."}
                
                pu = article.pu
                
                # Determine weight
                line_weight = art['weight']
                if line_weight is None:
                    line_weight = article.get_default_weight()
                
                real_total_weight += (art['qte'] * line_weight)

                bon_lines_real.append((0, 0, {
                    'article_id': article.id,
                    'qte': art['qte'],
                    'pu': pu,
                }))
                
                # Keep original data for fictif calculation later
                art['article_id'] = article.id
                art['pu'] = pu

            # Ratio for fictif
            ratio = 1.0
            if poids_fictif and real_total_weight > 0:
                ratio = poids_fictif / real_total_weight
                
                for art in article_lines:
                    new_qte = art['qte'] * ratio
                    bon_lines_fictif.append((0, 0, {
                        'article_id': art['article_id'],
                        'qte': new_qte,
                        'pu': art['pu'],
                    }))

            # Create Bon Réel
            bon_reel = request.env['bon.generation'].sudo().create({
                'company_id': company.id,
                'date': date_val,
                'line_ids': bon_lines_real
            })

            report_action = request.env['ir.actions.report'].sudo()
            pdf_content_reel, _ = report_action._render_qweb_pdf('generate_bons.action_report_bon_generation', res_ids=bon_reel.ids)
            b64_reel = base64.b64encode(pdf_content_reel).decode('utf-8')
            
            response_files = [{
                'pdf_base64': b64_reel,
                'file_name': f"Facture_Proforma_{bon_reel.name}.pdf",
                'mimetype': 'application/pdf'
            }]
            
            msg = f"✅ Bon Proforma *{bon_reel.name}* (Réel) généré avec succès !"
            
            if poids_fictif and bon_lines_fictif:
                bon_fictif = request.env['bon.generation'].sudo().create({
                    'company_id': company.id,
                    'date': date_val,
                    'line_ids': bon_lines_fictif
                })
                pdf_content_fictif, _ = report_action._render_qweb_pdf('generate_bons.action_report_bon_generation', res_ids=bon_fictif.ids)
                b64_fictif = base64.b64encode(pdf_content_fictif).decode('utf-8')
                
                response_files.append({
                    'pdf_base64': b64_fictif,
                    'file_name': f"Facture_Proforma_{bon_fictif.name}_Fictif.pdf",
                    'mimetype': 'application/pdf'
                })
                msg += f"\n✅ Bon Proforma *{bon_fictif.name}* (Fictif - {poids_fictif}kg) généré !"

            return {
                'status': 'success',
                'message': msg,
                'files': response_files
            }

        except Exception as e:
            _logger.error(f"Erreur bot bon proforma: {str(e)}")
            return {'status': 'error', 'message': f"❌ Erreur lors de la génération: {str(e)}"}
