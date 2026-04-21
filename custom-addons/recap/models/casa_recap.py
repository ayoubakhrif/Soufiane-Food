from odoo import models, fields, api, _
from datetime import datetime, time

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
    currency_id = fields.Many2one('res.currency', string='Devise', default=lambda self: self.env.company.currency_id)

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
    total_benefices = fields.Float(string='Total Bénéfices', compute='_compute_kpis')
    total_perte = fields.Float(string='Total Pertes', compute='_compute_kpis')
    total_charges = fields.Float(string='Total Charges Casa', compute='_compute_kpis')
    credits_clients = fields.Float(string='Crédits Clients', compute='_compute_kpis')

    # --- Display Fields for Notebook ---
    charge_ids = fields.Many2many('charges.casa', compute='_compute_trans_ids', string='Charges du jour')
    versement_ids = fields.Many2many('casa.client.advance', compute='_compute_trans_ids', string='Versements du jour')
    virement_ids = fields.Many2many('casa.client.advance', compute='_compute_trans_ids', string='Virements du jour')
    cheque_ids = fields.Many2many('casa.client.advance', compute='_compute_trans_ids', string='Chèques du jour')

    def _compute_kpis(self):
        for rec in self:
            if not rec.date:
                rec.total_stock_casa = 0
                rec.total_stock_tanger = 0
                rec.total_benefices = 0
                rec.total_perte = 0
                rec.total_charges = 0
                rec.credits_clients = 0
                continue

            recap_date = rec.date
            # Datetime for moves filtering (end of day)
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

            # 2. Total Bénéfices (Today)
            exits = self.env['casa.stock.exit'].search([
                ('date', '=', recap_date),
                ('state', '=', 'done')
            ])
            rec.total_benefices = sum(exits.mapped('margin'))

            # 3. Total Pertes (Today)
            pertes = self.env['casa.stock.perte'].search([
                ('date', '=', recap_date),
                ('state', '=', 'done')
            ])
            perte_val = 0.0
            for p in pertes:
                perte_val += p.qty * (p.weight or 0.0) * (p.price_purchase or 0.0)
            rec.total_perte = perte_val

            # 4. Total Charges (Today)
            charges = self.env['charges.casa'].search([
                ('date', '=', recap_date),
                ('state', '=', 'confirmed')
            ])
            rec.total_charges = sum(charges.mapped('total_amount'))

            # 5. Crédits Clients (Cumulative Balance as of today)
            # Balance = Initial + Ventes - Discounts - Advances + Impayes + SortiesSupp
            clients = self.env['casa.client'].search([])
            total_credits = 0.0
            
            # Optimization: aggregate data
            all_exits = self.env['casa.stock.exit'].search([('date', '<=', recap_date), ('state', '=', 'done')])
            all_discounts = self.env['casa.stock.discount'].search([('date', '<=', recap_date), ('state', '=', 'confirmed')])
            all_advances = self.env['casa.client.advance'].search([('date', '<=', recap_date), ('state', '=', 'confirmed')])
            all_unpaids = self.env['casa.client.unpaid'].search([('date', '<=', recap_date)])
            all_supps = self.env['casa.sortie.supp'].search([('date', '<=', recap_date)])
            
            # Map by client
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
                rec.charge_ids = False
                rec.versement_ids = False
                rec.virement_ids = False
                rec.cheque_ids = False
                continue

            rec.charge_ids = self.env['charges.casa'].search([('date', '=', rec.date)])
            
            advances = self.env['casa.client.advance'].search([
                ('date', '=', rec.date),
                ('state', '=', 'confirmed')
            ])
            rec.versement_ids = advances.filtered(lambda a: a.payment_mode == 'versement')
            rec.virement_ids = advances.filtered(lambda a: a.payment_mode == 'virement')
            rec.cheque_ids = advances.filtered(lambda a: a.payment_mode == 'cheque')
