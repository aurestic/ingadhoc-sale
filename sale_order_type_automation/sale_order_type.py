# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
from openerp.exceptions import Warning


class SaleOrderTypology(models.Model):
    _inherit = 'sale.order.type'

    validate_automatically_picking = fields.Boolean(
        'Validate automatically picking',
        help="It will force availability")
    validate_automatically_invoice = fields.Boolean(
        'Validate automatically invoice',)
    payment_journal_id = fields.Many2one(
        'account.journal',
        'Payment Journal',
        domain="[('type','in', ['cash', 'bank'])]"
    )
    validate_automatically_voucher = fields.Boolean(
        'Validate automatically voucher')

    @api.onchange('payment_journal_id')
    def onchange_payment_journal_id(self):
        if self.payment_journal_id:
            self.validate_automatically_invoice = True

    @api.onchange('order_policy')
    def onchange_order_policy(self):
        if self.order_policy == 'prepaid':
            self.validate_automatically_invoice = False
            self.validate_automatically_picking = False
            self.validate_automatically_voucher = False
            self.payment_journal_id = False
            self.journal_id = False
        elif self.order_policy == 'manual':
            self.invoice_state = 'none'
        else:
            self.invoice_state = '2binvoiced'

    @api.multi
    @api.constrains(
        'journal_id',
        'payment_journal_id',
        'refund_journal_id',
        'sequence_id')
    def validate_company_id(self):
        text = _(
            'The Journal "%s" company must be the same than sale order type')
        for record in self:
            if record.journal_id and record.journal_id.company_id != record.company_id:
                raise Warning(text % record.journal_id.name)
            if record.payment_journal_id and record.payment_journal_id.company_id != record.company_id:
                raise Warning(text % record.payment_journal_id.name)
            if record.refund_journal_id and record.refund_journal_id.company_id != record.company_id:
                raise Warning(text % record.refund_journal_id.name)
            if record.sequence_id and record.sequence_id.company_id != record.company_id:
                raise Warning(_(
                    'The Sequence "%s" company must be the same than'
                    ' sale order type') % record.sequence_id.name)
