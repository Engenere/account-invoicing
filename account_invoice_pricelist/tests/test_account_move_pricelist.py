# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import hashlib
import inspect

from odoo.tests import Form, common

from odoo.addons.sale.models.sale import SaleOrderLine as upstream

# if this hash fails then the original function it was copied from
# needs to be checked to see if there are any major changes that
# need to be updated in this module's _get_real_price_currency

VALID_HASHES = ["7c0bb27c20598327008f81aee58cdfb4"]


class TestAccountMovePricelist(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.AccountMove = self.env["account.move"]
        self.ProductPricelist = self.env["product.pricelist"]
        self.FiscalPosition = self.env["account.fiscal.position"]
        self.fiscal_position = self.FiscalPosition.create(
            {"name": "Test Fiscal Position", "active": True}
        )
        self.journal_sale = self.env["account.journal"].create(
            {"name": "Test sale journal", "type": "sale", "code": "TEST_SJ"}
        )
        # Make sure the currency of the company is USD, as this not always happens
        # To be removed in V17: https://github.com/odoo/odoo/pull/107113
        self.company = self.env.company
        self.env.cr.execute(
            "UPDATE res_company SET currency_id = %s WHERE id = %s",
            (self.env.ref("base.USD").id, self.company.id),
        )
        self.at_receivable = self.env["account.account.type"].create(
            {
                "name": "Test receivable account",
                "type": "receivable",
                "internal_group": "income",
            }
        )
        self.a_receivable = self.env["account.account"].create(
            {
                "name": "Test receivable account",
                "code": "TEST_RA",
                "user_type_id": self.at_receivable.id,
                "reconcile": True,
            }
        )
        self.product = self.env["product.template"].create(
            {"name": "Product Test", "list_price": 100.00}
        )
        self.product_0 = self.env["product.template"].create(
            {"name": "Product Test 2", "list_price": 0.00}
        )
        self.sale_pricelist = self.ProductPricelist.create(
            {
                "name": "Test Sale pricelist",
                "item_ids": [
                    (
                        0,
                        0,
                        {
                            "applied_on": "1_product",
                            "compute_price": "fixed",
                            "fixed_price": 60.00,
                            "product_tmpl_id": self.product.id,
                        },
                    )
                ],
            }
        )
        self.partner = self.env["res.partner"].create(
            {
                "name": "Test Partner",
                "property_product_pricelist": self.sale_pricelist.id,
                "property_account_receivable_id": self.a_receivable.id,
                "property_account_position_id": self.fiscal_position.id,
            }
        )
        self.sale_pricelist_fixed_without_discount = self.ProductPricelist.create(
            {
                "name": "Test Sale pricelist",
                "discount_policy": "without_discount",
                "item_ids": [
                    (
                        0,
                        0,
                        {
                            "applied_on": "1_product",
                            "compute_price": "fixed",
                            "fixed_price": 60.00,
                            "product_tmpl_id": self.product.id,
                        },
                    )
                ],
            }
        )
        self.sale_pricelist_with_discount = self.ProductPricelist.create(
            {
                "name": "Test Sale pricelist - 2",
                "discount_policy": "with_discount",
                "item_ids": [
                    (
                        0,
                        0,
                        {
                            "applied_on": "1_product",
                            "compute_price": "percentage",
                            "percent_price": 10.0,
                            "product_tmpl_id": self.product.id,
                        },
                    )
                ],
            }
        )
        self.sale_pricelist_without_discount = self.ProductPricelist.create(
            {
                "name": "Test Sale pricelist - 3",
                "discount_policy": "without_discount",
                "item_ids": [
                    (
                        0,
                        0,
                        {
                            "applied_on": "1_product",
                            "compute_price": "percentage",
                            "percent_price": 10.0,
                            "product_tmpl_id": self.product.id,
                        },
                    )
                ],
            }
        )
        self.euro_currency = self.env["res.currency"].search([("name", "=", "EUR")])
        self.sale_pricelist_with_discount_in_euros = self.ProductPricelist.create(
            {
                "name": "Test Sale pricelist - 4",
                "discount_policy": "with_discount",
                "currency_id": self.euro_currency.id,
                "item_ids": [
                    (
                        0,
                        0,
                        {
                            "applied_on": "1_product",
                            "compute_price": "percentage",
                            "percent_price": 10.0,
                            "product_tmpl_id": self.product.id,
                        },
                    )
                ],
            }
        )
        self.sale_pricelist_without_discount_in_euros = self.ProductPricelist.create(
            {
                "name": "Test Sale pricelist - 5",
                "discount_policy": "without_discount",
                "currency_id": self.euro_currency.id,
                "item_ids": [
                    (
                        0,
                        0,
                        {
                            "applied_on": "1_product",
                            "compute_price": "percentage",
                            "percent_price": 10.0,
                            "product_tmpl_id": self.product.id,
                        },
                    )
                ],
            }
        )
        self.sale_pricelist_fixed_with_discount_in_euros = self.ProductPricelist.create(
            {
                "name": "Test Sale pricelist - 6",
                "discount_policy": "with_discount",
                "currency_id": self.euro_currency.id,
                "item_ids": [
                    (
                        0,
                        0,
                        {
                            "applied_on": "1_product",
                            "compute_price": "fixed",
                            "fixed_price": 60.00,
                            "product_tmpl_id": self.product.id,
                        },
                    )
                ],
            }
        )
        self.sale_pricelist_fixed_wo_disc_euros = self.ProductPricelist.create(
            {
                "name": "Test Sale pricelist - 7",
                "discount_policy": "without_discount",
                "currency_id": self.euro_currency.id,
                "item_ids": [
                    (
                        0,
                        0,
                        {
                            "applied_on": "1_product",
                            "compute_price": "fixed",
                            "fixed_price": 60.00,
                            "product_tmpl_id": self.product.id,
                        },
                    )
                ],
            }
        )
        self.invoice = self.AccountMove.create(
            {
                "partner_id": self.partner.id,
                "move_type": "out_invoice",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.product_variant_ids[:1].id,
                            "name": "Test line",
                            "quantity": 1.0,
                            "price_unit": 100.00,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.product_variant_ids[:2].id,
                            "name": "Test line 2",
                            "quantity": 1.0,
                            "price_unit": 100.00,
                        },
                    ),
                ],
            }
        )
        # Fix currency rate of EUR -> USD to 1.5289
        usd_currency = self.env["res.currency"].search([("name", "=", "USD")])
        usd_rates = self.env["res.currency.rate"].search(
            [("currency_id", "=", usd_currency.id)]
        )
        usd_rates.unlink()
        self.env["res.currency.rate"].create(
            {
                "currency_id": usd_currency.id,
                "rate": 1.5289,
                "create_date": "2010-01-01",
                "write_date": "2010-01-01",
            }
        )

    def test_account_invoice_pricelist(self):
        self.invoice._onchange_partner_id_account_invoice_pricelist()
        self.assertEqual(self.invoice.pricelist_id, self.sale_pricelist)

    def test_account_invoice_change_pricelist(self):
        self.invoice.pricelist_id = self.sale_pricelist.id
        self.invoice.button_update_prices_from_pricelist()
        invoice_line = self.invoice.invoice_line_ids[:1]
        self.assertEqual(invoice_line.price_unit, 60.00)
        self.assertEqual(invoice_line.discount, 0.00)

    def test_account_invoice_pricelist_without_discount(self):
        self.invoice.pricelist_id = self.sale_pricelist_fixed_without_discount.id
        self.invoice.button_update_prices_from_pricelist()
        invoice_line = self.invoice.invoice_line_ids[:1]
        self.assertEqual(invoice_line.price_unit, 100.00)
        self.assertEqual(invoice_line.discount, 40.00)

    def test_account_invoice_with_discount_change_pricelist(self):
        self.invoice.pricelist_id = self.sale_pricelist_with_discount.id
        self.invoice.button_update_prices_from_pricelist()
        invoice_line = self.invoice.invoice_line_ids[:1]
        self.assertEqual(invoice_line.price_unit, 90.00)
        self.assertEqual(invoice_line.discount, 0.00)

    def test_account_invoice_without_discount_change_pricelist(self):
        self.invoice.pricelist_id = self.sale_pricelist_without_discount.id
        self.invoice.button_update_prices_from_pricelist()
        invoice_line = self.invoice.invoice_line_ids[:1]
        self.assertEqual(invoice_line.price_unit, 100.00)
        self.assertEqual(invoice_line.discount, 10.00)

    def test_account_invoice_pricelist_with_discount_secondary_currency(self):
        self.invoice.currency_id = self.euro_currency.id
        self.invoice.pricelist_id = self.sale_pricelist_with_discount_in_euros.id
        self.invoice.button_update_prices_from_pricelist()
        invoice_line = self.invoice.invoice_line_ids[:1]
        self.assertAlmostEqual(invoice_line.price_unit, 58.87)
        self.assertEqual(invoice_line.discount, 0.00)

    def test_account_invoice_pricelist_without_discount_secondary_currency(self):
        self.invoice.currency_id = self.euro_currency.id
        self.invoice.pricelist_id = self.sale_pricelist_without_discount_in_euros.id
        self.invoice.button_update_prices_from_pricelist()
        invoice_line = self.invoice.invoice_line_ids[:1]
        self.assertAlmostEqual(invoice_line.price_unit, 65.41)
        self.assertEqual(invoice_line.discount, 10.00)

    def test_account_invoice_fixed_pricelist_with_discount_secondary_currency(self):
        self.invoice.currency_id = self.euro_currency.id
        self.invoice.pricelist_id = self.sale_pricelist_fixed_with_discount_in_euros.id
        self.invoice.button_update_prices_from_pricelist()
        invoice_line = self.invoice.invoice_line_ids[:1]
        self.assertEqual(invoice_line.price_unit, 60.00)
        self.assertEqual(invoice_line.discount, 0.00)

    def test_account_invoice_fixed_pricelist_without_discount_secondary_currency(self):
        self.invoice.currency_id = self.euro_currency.id
        self.invoice.pricelist_id = self.sale_pricelist_fixed_wo_disc_euros.id
        self.invoice.button_update_prices_from_pricelist()
        invoice_line = self.invoice.invoice_line_ids[:1]
        self.assertAlmostEqual(invoice_line.price_unit, 65.41)
        self.assertEqual(invoice_line.discount, 8.27)

    def test_upstream_file_hash(self):
        """Test that copied upstream function hasn't received fixes"""
        func = inspect.getsource(upstream._get_real_price_currency).encode()
        func_hash = hashlib.md5(func).hexdigest()
        self.assertIn(func_hash, VALID_HASHES)

    def test_add_line_price_0(self):
        inv_form = Form(self.invoice)
        with inv_form.invoice_line_ids.new() as inv_line:
            inv_line.product_id = self.product_0.product_variant_ids[0]
            self.assertEqual(inv_line.discount, 0.0)
