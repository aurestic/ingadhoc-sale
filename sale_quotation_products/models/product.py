# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api
from openerp.osv.orm import setup_modifiers
from lxml import etree


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def fields_view_get(
            self, view_id=None, view_type=False, toolbar=False, submenu=False):
        """
        If we came from sale order, we send in context 'force_product_edit'
        and we change tree view to make editable and also field qty
        """
        res = super(ProductProduct, self).fields_view_get(
            view_id=view_id, view_type=view_type,
            toolbar=toolbar, submenu=submenu)
        sale_quotation_products = self._context.get('sale_quotation_products')
        if sale_quotation_products and view_type == 'tree':
            doc = etree.XML(res['arch'])

            # make all fields not editable
            for node in doc.xpath("//field"):
                node.set('readonly', '1')
                setup_modifiers(node, res['fields'], in_tree_view=True)

            # add qty field
            placeholder = doc.xpath("//field[1]")[0]
            placeholder.addprevious(
                etree.Element('field', {
                    'name': 'qty',
                    # we force editable no matter user rights
                    'readonly': '0',
                }))
            res['fields'].update(self.fields_get(['qty']))

            # make tree view editable
            for node in doc.xpath("/tree"):
                node.set('edit', 'true')
                node.set('create', 'false')
                node.set('editable', 'top')
            res['arch'] = etree.tostring(doc)
        return res

    @api.multi
    def write(self, vals):
        """
        Si en vals solo viene qty y force_product_edit entonces es un dummy
        write y lo hacemos con sudo
        """
        if len(vals) == 1 and vals.get('qty') and self._context.get(
                'force_product_edit'):
            self = self.sudo()
        return super(ProductProduct, self).write(vals)

    @api.one
    def _get_qty(self):
        self.qty = 0
        sale_order_id = self._context.get('active_id', False)
        if sale_order_id:
            lines = self.env['sale.order.line'].search([
                ('order_id', '=', sale_order_id),
                ('product_id', '=', self.id)])
            self.qty = sum([self.env['product.uom']._compute_qty_obj(
                line.product_uom,
                line.product_uom_qty,
                self.uom_id) for line in lines])

    @api.one
    def _set_qty(self):
        sale_order_id = self._context.get('active_id', False)
        qty = self.qty
        if sale_order_id:
            lines = self.env['sale.order.line'].search([
                ('order_id', '=', sale_order_id),
                ('product_id', '=', self.id)])
            if lines:
                (lines - lines[0]).unlink()
                lines[0].write({
                    'product_uom_qty': qty,
                    'product_uom': self.uom_id.id,
                })
            else:
                self.env['sale.order'].browse(
                    sale_order_id).add_products(self.id, qty)

    qty = fields.Integer(
        'Quantity',
        compute='_get_qty',
        inverse='_set_qty')

    # TODO Borrar si no necesitamos
    # @api.multi
    # def get_product_description(self):
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'product.product',
    #         'view_mode': 'form',
    #         'res_id': self.id,
    #         'target': 'current'
    #     }
