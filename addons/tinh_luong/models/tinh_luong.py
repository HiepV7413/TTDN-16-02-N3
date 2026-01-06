# models/payroll.py
from odoo import models, fields, api

class TinhLuong(models.Model):
    _name = 'tinh_luong'
    _description = 'Bảng lương'

    nhan_vien_id = fields.Many2one('nhan_vien', string="Nhân viên", required=True)
    thang = fields.Integer("Tháng", required=True)
    nam = fields.Integer("Năm", required=True)

    tong_so_gio_lam = fields.Float("Tổng giờ làm")
    luong = fields.Float("Lương thực lĩnh")
