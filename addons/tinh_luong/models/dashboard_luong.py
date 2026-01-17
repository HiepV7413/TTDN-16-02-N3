# -*- coding: utf-8 -*-
from odoo import models, fields, tools

class DashboardLuong(models.Model):
    _name = 'dashboard_luong'
    _description = 'Dashboard tổng chi trả lương'
    _auto = False
    _rec_name = 'thang_hien_thi'
    _order = 'thang_sort'

    thang_hien_thi = fields.Char("Tháng")
    thang_sort = fields.Date("Tháng")
    tong_chi_tra = fields.Float("Tổng chi trả")

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW dashboard_luong AS (
                SELECT
                    row_number() OVER (
                        ORDER BY date_trunc('month', make_date(bl.nam, bl.thang, 1))
                    ) AS id,

                    to_char(
                        date_trunc('month', make_date(bl.nam, bl.thang, 1)),
                        'MM/YYYY'
                    ) AS thang_hien_thi,

                    date_trunc(
                        'month',
                        make_date(bl.nam, bl.thang, 1)
                    )::date AS thang_sort,

                    SUM(bl.tong_luong) AS tong_chi_tra

                FROM bang_luong bl
                WHERE make_date(bl.nam, bl.thang, 1)
                      >= (CURRENT_DATE - INTERVAL '12 months')

                GROUP BY
                    date_trunc('month', make_date(bl.nam, bl.thang, 1))
            )
        """)
