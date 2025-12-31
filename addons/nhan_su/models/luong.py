from odoo import models, fields, api
from datetime import date

from odoo.exceptions import ValidationError


class Luong(models.Model):
    _name = 'luong'
    _description = 'Bảng lương'
    _order = 'nam desc, thang desc'

    nhan_vien_id = fields.Many2one(
        'nhan_vien',
        string='Nhân viên',
        required=True,
        ondelete='cascade',
    )

    thang = fields.Integer(
        string='Tháng',
        required=True,
        default=lambda self: date.today().month
    )

    nam = fields.Integer(
        string='Năm',
        required=True,
        default=lambda self: date.today().year
    )

    cham_cong_ids = fields.One2many(
        'cham_cong',
        'luong_id',
        string='Chấm công tháng'
    )

    so_cong = fields.Integer(
        string='Số công',
        compute='_compute_so_cong',
        store=True
    )

    thuong = fields.Float(string='Thưởng', default=0)
    phat = fields.Float(string='Phạt', default=0)

    tong_luong = fields.Float(
        string='Tổng lương',
        compute='_compute_tong_luong',
        store=True
    )

    @api.depends('cham_cong_ids')
    def _compute_so_cong(self):
        for record in self:
            record.so_cong = len(record.cham_cong_ids)

    @api.depends(
        'so_cong',
        'thuong',
        'phat',
        'nhan_vien_id.luong_co_ban'
    )
    def _compute_tong_luong(self):
        for record in self:
            if not record.nhan_vien_id:
                record.tong_luong = 0
                continue

            # Công chuẩn 26 ngày / tháng
            luong_1_cong = record.nhan_vien_id.luong_co_ban / 26

            record.tong_luong = (
                record.so_cong * luong_1_cong
                + record.thuong
                - record.phat
            )

    @api.constrains('nhan_vien_id', 'ngay_cham_cong')
    def _check_luong_thang(self):
        for record in self:
            if not record.nhan_vien_id or not record.ngay_cham_cong:
                continue

            thang = record.ngay_cham_cong.month
            nam = record.ngay_cham_cong.year

            luong = self.env['luong'].search([
                ('nhan_vien_id', '=', record.nhan_vien_id.id),
                ('thang', '=', thang),
                ('nam', '=', nam)
            ], limit=1)

            if not luong:
                raise ValidationError(
                    f"Nhân viên '{record.nhan_vien_id.ho_va_ten}' "
                    f"chưa có bảng lương tháng {thang}/{nam}."
                )

            # 🔒 GÁN CỨNG BẢNG LƯƠNG ĐÚNG
            record.luong_id = luong.id
