# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import api, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def action_button_confirm(self):
        res = super(SaleOrder, self).action_button_confirm()

        validate_picking = self.type_id.validate_automatically_picking
        validate_invoice = self.type_id.validate_automatically_invoice
        validate_voucher = self.type_id.validate_automatically_voucher

        if validate_picking and self.picking_ids:
            self.picking_ids[0].force_assign()
            detail_transfer_id = self.picking_ids[0].transfer_details()
            self.env['stock.transfer_details'].browse(
                detail_transfer_id).do_detailed_transfer()

        if self.type_id.journal_id and validate_invoice:

            picking_ids = self.picking_ids.ids

            picking = self.picking_ids.filtered(lambda x: x.picking_type_code == 'outgoing')[:1]

            # Creamos factura desde albaran si el control de facturas es para ser facturado
            if validate_picking and picking_ids and picking.invoice_state == '2binvoiced':
                self.env['stock.invoice.onshipping'].with_context(active_ids=picking_ids).create({}).open_invoice()
                invoice_id = picking.invoice_id.id
            # La creamos desde el pedido
            else:
                invoice_id = self.action_invoice_create()

            inv = self.env['account.invoice'].browse(invoice_id)
            inv.browse(invoice_id).signal_workflow('invoice_open')

            if self.type_id.payment_journal_id:
                if inv:
                    account_voucher_obj = self.env['account.voucher']
                    amount = inv.type in ('out_refund', 'in_refund') and -inv.residual or inv.residual
                    voucher = account_voucher_obj.create({
                        "name": "",
                        "amount": amount,
                        "journal_id": self.type_id.payment_journal_id.id,
                        "account_id": inv.partner_id.property_account_receivable.id,
                        "period_id": account_voucher_obj._get_period(),
                        "partner_id": self.env['res.partner']._find_accounting_partner(inv.partner_id).id,
                        "type": inv.type in ('out_invoice', 'out_refund') and 'receipt' or 'payment'
                    })
                    self.env["account.voucher.line"].create({
                        "name": "",
                        "payment_option": "without_writeoff",
                        "amount": amount,
                        "voucher_id": voucher.id,
                        "partner_id": inv.partner_id.id,
                        "account_id": inv.partner_id.property_account_receivable.id,
                        "type": "cr",
                        "move_line_id": inv.move_id.line_id[0].id,
                    })
                    if validate_voucher:
                        voucher.button_proforma_voucher()

        # Llamamos al action_done por si el workflow no es capaz de actualizar el estado del pedido.
        if validate_picking or validate_invoice:
            picking = self.picking_ids.filtered(lambda x: x.picking_type_code == 'outgoing')[:1]
            if validate_invoice:
                self.action_done()
            elif validate_picking and (self.order_policy == 'picking' or picking.invoice_state != 'none'):
                self.action_done()

        return res
