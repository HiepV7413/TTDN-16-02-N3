# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date
from odoo.exceptions import ValidationError

class NhanVien(models.Model):
    _name = 'nhan_vien'
    _description = 'Thông tin nhân viên'
    _rec_name = 'ho_va_ten'
    _order = 'ten asc, tuoi desc'

    # --- ĐỊNH DANH ---
    ma_dinh_danh = fields.Char("Mã định danh", required=True, copy=False)
    ho_ten_dem = fields.Char("Họ tên đệm", required=True)
    ten = fields.Char("Tên", required=True)
    ho_va_ten = fields.Char("Họ và tên", compute="_compute_ho_va_ten", store=True)
    anh = fields.Binary("Ảnh đại diện")

    # --- CÁ NHÂN ---
    ngay_sinh = fields.Date("Ngày sinh")
    tuoi = fields.Integer("Tuổi", compute="_compute_tuoi", store=True)
    que_quan = fields.Char("Quê quán")
    email = fields.Char("Email")
    so_dien_thoai = fields.Char("Số điện thoại")
    
    # --- CÔNG VIỆC ---
    luong_co_ban = fields.Float(string='Lương cơ bản', help='Lương cơ bản theo tháng')
    lich_su_cong_tac_ids = fields.One2many("lich_su_cong_tac", "nhan_vien_id", string="Lịch sử công tác")
    danh_sach_chung_chi_bang_cap_ids = fields.One2many("danh_sach_chung_chi_bang_cap", "nhan_vien_id", string="Chứng chỉ bằng cấp")
    
    # --- LIÊN KẾT MODULE KHÁC ---
    danh_sach_hop_dong_ids = fields.One2many('danh_sach_hop_dong', 'nhan_vien_id', string='Danh sách hợp đồng')
    cham_cong_ids = fields.One2many('cham_cong', 'nhan_vien_id', string='Lịch sử chấm công')
    luong_ids = fields.One2many('bang_luong', 'nhan_vien_id', string='Lịch sử lương')

    # --- COMPUTE FIELDS ---
    so_nguoi_bang_tuoi = fields.Integer("Số người bằng tuổi", compute="_compute_so_nguoi_bang_tuoi", store=True)
    
    hop_dong_hien_tai_id = fields.Many2one('danh_sach_hop_dong', string='Hợp đồng hiện tại', compute='_compute_hop_dong_hien_tai', store=True)
    trang_thai_hop_dong = fields.Selection(related='hop_dong_hien_tai_id.trang_thai', string='Trạng thái HĐ', readonly=True)

    so_ngay_lam_thang_nay = fields.Integer("Số ngày làm tháng này", compute='_compute_thong_ke_cham_cong')
    so_lan_tre_thang_nay = fields.Integer("Số lần trễ tháng này", compute='_compute_thong_ke_cham_cong')

    # --- CONSTRAINTS ---
    _sql_constraints = [
        ('ma_dinh_danh_unique', 'unique(ma_dinh_danh)', 'Mã định danh nhân viên phải là duy nhất!')
    ]

    @api.constrains('tuoi')
    def _check_tuoi(self):
        for record in self:
            if record.tuoi < 18:
                raise ValidationError("Nhân viên phải từ 18 tuổi trở lên.")

    # --- LOGIC XỬ LÝ ---
    @api.depends("ho_ten_dem", "ten")
    def _compute_ho_va_ten(self):
        for record in self:
            if record.ho_ten_dem and record.ten:
                record.ho_va_ten = f"{record.ho_ten_dem} {record.ten}"
            else:
                record.ho_va_ten = record.ten or record.ho_ten_dem

    @api.onchange("ten", "ho_ten_dem")
    def _default_ma_dinh_danh(self):
        for record in self:
            if record.ho_ten_dem and record.ten:
                # Lấy chữ cái đầu của họ tên đệm (VD: Nguyen Van -> nv)
                chu_cai_dau = ''.join([word[0] for word in record.ho_ten_dem.lower().split() if word])
                # Kết hợp: ten + ho_dem (VD: anh + nv -> anhnv)
                import random
                suffix = random.randint(10, 99) # Thêm số ngẫu nhiên để tránh trùng
                record.ma_dinh_danh = f"{record.ten.lower()}{chu_cai_dau}{suffix}"

    @api.depends("ngay_sinh")
    def _compute_tuoi(self):
        today = date.today()
        for record in self:
            if record.ngay_sinh:
                record.tuoi = today.year - record.ngay_sinh.year
            else:
                record.tuoi = 0

    @api.depends("tuoi")
    def _compute_so_nguoi_bang_tuoi(self):
        for record in self:
            if record.tuoi:
                # Đếm số người cùng tuổi nhưng khác ID
                count = self.search_count([
                    ('tuoi', '=', record.tuoi),
                    ('id', '!=', record.id) # Dùng ID thay vì ma_dinh_danh để an toàn hơn
                ])
                record.so_nguoi_bang_tuoi = count
            else:
                record.so_nguoi_bang_tuoi = 0

    @api.depends('danh_sach_hop_dong_ids.trang_thai')
    def _compute_hop_dong_hien_tai(self):
        for record in self:
            # Lấy hợp đồng đang hiệu lực gần nhất
            hop_dong = record.danh_sach_hop_dong_ids.filtered(lambda x: x.trang_thai == 'dang_hieu_luc')
            record.hop_dong_hien_tai_id = hop_dong[0] if hop_dong else False

    def _compute_thong_ke_cham_cong(self):
        today = fields.Date.today()
        start_of_month = today.replace(day=1)
        
        for record in self:
            # Dùng search_count để tối ưu thay vì len(filtered)
            domain_base = [
                ('nhan_vien_id', '=', record.id),
                ('ngay_cham_cong', '>=', start_of_month),
                ('ngay_cham_cong', '<=', today)
            ]
            
            record.so_ngay_lam_thang_nay = self.env['cham_cong'].search_count(
                domain_base + [('trang_thai', 'in', ['di_lam', 'di_muon', 've_som', 'di_muon_ve_som'])]
            )
            
            record.so_lan_tre_thang_nay = self.env['cham_cong'].search_count(
                domain_base + [('trang_thai', 'in', ['di_muon', 'di_muon_ve_som'])]
            )