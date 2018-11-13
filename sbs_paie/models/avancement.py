# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, Warning

NO_DEST_GRILLE = _(u"Veuillez définir la grille de destination")

SUBJECT_NEW_AVA = _("Nouvel avancement")
SUBJECT_CON_AVA = _("Avancement confirmé")
SUBJECT_TER_AVA = _("Avancement terminé")
SUBJECT_ANN_AVA = _("Avancement annulé")
BODY_NEW_AVA = _(u"l'avancement de l'employé %s a été créé")
BODY_CON_AVA = _(u"l'avancement de l'employé %s a été confirmé")
BODY_TER_AVA = _(u"l'avancement de l'employé %s est terminé")
BODY_ANN_AVA = _(u"l'avancement de l'employé %s est annulé")
NO_VALID_CONTRACT = _(u'Le contrat de l\'employé doit être ouvert')
NO_CONTRACT = _(u'L\'employé doit avoir un contrat en cours')


class Avancement(models.Model):

    _inherit = ['mail.thread']
    _name = 'aft_paie.avancement'
    _rec_name = 'code'
    _description = 'Avancement du personnel'
    _order = "date_avancement desc"

    code = fields.Char(
        string='Code',
        help="Code de l'avancement",
        readonly=True)

    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Employee',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]})

    contract_id = fields.Many2one(
        comodel_name='hr.contract',
        string='Contrat',
        compute="_compute_contract_id",
        store=True)

    src_grille = fields.Many2one(
        string='Grille salariale',
        readonly=True,
        help="grille salariale originale de l'employe",
        comodel_name='aft_paie.grille_salaire',
        compute="_compute_src_grille",
        store=True)

    montant_grille = fields.Float(
        string="Ancien salaire",
        related="src_grille.montant",
        readonly=True)

    num_ordre_src = fields.Integer(
        string="Ancien numero d'ordre",
        related="src_grille.num_ordre",
        readonly=True)

    dst_grille = fields.Many2one(
        comodel_name='aft_paie.grille_salaire',
        string='Grille de destination',
        readonly=True,
        states={'draft': [('readonly', False)]})

    montant_grille_dest = fields.Float(
        string="Nouveau salaire",
        related="dst_grille.montant",
        readonly=True)

    date_avancement = fields.Date(
        'Date Effective',
        readonly=True)

    date = fields.Date(
        string='Date',
        readonly=True,
        default=fields.Date.today())

    description = fields.Text(
        string='Observation',
        readonly=True,
        states={'draft': [('readonly', False)]})

    reclassement = fields.Boolean(
        string='Reclassement',
        default=False,
        help="Cochez cette case pour effectuer un reclassement",
        readonly=True,
        states={'draft': [('readonly', False)]})

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirm', 'Confirmé'),
        ('done', 'Terminé'),
        ('cancel', 'Annulé')],
        string='Etat',
        readonly=True,
        default='draft')

    @api.onchange('reclassement', 'employee_id', 'src_grille')
    def onchange_reclassement(self):
        domain = [
            ('montant', '>', self.montant_grille),
            ('num_ordre', '>', self.num_ordre_src)]
        oper = '!=' if self.reclassement else '='
        domain.append(('categ_id', oper, self.src_grille.categ_id.id))
        return {'domain': {'dst_grille': domain}}

    @api.depends("employee_id")
    def _compute_contract_id(self):
        for r in self:
            r.contract_id = None
            if r.employee_id:
                r.contract_id = r.employee_id.contract_id

    @api.depends("contract_id")
    def _compute_src_grille(self):
        for r in self:
            if r.contract_id:
                r.src_grille = r.contract_id.grille_salaire

    @api.multi
    def action_confirm(self):
        sequence_obj = self.env['ir.sequence']
        for r in self:
            r.code = sequence_obj.next_by_code(
                'paie.avancement')
            r.state = 'confirm'

            r.message_post(
                body=BODY_CON_AVA % r.employee_id.name,
                subject=SUBJECT_CON_AVA,
                message_type='notification',
                subtype="aft_paie.avancement_confirme")

    @api.multi
    def action_done(self):
        """Termine le contrat et effectue l'avancement."""
        for record in self:
            contrat = record.employee_id.contract_id

            if not record.dst_grille:
                raise ValidationError(
                    u'Veuillez definir la grille de destination')

            if not record.date:
                raise ValidationError(
                    u'Veuillez definir la date de l\'avancement')

            if not contrat:
                raise ValidationError(NO_CONTRACT)

            if contrat.state != 'open':
                raise ValidationError(NO_VALID_CONTRACT)

            contrat.grille_salaire = record.dst_grille
            record.date_avancement = fields.Date.today()
            record.state = 'done'

            record.message_post(
                body=BODY_TER_AVA % record.employee_id.name,
                subject=SUBJECT_TER_AVA,
                message_type='notification',
                subtype="aft_paie.avancement_termine")

    @api.multi
    def action_cancel(self):
        for r in self:
            r.state = 'cancel'
            r.message_post(
                body=BODY_ANN_AVA % r.employee_id.name,
                subject=SUBJECT_ANN_AVA,
                message_type='notification',
                subtype="aft_paie.avancement_annule")

    @api.constrains('state')
    def check_grille(self):
        u"""Vérifie la grille de destination."""
        grille_obj = self.env['aft_paie.grille_salaire']
        groupe_gest_paie = self.env.ref(
            'hr_payroll.group_hr_payroll_manager').mapped('users.id')
        for r in self:
            if r.state == 'draft':
                # ajoute les responsables de la paie dans les abonnés
                r.message_subscribe_users(user_ids=groupe_gest_paie)

                r.message_post(
                    body=BODY_NEW_AVA % r.employee_id.name,
                    subject=SUBJECT_NEW_AVA,
                    message_type='notification',
                    subtype="aft_paie.avancement_brouillon")

            if not r.dst_grille:
                domain = [
                    ('montant', '>', r.montant_grille),
                    ('num_ordre', '>', r.num_ordre_src)]
                if r.reclassement:
                    domain.append(
                        ('categ_id', '!=', r.src_grille.categ_id.id))
                resp = grille_obj.search(domain, limit=1)
                r.dst_grille = resp[0] if resp else None
            if r.state == 'confirm' and not r.dst_grille:
                raise ValidationError(NO_DEST_GRILLE)
