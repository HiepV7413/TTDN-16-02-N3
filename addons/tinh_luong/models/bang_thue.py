from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ThueThuNhap(models.Model):
    _name = 'thue_thu_nhap'
    _description = 'Cau hinh Thue TNCN 2026'
    _order = 'ap_dung_tu desc'

    name = fields.Char(string='Tên thuế', required=True, default="Thuế TNCN 2026")
    ma_thue = fields.Char(string='Mã thuế', required=True, copy=False)
    
    # Dùng currency_id để hiển thị định dạng tiền tệ (VNĐ)
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', 
                                 default=lambda self: self.env.ref('base.VND'))

    loai_thue = fields.Selection([
        ('luy_tien', 'Thuế lũy tiến (Biểu thuế 5 bậc)'),
        ('co_dinh', 'Thuế suất cố định'),
    ], default='luy_tien', required=True)

    ap_dung_tu = fields.Date(string='Ngày bắt đầu hiệu lực', required=True)
    ap_dung_den = fields.Date(string='Ngày hết hiệu lực')

    # Giá trị mặc định theo luật 2026
    giam_tru_ban_than = fields.Monetary(string='Giảm trừ bản thân', default=15500000, currency_field='currency_id')
    giam_tru_nguoi_phu_thuoc = fields.Monetary(string='Giảm trừ người phụ thuộc', default=6200000, currency_field='currency_id')

    trang_thai = fields.Selection([
        ('dang_ap_dung', 'Đang áp dụng'),
        ('het_hieu_luc', 'Hết hiệu lực')
    ], compute='_compute_trang_thai', store=True)

    bac_ids = fields.One2many('thue_thu_nhap_bac', 'thue_id', string='Chi tiết bậc thuế')
    ghi_chu = fields.Text(string='Ghi chú pháp lý')

    @api.depends('ap_dung_tu', 'ap_dung_den')
    def _compute_trang_thai(self):
        today = fields.Date.today()
        for rec in self:
            if rec.ap_dung_tu and rec.ap_dung_tu <= today and (not rec.ap_dung_den or rec.ap_dung_den >= today):
                rec.trang_thai = 'dang_ap_dung'
            else:
                rec.trang_thai = 'het_hieu_luc'
