from odoo import models, fields, api
from datetime import date
from odoo.exceptions import ValidationError

class HopDong(models.Model):
    _name = 'hop_dong'
    _description = 'Bảng chứa các loại hợp đồng'
    _rec_name = 'ten_hop_dong'
    _order = 'ten_hop_dong asc'
    
    ten_hop_dong = fields.Char("Tên hợp đồng", required=True)
    ma_hop_dong = fields.Char("Mã hợp đồng", required=True)
    mo_ta = fields.Text("Mô tả")
    thoi_han_mac_dinh = fields.Integer("Thời hạn mặc định (tháng)", default=12)
    loai = fields.Selection([
        ('thu_viec', 'Thử việc'),
        ('xac_dinh_thoi_han', 'Xác định thời hạn'),
        ('khong_xac_dinh_thoi_han', 'Không xác định thời hạn'),
        ('cong_tac_vien', 'Cộng tác viên'),
        ('part_time', 'Bán thời gian'),
    ], string="Loại hợp đồng", required=True, default='thu_viec')
    
    active = fields.Boolean("Đang sử dụng", default=True)
    
    danh_sach_hop_dong_ids = fields.One2many(
        'danh_sach_hop_dong',
        inverse_name='hop_dong_id',
        string='Danh sách nhân viên'
    )
    
    so_nhan_vien = fields.Integer(
        "Số nhân viên đang sử dụng",
        compute='_compute_so_nhan_vien',
        store=True
    )
    
    @api.depends('danh_sach_hop_dong_ids')
    def _compute_so_nhan_vien(self):
        for record in self:
            record.so_nhan_vien = len(record.danh_sach_hop_dong_ids.filtered(
                lambda x: x.trang_thai == 'dang_hieu_luc'
            ))
    
    _sql_constraints = [
        ('ma_hop_dong_unique', 'unique(ma_hop_dong)', 'Mã hợp đồng phải là duy nhất!')
    ]
