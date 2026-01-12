# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date

class TienThuong(models.Model):
    _name = 'tien_thuong'
    _description = 'Tiền thưởng'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'nam desc, thang desc, id desc'

    # ======================
    # THÔNG TIN CHUNG
    # ======================
    name = fields.Char(
        string='Mã thưởng',
        compute='_compute_name',
        store=True
    )

    thang = fields.Integer(
        string='Tháng áp dụng',
        required=True,
        default=lambda self: date.today().month
    )

    nam = fields.Integer(
        string='Năm áp dụng',
        required=True,
        default=lambda self: date.today().year
    )

    so_tien = fields.Float(
        string='Số tiền thưởng',
        required=True,
        tracking=True
    )

    ly_do = fields.Text(
        string='Lý do thưởng',
        required=True
    )

    # ======================
    # PHẠM VI THƯỞNG
    # ======================
    kieu_thuong = fields.Selection([
        ('mot_nguoi', 'Thưởng cho 1 nhân viên'),
        ('tat_ca', 'Thưởng cho toàn bộ nhân viên')
    ], string='Hình thức thưởng', default='mot_nguoi', required=True)

    nhan_vien_id = fields.Many2one(
        'nhan_vien',
        string='Nhân viên được thưởng',
        tracking=True
    )

    # ======================
    # TÍCH HỢP LƯƠNG
    # ======================
    cong_vao_luong = fields.Boolean(
        string='Cộng vào lương',
        default=True,
        help='Nếu bật, tiền thưởng sẽ được cộng vào bảng lương'
    )

    # ======================
    # TRẠNG THÁI
    # ======================
    trang_thai = fields.Selection([
        ('nhap', 'Nháp'),
        ('da_duyet', 'Đã duyệt'),
        ('da_chi', 'Đã chi trả'),
    ], string='Trạng thái', default='nhap', tracking=True)

    ngay_duyet = fields.Date('Ngày duyệt')
    nguoi_duyet_id = fields.Many2one('res.users', string='Người duyệt')

    ghi_chu = fields.Text('Ghi chú nội bộ')

    # ======================
    # CONSTRAINT
    # ======================
    @api.constrains('kieu_thuong', 'nhan_vien_id')
    def _check_nhan_vien(self):
        for rec in self:
            if rec.kieu_thuong == 'mot_nguoi' and not rec.nhan_vien_id:
                raise ValidationError("Phải chọn nhân viên khi thưởng cho 1 người!")

    # ======================
    # COMPUTE
    # ======================
    @api.depends('thang', 'nam', 'kieu_thuong', 'nhan_vien_id')
    def _compute_name(self):
        for rec in self:
            if rec.kieu_thuong == 'mot_nguoi' and rec.nhan_vien_id:
                rec.name = f"TH-{rec.thang:02d}/{rec.nam}-{rec.nhan_vien_id.ma_dinh_danh}"
            else:
                rec.name = f"TH-{rec.thang:02d}/{rec.nam}-ALL"

    # ======================
    # ACTIONS
    # ======================
    def action_duyet(self):
        for rec in self:
            if rec.trang_thai != 'nhap':
                continue
            rec.trang_thai = 'da_duyet'
            rec.ngay_duyet = fields.Date.today()
            rec.nguoi_duyet_id = self.env.user.id

    def action_da_chi(self):
        for rec in self:
            if rec.trang_thai != 'da_duyet':
                raise ValidationError("Tiền thưởng phải được duyệt trước khi chi!")
            rec.trang_thai = 'da_chi'
