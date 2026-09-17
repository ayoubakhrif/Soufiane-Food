from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import date

class ClaimsDHLDelay(models.Model):
    _name = 'claims.dhl.delay'
    _description = 'DHL Delay Claim'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'bl_id'

    # ==========================
    # 1. Main Data
    # ==========================
    
    def action_print_report(self):
        for rec in self:
            if rec.amount_due <= 0:
                raise UserError("Cannot print report: Amount Due must be greater than 0.")
            if rec.state == 'initial':
                raise UserError("Cannot print report: Claim is in Initial state.")
            if rec.responsible_id and rec.responsible_id != self.env.user:
                raise UserError("You cannot print this report. Only the responsible user (%s) can print it." % rec.responsible_id.name)
        return self.env.ref('claims.action_report_claims_dhl_delay').report_action(self)
        
    bl_id = fields.Many2one(
        'logistique.entry',
        string='BL Reference',
        required=True,
        readonly=True,
        domain="[('bl_number', '!=', False)]",
        tracking=True
    )
    claim_date = fields.Date(string='Date de création', default=fields.Date.context_today, readonly=True)
    date_received = fields.Date(string='Date Received', readonly=True, tracking=True)
    date_waiting = fields.Date(string='Date Waiting', readonly=True, tracking=True)
    date_refused = fields.Date(string='Date Refused', readonly=True, tracking=True)
    date_resolved = fields.Date(string='Date Resolved', readonly=True, tracking=True)
    date_closed = fields.Date(string='Date Closed', readonly=True, tracking=True)

    # Auto-filled (Read-only, from BL)
    company_id = fields.Many2one(related='bl_id.ste_id', string='Société', readonly=True, store=True)
    supplier_id = fields.Many2one(related='bl_id.supplier_id', string='Supplier', readonly=True, store=True)
    origin = fields.Char(related='bl_id.origin_id.name', string='Origin', readonly=True, store=True)
    article_id = fields.Many2one(related='bl_id.article_id', string='Article', readonly=True, store=True)
    lot = fields.Char(related='bl_id.lot', string='LOT', readonly=True, store=True)
    invoice_number = fields.Char(related='bl_id.invoice_number', string='Invoice Number', readonly=True, store=True)

    # Paramètres Conteneurs & Dates (liés au BL)
    shipping_id = fields.Many2one(related='bl_id.shipping_id', string='Compagnie Maritime', readonly=True, store=True)
    container_type = fields.Selection(related='bl_id.container_type', string='Container Type', readonly=True, store=True)
    container_size = fields.Selection(related='bl_id.container_size', string='Container Size', readonly=True, store=True)
    free_surestarie_days = fields.Integer(related='bl_id.free_time', string='Franchise Surestarie', readonly=True, store=True)
    date_sortie_port = fields.Date(related='bl_id.exit_date', string='Date Sortie Plein (Exit)', readonly=True, store=True)
    date_rentree_vide = fields.Date(related='bl_id.entry_date', string='Date Rentrée Vide (Entry)', readonly=True, store=True)

    container_count = fields.Integer(
        string='Nombre de Conteneurs',
        compute='_compute_container_count',
        store=True,
        readonly=True
    )

    amount_due_calculated = fields.Float(
        string='Montant Calculé',
        compute='_compute_amount_due_calculated',
        store=True,
        help="Montant calculé automatiquement sur la tranche la plus chère."
    )
    calculation_details = fields.Text(
        string='Détail du calcul',
        compute='_compute_amount_due_calculated',
        store=True
    )

    # ==========================
    # 2. User-entered Fields
    # ==========================
    
    company_logo = fields.Binary(compute='_compute_company_logo', string='Logo Société')

    def _compute_company_logo(self):
        for rec in self:
            # Sudo to bypass access rights to core.ste
            if rec.bl_id and rec.bl_id.ste_id and rec.bl_id.ste_id.core_ste_id:
                rec.company_logo = rec.bl_id.ste_id.core_ste_id.sudo().image_1920
            else:
                rec.company_logo = False

    eta_planned = fields.Date(
        string='ETA',
        required=True,
        readonly=True,
        tracking=True
    )
    eta_dhl = fields.Date(
        string='ETA DHL',
        required=True,
        readonly=True,
        tracking=True
    )
    dhl_delay = fields.Integer(
        string='DHL Delay (Days)',
        compute='_compute_dhl_delay',
        store=True,
        readonly=True
    )
    comment = fields.Text(string='Old Comment (Deprecated)')
    
    comment_creator = fields.Text(
        string='Commentaire (Créateur)',
        help="Commentaire du créateur de la réclamation. Toujours modifiable."
    )
    comment_responsible = fields.Text(
        string='Commentaire (Responsable)',
        help="Commentaire du responsable. Toujours modifiable."
    )

    amount_due = fields.Float(
        string='Amount Due',
        tracking=True
    )

    # ==========================
    # 3. Creator & Responsibility
    # ==========================
    create_uid = fields.Many2one('res.users', string='Creator', readonly=True)
    responsible_id = fields.Many2one(
        'res.users',
        string='Responsible',
        readonly=True,
        tracking=True
    )

    # ==========================
    # 4. Workflow & States
    # ==========================
    state = fields.Selection([
        ('initial', 'Initial'),
        ('received', 'Received'),
        ('waiting', 'Waiting Supplier Response'),
        ('refused', 'Refusé'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ], string='Status', default='initial', required=True, tracking=True)

    # ==========================
    # 5. Logic
    # ==========================

    @api.depends('bl_id', 'bl_id.container_ids')
    def _compute_container_count(self):
        for rec in self:
            if rec.bl_id and rec.bl_id.container_ids:
                rec.container_count = len(rec.bl_id.container_ids)
            else:
                rec.container_count = 1

    @api.depends('eta_planned', 'eta_dhl')
    def _compute_dhl_delay(self):
        for rec in self:
            if rec.eta_planned and rec.eta_dhl:
                delta = rec.eta_dhl - rec.eta_planned
                rec.dhl_delay = delta.days + 1
            else:
                rec.dhl_delay = 0

    @api.depends(
        'dhl_delay', 'eta_planned', 'date_sortie_port', 'date_rentree_vide',
        'shipping_id', 'container_type', 'container_size', 'free_surestarie_days',
        'container_count'
    )
    def _compute_amount_due_calculated(self):
        for rec in self:
            rec.amount_due_calculated = 0.0
            rec.calculation_details = ""

            if not rec.dhl_delay or rec.dhl_delay <= 0:
                rec.calculation_details = "Aucun retard DHL détecté (Retard DHL <= 0 jours)."
                continue

            if not rec.shipping_id or not rec.container_type or not rec.container_size:
                rec.calculation_details = "Informations conteneur ou compagnie maritime incomplètes sur le BL."
                continue

            config = self.env['logistique.surest_mag.config'].search([
                ('shipping_id', '=', rec.shipping_id.id),
                ('container_type', '=', rec.container_type),
                ('container_size', '=', rec.container_size),
            ], limit=1)

            if not config:
                sel = rec._fields['container_type'].selection
                sel_list = sel(rec) if callable(sel) else sel
                type_label = dict(sel_list).get(rec.container_type, rec.container_type)
                rec.calculation_details = (
                    f"Aucun barème trouvé pour la compagnie {rec.shipping_id.name}, "
                    f"type {type_label}, taille {rec.container_size}'."
                )
                continue

            # Construction des tranches/phases tarifaires
            phases = config.phase_ids.sorted(key=lambda p: p.sequence)
            if not phases:
                rec.calculation_details = f"Aucune tranche tarifaire configurée pour {config.name_get()[0][1]}."
                continue

            # Jours totaux de Magasinage et Surestarie
            days_magasinage = 0
            if rec.eta_planned and rec.date_sortie_port and rec.date_sortie_port >= rec.eta_planned:
                days_magasinage = (rec.date_sortie_port - rec.eta_planned).days + 1

            days_surestarie = 0
            if rec.eta_planned and rec.date_rentree_vide and rec.date_rentree_vide >= rec.eta_planned:
                days_surestarie = (rec.date_rentree_vide - rec.eta_planned).days + 1

            # Retard fournisseur à imputer
            delay = rec.dhl_delay
            free_days = rec.free_surestarie_days or 0
            cnt = rec.container_count or 1

            # Découpage des tranches : construire la liste des plages [start_day, end_day, sur_rate, mag_rate, phase_name]
            tariff_ranges = []
            curr_day = 1
            for phase in phases:
                p_start = curr_day
                p_end = 999999 if phase.is_beyond else (p_start + phase.days - 1)
                p_name = f"Beyond (Taux: {phase.surestarie_rate} / {phase.magasinage_rate})" if phase.is_beyond else f"Phase {phase.sequence} ({phase.days}j, Taux: {phase.surestarie_rate} / {phase.magasinage_rate})"
                tariff_ranges.append({
                    'start': p_start,
                    'end': p_end,
                    'surestarie_rate': phase.surestarie_rate,
                    'magasinage_rate': phase.magasinage_rate,
                    'name': p_name
                })
                if phase.is_beyond:
                    break
                curr_day += phase.days

            # 1. Calcul Surestarie sur les delay derniers jours facturés
            # Les jours facturés de surestarie vont de (free_days + 1) à days_surestarie
            sur_start_billed = free_days + 1
            sur_end_billed = days_surestarie
            total_sur_ht = 0.0
            sur_details = []

            if sur_end_billed >= sur_start_billed:
                # Les delay derniers jours facturés :
                imputed_sur_start = max(sur_start_billed, sur_end_billed - delay + 1)
                imputed_sur_end = sur_end_billed
                imputed_sur_days = imputed_sur_end - imputed_sur_start + 1

                for tr in tariff_ranges:
                    overlap_start = max(tr['start'], imputed_sur_start)
                    overlap_end = min(tr['end'], imputed_sur_end)
                    if overlap_end >= overlap_start:
                        nb_days = overlap_end - overlap_start + 1
                        sub = nb_days * tr['surestarie_rate'] * cnt
                        total_sur_ht += sub
                        sur_details.append(
                            f"• {nb_days}j (jours {overlap_start} à {overlap_end}) à {tr['surestarie_rate']} MAD/j = {sub:.2f} MAD"
                        )
            else:
                sur_details.append("• 0 jour facturé (délai inclus dans la franchise de surestarie ou date rentrée vide non saisie).")

            # 2. Calcul Magasinage sur les delay derniers jours de magasinage
            total_mag_ht = 0.0
            mag_details = []

            if days_magasinage > 0:
                imputed_mag_start = max(1, days_magasinage - delay + 1)
                imputed_mag_end = days_magasinage
                imputed_mag_days = imputed_mag_end - imputed_mag_start + 1

                for tr in tariff_ranges:
                    overlap_start = max(tr['start'], imputed_mag_start)
                    overlap_end = min(tr['end'], imputed_mag_end)
                    if overlap_end >= overlap_start:
                        nb_days = overlap_end - overlap_start + 1
                        sub = nb_days * tr['magasinage_rate'] * cnt
                        total_mag_ht += sub
                        mag_details.append(
                            f"• {nb_days}j (jours {overlap_start} à {overlap_end}) à {tr['magasinage_rate']} MAD/j = {sub:.2f} MAD"
                        )
            else:
                mag_details.append("• Date de sortie non renseignée ou <= ETA.")

            total_calculated = total_sur_ht + total_mag_ht
            rec.amount_due_calculated = total_calculated

            # Libellé sécurisé pour container_type
            sel = rec._fields['container_type'].selection
            sel_list = sel(rec) if callable(sel) else sel
            type_label = dict(sel_list).get(rec.container_type, rec.container_type) or ''

            # Génération du récapitulatif textuel
            lines = [
                f"Retard DHL fournisseur : {delay} jour(s) | Conteneurs : {cnt} ({type_label} {rec.container_size}')",
                f"Compagnie : {rec.shipping_id.name} | Franchise surestarie : {free_days} jour(s)",
                "",
                f"--- SURESTARIE (Total séjour : {days_surestarie}j) ---",
                f"Tranche(s) imputée(s) : {sur_details[0] if len(sur_details) == 1 else ''}"
            ]
            if len(sur_details) > 1:
                lines.extend(sur_details)
            lines.append(f"Sous-total Surestarie : {total_sur_ht:.2f} MAD")
            lines.append("")
            lines.append(f"--- MAGASINAGE (Total séjour port : {days_magasinage}j) ---")
            lines.extend(mag_details)
            lines.append(f"Sous-total Magasinage : {total_mag_ht:.2f} MAD")
            lines.append("")
            lines.append(f"TOTAL CALCULÉ (Tranches les plus chères) : {total_calculated:.2f} MAD")

            rec.calculation_details = "\n".join(lines)

    @api.onchange('amount_due_calculated')
    def _onchange_amount_due_calculated(self):
        for rec in self:
            if rec.amount_due_calculated and (not rec.amount_due or rec.amount_due == 0.0):
                rec.amount_due = rec.amount_due_calculated

    @api.onchange('bl_id')
    def _onchange_bl_id(self):
        for rec in self:
            if rec.bl_id:
                rec.eta_planned = rec.bl_id.eta
                rec.eta_dhl = rec.bl_id.eta_dhl
                if rec.amount_due_calculated:
                    rec.amount_due = rec.amount_due_calculated

    def action_apply_calculated_amount(self):
        """Action manuelle permettant de réinitialiser le montant dû avec le montant calculé."""
        for rec in self:
            rec.amount_due = rec.amount_due_calculated

    def action_sync_logistics_data(self):
        """Synchronise manuellement les données depuis le BL (logistique.entry) et recalcule le montant dû."""
        for rec in self:
            if not rec.bl_id:
                continue
            bl = rec.bl_id
            vals = {}
            if bl.eta:
                vals['eta_planned'] = bl.eta
            if bl.eta_dhl:
                vals['eta_dhl'] = bl.eta_dhl
            
            # Si les champs related en base ont besoin d'être rafraîchis
            rec.write(vals)
            
            # Forcer le recalcul du montant dû calculé et de l'amount_due
            rec._compute_container_count()
            rec._compute_dhl_delay()
            rec._compute_amount_due_calculated()
            if rec.amount_due_calculated:
                rec.amount_due = rec.amount_due_calculated

    # ==========================
    # 6. Workflow Actions
    # ==========================

    def action_receive(self):
        """Initial -> Received. Sets current user as responsible."""
        for rec in self:
            rec.responsible_id = self.env.user
            rec.state = 'received'
            rec.date_received = fields.Date.context_today(self)

    def action_send_supplier(self):
        """Received -> Waiting"""
        self._check_responsibility()
        self.write({
            'state': 'waiting',
            'date_waiting': fields.Date.context_today(self)
        })

    def action_resolve(self):
        """Waiting -> Resolved"""
        self._check_responsibility()
        if not self.evidence_link:
             raise ValidationError("You must provide an evidence link before resolving this claim.")
        self.write({
            'state': 'resolved',
            'date_resolved': fields.Date.context_today(self)
        })

    def action_close(self):
        """Resolved -> Closed. Admin only."""
        if not self.env.user.has_group('claims.group_claims_manager'):
            raise UserError("Only Administrators can close claims.")
        self.write({
            'state': 'closed',
            'date_closed': fields.Date.context_today(self)
        })

    def action_refuse(self):
        """Waiting -> Refused. Admin or Responsible user."""
        if not self.env.user.has_group('claims.group_claims_manager'):
            self._check_responsibility()
        self.write({
            'state': 'refused',
            'date_refused': fields.Date.context_today(self)
        })

    def _check_responsibility(self):
        """Ensure only the responsible user can proceed."""
        for rec in self:
            if rec.responsible_id and rec.responsible_id != self.env.user:
                raise UserError("You are not the responsible person for this claim. Only %s can proceed." % rec.responsible_id.name)

    # ==========================
    # 7. Evidence Logic
    # ==========================
    evidence_link = fields.Char(string='Evidence Link', help="Link to proof documents (emails, reports, etc.)")
    can_see_evidence = fields.Boolean(compute='_compute_can_see_evidence')
    document_ids = fields.Many2many(
        'ir.attachment',
        'claims_dhl_attachment_rel',
        'claim_id',
        'attachment_id',
        string='Documents PDF',
        tracking=True,
        help="Upload proof documents (PDF, etc.) proving the paid amounts."
    )

    @api.depends('responsible_id')
    def _compute_can_see_evidence(self):
        is_admin = self.env.user.has_group('claims.group_claims_manager') or self.env.user.has_group('base.group_system')
        for rec in self:
            rec.can_see_evidence = is_admin or (rec.responsible_id == self.env.user)

    def action_open_evidence(self):
        self.ensure_one()
        if self.evidence_link:
            return {
                'type': 'ir.actions.act_url',
                'url': self.evidence_link,
                'target': 'new',
            }

    def action_previous_state(self):
        """Action for Admin to revert the claim to the previous state."""
        if not self.env.user.has_group('claims.group_claims_manager'):
            raise UserError("Only Administrators can turn claims to the previous state.")
        for rec in self:
            if rec.state == 'received':
                rec.write({'state': 'initial', 'date_received': False})
            elif rec.state == 'waiting':
                rec.write({'state': 'received', 'date_waiting': False})
            elif rec.state in ['resolved', 'refused']:
                rec.write({'state': 'waiting', 'date_resolved': False, 'date_refused': False})
            elif rec.state == 'closed':
                rec.write({'state': 'resolved', 'date_closed': False})
