from odoo import models, fields, api
from datetime import date
from odoo.exceptions import ValidationError

class DanhSachHopDong(models.Model):
    _name = 'danh_sach_hop_dong'
    _description = 'Bảng danh sách hợp đồng của nhân viên'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'so_hop_dong'
    _order = 'ngay_bat_dau desc, nhan_vien_id asc'
    
    so_hop_dong = fields.Char("Số hợp đồng", required=True)
    nhan_vien_id = fields.Many2one(
        'nhan_vien',
        string='Nhân viên',
        required=True,
        ondelete='cascade'
    )
    hop_dong_id = fields.Many2one(
        'hop_dong',
        string='Loại hợp đồng',
        required=True,
        ondelete='restrict'
    )
    
    ngay_bat_dau = fields.Date("Ngày bắt đầu", required=True, default=fields.Date.today)
    ngay_ket_thuc = fields.Date("Ngày kết thúc")
    ngay_ky = fields.Date("Ngày ký", default=fields.Date.today)
    
    luong_co_ban = fields.Float("Lương cơ bản")
    phu_cap = fields.Float("Phụ cấp")
    tong_luong = fields.Float("Tổng lương", compute='_compute_tong_luong', store=True)
    
    trang_thai = fields.Selection([
        ('du_thao', 'Dự thảo'),
        ('dang_hieu_luc', 'Đang hiệu lực'),
        ('het_han', 'Hết hạn'),
        ('da_huy', 'Đã hủy'),
    ], string="Trạng thái", required=True, default='du_thao', tracking=True)  # Thêm tracking=True
    
    ghi_chu = fields.Text("Ghi chú")
    file_hop_dong = fields.Binary("File hợp đồng", attachment=True)  # Thêm attachment=True
    file_name = fields.Char("Tên file")
    
    thoi_han = fields.Integer("Thời hạn (tháng)", compute='_compute_thoi_han', store=True)
    
    ho_va_ten = fields.Char("Họ và tên", related='nhan_vien_id.ho_va_ten', readonly=True)
    ma_dinh_danh = fields.Char("Mã NV", related='nhan_vien_id.ma_dinh_danh', readonly=True)
    
    @api.depends('luong_co_ban', 'phu_cap')
    def _compute_tong_luong(self):
        """Tính tổng lương = lương cơ bản + phụ cấp"""
        for record in self:
            record.tong_luong = (record.luong_co_ban or 0) + (record.phu_cap or 0)
    
    @api.depends('ngay_bat_dau', 'ngay_ket_thuc')
    def _compute_thoi_han(self):
        """Tính thời hạn hợp đồng (số tháng)"""
        for record in self:
            if record.ngay_bat_dau and record.ngay_ket_thuc:
                delta = record.ngay_ket_thuc - record.ngay_bat_dau
                record.thoi_han = round(delta.days / 30)
            else:
                record.thoi_han = 0
    
    @api.onchange('hop_dong_id')
    def _onchange_hop_dong(self):
        """Tự động điền thời hạn và gợi ý ngày kết thúc"""
        if self.hop_dong_id and self.ngay_bat_dau:
            from dateutil.relativedelta import relativedelta
            thoi_han = self.hop_dong_id.thoi_han_mac_dinh
            if thoi_han:
                self.ngay_ket_thuc = self.ngay_bat_dau + relativedelta(months=thoi_han)
    
    @api.onchange('ngay_bat_dau')
    def _onchange_ngay_bat_dau(self):
        """Cập nhật ngày kết thúc khi thay đổi ngày bắt đầu"""
        if self.ngay_bat_dau and self.hop_dong_id:
            from dateutil.relativedelta import relativedelta
            thoi_han = self.hop_dong_id.thoi_han_mac_dinh
            if thoi_han:
                self.ngay_ket_thuc = self.ngay_bat_dau + relativedelta(months=thoi_han)
    
    @api.constrains('ngay_bat_dau', 'ngay_ket_thuc')
    def _check_ngay(self):
        """Kiểm tra ngày kết thúc phải sau ngày bắt đầu"""
        for record in self:
            if record.ngay_bat_dau and record.ngay_ket_thuc:
                if record.ngay_ket_thuc < record.ngay_bat_dau:
                    raise ValidationError("Ngày kết thúc phải sau hoặc bằng ngày bắt đầu!")
    
    @api.constrains('luong_co_ban')
    def _check_luong(self):
        """Kiểm tra lương phải > 0"""
        for record in self:
            if record.luong_co_ban and record.luong_co_ban <= 0:
                raise ValidationError("Lương cơ bản phải lớn hơn 0!")
    
    @api.constrains('nhan_vien_id', 'trang_thai')
    def _check_hop_dong_trung(self):
        """Kiểm tra nhân viên không được có 2 hợp đồng đang hiệu lực cùng lúc"""
        for record in self:
            if record.trang_thai == 'dang_hieu_luc':
                count = self.search_count([
                    ('nhan_vien_id', '=', record.nhan_vien_id.id),
                    ('trang_thai', '=', 'dang_hieu_luc'),
                    ('id', '!=', record.id)
                ])
                if count > 0:
                    raise ValidationError(
                        f"Nhân viên {record.ho_va_ten} đã có hợp đồng đang hiệu lực!"
                    )
    
    def action_set_dang_hieu_luc(self):
        """Action to set contract to 'dang_hieu_luc' (activate).

        Checks for existing active contract for the same employee and raises
        ValidationError if one exists.
        """
        for rec in self:
            if rec.trang_thai == 'du_thao':
                count = self.search_count([
                    ('nhan_vien_id', '=', rec.nhan_vien_id.id),
                    ('trang_thai', '=', 'dang_hieu_luc'),
                    ('id', '!=', rec.id),
                ])
                if count > 0:
                    raise ValidationError(
                        f"Nhân viên {rec.ho_va_ten} đã có hợp đồng đang hiệu lực!"
                    )
                rec.write({'trang_thai': 'dang_hieu_luc'})

    def action_set_het_han(self):
        """Set contract(s) to 'het_han'."""
        for rec in self:
            if rec.trang_thai == 'dang_hieu_luc':
                rec.write({'trang_thai': 'het_han'})

    def action_set_da_huy(self):
        """Set contract(s) to 'da_huy'."""
        for rec in self:
            if rec.trang_thai != 'da_huy':
                rec.write({'trang_thai': 'da_huy'})

    _sql_constraints = [
        ('so_hop_dong_unique', 'unique(so_hop_dong)', 'Số hợp đồng phải là duy nhất!')
    ]
