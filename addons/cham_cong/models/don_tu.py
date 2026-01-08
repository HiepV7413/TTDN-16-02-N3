# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime

class DonTu(models.Model):
    _name = 'don_tu'
    _description = 'Đơn từ'
    _rec_name = 'nhan_vien_id'

    nhan_vien_id = fields.Many2one('nhan_vien', string="Nhân viên", required=True)
    ngay_lam_don = fields.Date("Ngày làm đơn", required=True, default=fields.Date.today)
    ngay_ap_dung = fields.Date("Ngày áp dụng", required=True)
    
    trang_thai_duyet = fields.Selection([
        ('cho_duyet', 'Chờ duyệt'),
        ('da_duyet', 'Đã duyệt'),
        ('tu_choi', 'Từ chối'),
    ], string="Trạng thái phê duyệt", default='cho_duyet', required=True)

    loai_don = fields.Selection([
        ('nghi', 'Đơn xin nghỉ'),
        ('di_muon', 'Đơn xin đi muộn'),
        ('ve_som', 'Đơn xin về sớm'),
        ('tang_ca', 'Đơn xin tăng ca'),
    ], string="Loại đơn", required=True)

    # Chuyển từ Date sang Datetime
    # Dùng để ghi nhận thời điểm bắt đầu hoặc kết thúc tăng ca thực tế
    so_gio_tang_ca = fields.Datetime("Thời điểm tăng ca", default=fields.Datetime.now)

    # Thời gian cho đi muộn/về sớm (Phút)
    thoi_gian_xin = fields.Float("Thời gian xin (phút)")