import requests
import logging
from odoo import models, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class MaerskTrackingService(models.AbstractModel):
    _name = 'maersk.tracking.service'
    _description = 'Maersk DCSA v2.2 Tracking Service'

    MAERSK_OAUTH_URL = "https://api.maersk.com/oauth/v2/access_token"
    MAERSK_API_BASE_URL = "https://api.maersk.com/track-and-trace/v2.2"

    def _get_access_token(self):
        consumer_key = self.env['ir.config_parameter'].sudo().get_param('maersk.consumer_key')
        consumer_secret = self.env['ir.config_parameter'].sudo().get_param('maersk.consumer_secret')

        if not consumer_key or not consumer_secret:
            raise UserError(_("Les clés API Maersk ne sont pas configurées. Veuillez les renseigner dans Paramètres > Logistique."))

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'grant_type': 'client_credentials',
            'client_id': consumer_key,
            'client_secret': consumer_secret
        }

        try:
            response = requests.post(self.MAERSK_OAUTH_URL, headers=headers, data=data, timeout=15)
            if response.status_code == 200:
                token_data = response.json()
                return token_data.get('access_token')
            else:
                _logger.error("Erreur Auth Maersk: %s - %s", response.status_code, response.text)
                return None
        except Exception as e:
            _logger.exception("Erreur lors de la connexion OAuth2 Maersk: %s", str(e))
            return None

    def sync_eta_for_entry(self, entry):
        """ Fetch DCSA v2.2 events for the entry and update ETA """
        tracking_number = entry._terminal49_get_tracking_number()
        if not tracking_number:
            return

        token = self._get_access_token()
        if not token:
            entry.message_post(body=_("❌ Erreur Maersk : Impossible d'obtenir le token d'accès. Vérifiez vos clés API."))
            return

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        params = {
            'transportDocumentReference': tracking_number
        }

        try:
            response = requests.get(f"{self.MAERSK_API_BASE_URL}/events", headers=headers, params=params, timeout=15)
            
            if response.status_code == 200:
                events = response.json()
                if not events:
                    entry.message_post(body=_("ℹ️ Maersk : Aucun événement trouvé pour le BL %s.") % tracking_number)
                    return

                # Recherche du dernier ETA estimé (ARRI + EST)
                eta_date = None
                for event in events:
                    # Adapté au standard DCSA v2.2
                    if event.get('eventType') == 'TRANSPORT' and event.get('eventClassifierCode') == 'EST' and event.get('eventTypeCode') == 'ARRI':
                        date_str = event.get('eventDateTime')
                        if date_str:
                            eta_date = date_str.split('T')[0]

                if eta_date:
                    if str(entry.eta) != eta_date:
                        old_eta = entry.eta
                        entry.write({'eta': eta_date})
                        entry.message_post(body=_("✅ Mise à jour Maersk : ETA modifié de %s à %s") % (old_eta or 'vide', eta_date))
                    else:
                        _logger.info("Maersk ETA unchanged for %s", tracking_number)
                else:
                    entry.message_post(body=_("ℹ️ Maersk : Dossier trouvé mais aucun ETA (Arrival Estimated) n'est disponible pour le moment."))
            elif response.status_code == 404:
                entry.message_post(body=_("⚠️ Maersk (404) : BL non trouvé. Le Consumer Key doit être associé au Customer Code côté Maersk, ou le BL n'est pas encore visible."))
            else:
                _logger.error("Erreur Maersk API: %s - %s", response.status_code, response.text)
                entry.message_post(body=_("❌ Erreur API Maersk (Code: %s) : %s") % (response.status_code, response.text))
        except Exception as e:
            _logger.exception("Erreur requête Maersk: %s", str(e))
            entry.message_post(body=_("❌ Exception lors de l'appel à Maersk : %s") % str(e))
