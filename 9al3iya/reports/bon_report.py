from odoo import models, fields
from collections import defaultdict
import tempfile
import os
import logging
from ..services.google_drive_uploader import upload_to_drivev2, DEFAULT_AUTH_DIR

_logger = logging.getLogger(__name__)


class BonLivraisonReportv2(models.AbstractModel):
    _name = 'report.cal3iya.bon_report_template'
    _description = 'Bon de Livraison Groupé'

    def _get_report_values(self, docids, data=None):
        """Regroupe les sorties par client/chauffeur/société pour le rendu QWeb."""
        docs = self.env['cal3iyasortie'].browse(docids)

        grouped = defaultdict(list)
        for rec in docs:
            key = (rec.client_id.id or 0, rec.driver_id.id or 0, rec.ste_id.id or 0)
            grouped[key].append(rec)

        grouped_bons = []
        for (client_id, driver_id, ste_id), sorties in grouped.items():
            client = self.env['cal3iya.client'].browse(client_id)
            driver = self.env['cal3iya.driver'].browse(driver_id)
            ste_rec = self.env['cal3iya.ste'].browse(ste_id)
            date = min((s.date_exit for s in sorties if s.date_exit), default=None)

            grouped_bons.append({
                'client': client,
                'driver': driver,
                'ste': ste_rec.name if ste_rec else '',
                'ste_rec': ste_rec,
                'date': date,
                'lines': sorties,
            })

        return {'grouped_bons': grouped_bons}


# -------------------------------------------------------------------------
# 👇 Extension du moteur PDF Odoo pour inclure l’upload Drive automatiquement
# -------------------------------------------------------------------------

class IrActionsReportDrivev2(models.Model):
    _inherit = 'ir.actions.report'

    """Extension du rendu PDF pour uploader automatiquement sur Google Drive."""

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        # Appel normal d’Odoo pour générer le PDF
        pdf_content, content_type = super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)

        # On ne déclenche l’upload que pour ton rapport
        if report_ref == 'cal3iya.bon_report_template':
            _logger.info("=== 📄 Début upload automatique Google Drive ===")

            try:
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                tmp.write(pdf_content)
                tmp.flush()
                tmp.close()
                _logger.info(f"📂 Fichier temp créé : {tmp.name}")

                sorties = self.env['cal3iyasortie'].browse(res_ids)
                client_name = sorties[0].client_id.name or "Client"
                date_str = (sorties[0].date_exit or fields.Date.today()).strftime("%Y-%m-%d")
                file_name = f"BL_{client_name}_{date_str}.pdf"

                # Upload sur Google Drive
                link, file_id = upload_to_drivev2(tmp.name, file_name, auth_dir=DEFAULT_AUTH_DIR, ste_name=sorties[0].ste_id.name if sorties[0].ste_id else None)
                _logger.info(f"✅ Upload réussi ! Lien : {link}")

                # Mise à jour des sorties
                for s in sorties:
                    s.write({
                        'drive_file_url': link,
                        'drive_file_id': file_id,
                    })
                    _logger.info(f"🔗 Lien ajouté à la sortie ID {s.id}")

            except Exception as e:
                _logger.exception(f"❌ Erreur upload Drive : {e}")
            finally:
                if os.path.exists(tmp.name):
                    os.unlink(tmp.name)

        return pdf_content, content_type
