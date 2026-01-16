# -*- coding: utf-8 -*-
from odoo import models, fields, tools

class DashboardChamCong(models.Model):
    _name = 'dashboard_cham_cong'
    _description = 'Dashboard chấm công theo tháng'
    _auto = False

    nhan_vien_id = fields.Many2one('nhan_vien', string='Nhân viên')
    thang = fields.Char(string='Tháng')
    thang_sort = fields.Date(string='Tháng')
    so_ngay_di_lam = fields.Integer(string='Số ngày đi làm')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW dashboard_cham_cong AS (
                SELECT
                    row_number() OVER (
                        ORDER BY date_trunc('month', cc.ngay_cham_cong)
                    ) AS id,

                    cc.nhan_vien_id,

                    to_char(date_trunc('month', cc.ngay_cham_cong), 'MM/YYYY') AS thang,

                    date_trunc('month', cc.ngay_cham_cong)::date AS thang_sort,

                    COUNT(cc.id) FILTER (
                        WHERE cc.trang_thai IN (
                            'di_lam', 'di_muon', 've_som', 'di_muon_ve_som'
                        )
                    ) AS so_ngay_di_lam

                FROM cham_cong cc
                WHERE cc.ngay_cham_cong >= (CURRENT_DATE - INTERVAL '12 months')
                GROUP BY
                    cc.nhan_vien_id,
                    date_trunc('month', cc.ngay_cham_cong)
            )
        """)

