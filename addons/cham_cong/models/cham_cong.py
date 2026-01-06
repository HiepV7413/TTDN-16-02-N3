from odoo import models, fields, api
from datetime import time

class ChamCong(models.Model):
    _name = 'cham_cong'
    _description = 'Chấm công'

    nhan_vien_id = fields.Many2one(
        'nhan_vien',
        string="Nhân viên",
        required=True
    )

    ngay_cham_cong = fields.Date(
        string="Ngày chấm công",
        required=True,
        default=fields.Date.today
    )

    gio_vao = fields.Datetime("Giờ vào")
    gio_ra = fields.Datetime("Giờ ra")

    so_gio_nghi_trua = fields.Float(
        string="Số giờ nghỉ trưa",
        default=1.0
    )

    so_gio_lam = fields.Float(
        string="Số giờ làm",
        compute="_compute_so_gio_lam",
        store=True
    )

    trang_thai = fields.Selection(
        [
            ('di_lam', 'Đi làm'),
            ('di_muon', 'Đi muộn'),
            ('ve_som', 'Về sớm'),
            ('nghi', 'Nghỉ'),
        ],
        string='Trạng thái',
        compute='_compute_trang_thai',
        store=True
    )

    # ======================
    # TÍNH SỐ GIỜ LÀM
    # ======================
    @api.depends('gio_vao', 'gio_ra', 'so_gio_nghi_trua')
    def _compute_so_gio_lam(self):
        for rec in self:
            if rec.gio_vao and rec.gio_ra:
                delta = rec.gio_ra - rec.gio_vao
                rec.so_gio_lam = max(
                    delta.total_seconds() / 3600 - rec.so_gio_nghi_trua,
                    0
                )
            else:
                rec.so_gio_lam = 0

    # ======================
    # TÍNH TRẠNG THÁI
    # ======================
    @api.depends('gio_vao', 'gio_ra')
    def _compute_trang_thai(self):
        for rec in self:
            if not rec.gio_vao and not rec.gio_ra:
                rec.trang_thai = 'nghi'
                continue

            if rec.gio_vao:
                gio_vao_time = rec.gio_vao.time()
                if gio_vao_time > time(8, 0):
                    rec.trang_thai = 'di_muon'
                    continue

            if rec.gio_ra:
                gio_ra_time = rec.gio_ra.time()
                if gio_ra_time < time(17, 0):
                    rec.trang_thai = 've_som'
                    continue

            rec.trang_thai = 'di_lam'
