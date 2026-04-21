from odoo import models, fields, api, _
from datetime import datetime, time

class ChargesCasaLine(models.Model):
    _inherit = 'charges.casa.line'
    
    client_id = fields.Many2one(related='charge_id.client_id', string='Client', readonly=True)
    ville = fields.Selection(related='charge_id.ville', string='Ville', readonly=True)

class CasaRecap(models.Model):
    _name = 'casa.recap'
    _description = 'Récapitulatif Quotidien'
    _order = 'date desc'

    name = fields.Char(string='Référence', compute='_compute_name', store=True)
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today
    )

    @api.depends('date')
    def _compute_name(self):
        for rec in self:
            if rec.date:
                rec.name = f"Récapitulatif du {rec.date.strftime('%d/%m/%Y')}"
            else:
                rec.name = "Nouveau Récapitulatif"

    # --- KPI Fields ---
    total_stock_casa = fields.Float(string='Total Stock Casa', compute='_compute_kpis')
    total_stock_tanger = fields.Float(string='Total Stock Tanger', compute='_compute_kpis')

    total_benefice_casa = fields.Float(string='Bénéfices Casa', compute='_compute_kpis')
    total_benefice_tanger = fields.Float(string='Bénéfices Tanger', compute='_compute_kpis')

    total_perte_casa = fields.Float(string='Pertes Casa', compute='_compute_kpis')
    total_perte_tanger = fields.Float(string='Pertes Tanger', compute='_compute_kpis')

    total_charges = fields.Float(string='Total Charges Casa', compute='_compute_kpis')
    credits_clients = fields.Float(string='Crédits Clients (Prov.)', compute='_compute_kpis')
    total_avances = fields.Float(string='Total Avances du jour', compute='_compute_kpis')
    
    total_avances_casa = fields.Float(string='Avances Casa', compute='_compute_kpis')
    total_avances_tanger = fields.Float(string='Avances Tanger', compute='_compute_kpis')
    total_avances_kenitra = fields.Float(string='Avances Kénitra', compute='_compute_kpis')
    total_avances_agadir = fields.Float(string='Avances Agadir', compute='_compute_kpis')
    total_avances_marrakech = fields.Float(string='Avances Marrakech', compute='_compute_kpis')

    # --- Display Fields for Notebook ---
    charge_line_ids = fields.Many2many('charges.casa.line', compute='_compute_trans_ids', string='Détails des Charges')
    versement_ids = fields.Many2many('casa.client.advance', compute='_compute_trans_ids', string='Versements du jour')
    virement_ids = fields.Many2many('casa.client.advance', compute='_compute_trans_ids', string='Virements du jour')
    cheque_ids = fields.Many2many('casa.client.advance', compute='_compute_trans_ids', string='Chèques du jour')
    espece_ids = fields.Many2many('casa.client.advance', compute='_compute_trans_ids', string='Espèces du jour')
    impaye_ids = fields.Many2many('casa.client.unpaid', compute='_compute_trans_ids', string='Impayés du jour')
    benefice_exit_ids = fields.Many2many('casa.stock.exit', compute='_compute_trans_ids', string='Sorties (Bénéfices)')
    perte_exit_ids = fields.Many2many('casa.stock.exit', compute='_compute_trans_ids', string='Sorties (Pertes)')
    total_impayes = fields.Float(string='Total Impayés du jour', compute='_compute_kpis')

    def action_recalculate(self):
        """Force simple reload to recompute non-stored fields"""
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def _compute_kpis(self):
        for rec in self:
            if not rec.date:
                rec.total_stock_casa = 0
                rec.total_stock_tanger = 0
                rec.total_benefice_casa = 0
                rec.total_benefice_tanger = 0
                rec.total_perte_casa = 0
                rec.total_perte_tanger = 0
                rec.total_charges = 0
                rec.credits_clients = 0
                rec.total_avances = 0
                rec.total_avances_casa = 0
                rec.total_avances_tanger = 0
                rec.total_avances_kenitra = 0
                rec.total_avances_agadir = 0
                rec.total_avances_marrakech = 0
                rec.total_impayes = 0
                continue

            recap_date = rec.date
            dt_until = datetime.combine(recap_date, time.max)

            # 1. Total Stock (Cumulative)
            moves = self.env['casa.stock.move'].search([
                ('date', '<=', dt_until),
                ('state', '=', 'done')
            ])
            
            stock_casa = 0.0
            stock_tanger = 0.0
            for m in moves:
                val = m.qty * (m.weight or 0.0) * (m.price_purchase or 0.0)
                if m.ville == 'casa':
                    stock_casa += val
                elif m.ville == 'tanger':
                    stock_tanger += val
            
            rec.total_stock_casa = stock_casa
            rec.total_stock_tanger = stock_tanger

            # 2 & 3. Total Bénéfices et Pertes des sorties (Vente - Réduction - Achat)
            exits = self.env['casa.stock.exit'].search([
                ('date', '=', recap_date),
                ('state', '=', 'done')
            ])
            
            benef_c = 0.0
            perte_c_ventes = 0.0
            for e in exits.filtered(lambda x: x.ville == 'casa'):
                margin = (e.mt_vente - getattr(e, 'discount_amount', 0.0) - e.mt_achat)
                if margin > 0:
                    benef_c += margin
                else:
                    perte_c_ventes += abs(margin)
            
            benef_t = 0.0
            perte_t_ventes = 0.0
            for e in exits.filtered(lambda x: x.ville == 'tanger'):
                margin = (e.mt_vente - getattr(e, 'discount_amount', 0.0) - e.mt_achat)
                if margin > 0:
                    benef_t += margin
                else:
                    perte_t_ventes += abs(margin)

            rec.total_benefice_casa = benef_c
            rec.total_benefice_tanger = benef_t

            # 3. Total Pertes (Explicit Pertes Stock + Pertes sur sorties)
            pertes = self.env['casa.stock.perte'].search([
                ('date', '=', recap_date),
                ('state', '=', 'done')
            ])
            perte_c = perte_c_ventes
            perte_t = perte_t_ventes
            for p in pertes:
                val = p.qty * (p.weight or 0.0) * (p.price_purchase or 0.0)
                if p.ville == 'casa':
                    perte_c += val
                elif p.ville == 'tanger':
                    perte_t += val
            rec.total_perte_casa = perte_c
            rec.total_perte_tanger = perte_t

            # 4. Total Charges (Today)
            charges = self.env['charges.casa'].search([
                ('date', '=', recap_date),
                ('state', '=', 'confirmed')
            ])
            rec.total_charges = sum(charges.mapped('total_amount'))

            # 5. Total Avances du Jour (Provisoire: draft + confirmed, excluding 'autre' and 'transport')
            avances_jour = self.env['casa.client.advance'].search([
                ('date', '=', recap_date),
                ('state', 'in', ('draft', 'confirmed')),
                ('payment_mode', 'not in', ('autre', 'transport'))
            ])
            rec.total_avances = sum(avances_jour.mapped('amount'))
            rec.total_avances_casa = sum(avances_jour.filtered(lambda a: a.ville == 'casa').mapped('amount'))
            rec.total_avances_tanger = sum(avances_jour.filtered(lambda a: a.ville == 'tanger').mapped('amount'))
            rec.total_avances_kenitra = sum(avances_jour.filtered(lambda a: a.ville == 'kenitra').mapped('amount'))
            rec.total_avances_agadir = sum(avances_jour.filtered(lambda a: a.ville == 'agadir').mapped('amount'))
            rec.total_avances_marrakech = sum(avances_jour.filtered(lambda a: a.ville == 'marrakech').mapped('amount'))

            # 5.1 Total Impayés du Jour
            impayes_jour = self.env['casa.client.unpaid'].search([
                ('date', '=', recap_date)
            ])
            rec.total_impayes = sum(impayes_jour.mapped('amount'))

            # 6. Crédits Clients (Cumulative Balance as of today using Compte Provisoire logic)
            clients = self.env['casa.client'].search([])
            total_credits = 0.0
            
            all_exits = self.env['casa.stock.exit'].search([('date', '<=', recap_date), ('state', 'in', ('confirmed', 'done'))])
            all_discounts = self.env['casa.stock.discount'].search([('date', '<=', recap_date), ('state', '=', 'confirmed')])
            all_advances = self.env['casa.client.advance'].search([('date', '<=', recap_date), ('state', 'in', ('draft', 'confirmed'))])
            all_unpaids = self.env['casa.client.unpaid'].search([('date', '<=', recap_date)])
            all_supps = self.env['casa.sortie.supp'].search([('date', '<=', recap_date)])
            
            exits_by_client = {}
            for e in all_exits:
                exits_by_client[e.client_id.id] = exits_by_client.get(e.client_id.id, 0.0) + e.mt_vente
            
            discounts_by_client = {}
            for d in all_discounts:
                discounts_by_client[d.client_id.id] = discounts_by_client.get(d.client_id.id, 0.0) + d.total_amount
            
            advances_by_client = {}
            for a in all_advances:
                advances_by_client[a.client_id.id] = advances_by_client.get(a.client_id.id, 0.0) + a.amount
            
            unpaids_by_client = {}
            for u in all_unpaids:
                unpaids_by_client[u.client_id.id] = unpaids_by_client.get(u.client_id.id, 0.0) + u.amount
            
            supps_by_client = {}
            for s in all_supps:
                supps_by_client[s.client_id.id] = supps_by_client.get(s.client_id.id, 0.0) + s.amount

            for client in clients:
                cid = client.id
                balance = (client.compte_initial or 0.0) \
                          + exits_by_client.get(cid, 0.0) \
                          - discounts_by_client.get(cid, 0.0) \
                          - advances_by_client.get(cid, 0.0) \
                          + unpaids_by_client.get(cid, 0.0) \
                          + supps_by_client.get(cid, 0.0)
                total_credits += balance
            
            rec.credits_clients = total_credits

    def _compute_trans_ids(self):
        for rec in self:
            if not rec.date:
                rec.charge_line_ids = False
                rec.versement_ids = False
                rec.virement_ids = False
                rec.cheque_ids = False
                rec.espece_ids = False
                rec.impaye_ids = False
                rec.benefice_exit_ids = False
                rec.perte_exit_ids = False
                continue

            day_charges = self.env['charges.casa'].search([('date', '=', rec.date)])
            rec.charge_line_ids = day_charges.mapped('line_ids')
            
            advances = self.env['casa.client.advance'].search([
                ('date', '=', rec.date),
                ('state', 'in', ('draft', 'confirmed'))
            ])
            rec.versement_ids = advances.filtered(lambda a: a.payment_mode == 'versement')
            rec.virement_ids = advances.filtered(lambda a: a.payment_mode == 'virement')
            rec.cheque_ids = advances.filtered(lambda a: a.payment_mode == 'cheque')
            rec.espece_ids = advances.filtered(lambda a: a.payment_mode == 'espece')

            # Impayés
            impayes = self.env['casa.client.unpaid'].search([('date', '=', rec.date)])
            rec.impaye_ids = impayes

            # Sorties (Bénéfices et Pertes)
            exits = self.env['casa.stock.exit'].search([
                ('date', '=', rec.date),
                ('state', '=', 'done')
            ])
            benef_ids = []
            perte_ids = []
            for e in exits:
                margin = (e.mt_vente - getattr(e, 'discount_amount', 0.0) - e.mt_achat)
                if margin > 0:
                    benef_ids.append(e.id)
                else:
                    perte_ids.append(e.id)
            rec.benefice_exit_ids = benef_ids
            rec.perte_exit_ids = perte_ids

