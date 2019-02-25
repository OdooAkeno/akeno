# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import datetime
from dateutil.relativedelta import relativedelta

DATE_FORMAT = "%Y-%m-%d"


class HrEmployee(models.Model):

    _inherit = 'hr.employee'

    age = fields.Integer(
        store=False,
        compute="_compute_age",
        readonly=True)

    @api.multi
    def _compute_age(self):
        for r in self:
            r.age = 0
            if r.birthday:
                dob = datetime.strptime(r.birthday[:10], DATE_FORMAT)
                r.age = relativedelta(datetime.now(), dob).years
