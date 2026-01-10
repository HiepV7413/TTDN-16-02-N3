from odoo import models, fields, api
from odoo.exceptions import ValidationError

class NguoiPhuThuoc(models.Model):
    _name = 'nguoi_phu_thuoc'
    _description = 'Người phụ thuộc của nhân viên'
    _order = 'ngay_bat_dau_giam_tru desc'

    nhan_vien_id = fields.Many2one(
        'nhan_vien',
        string='Nhân viên',
        required=True,
        ondelete='cascade'
    )

    ho_ten = fields.Char("Họ và tên", required=True)
    ngay_sinh = fields.Date("Ngày sinh")

    quan_he = fields.Selection([
        ('con', 'Con'),
        ('vo_chong', 'Vợ / Chồng'),
        ('cha_me', 'Cha / Mẹ'),
        ('nguoi_khac', 'Người khác'),
    ], string="Quan hệ", required=True)

    ma_so_thue = fields.Char("Mã số thuế người phụ thuộc")

    ngay_bat_dau_giam_tru = fields.Date(
        "Ngày bắt đầu giảm trừ",
        required=True
    )
    ngay_ket_thuc_giam_tru = fields.Date(
        "Ngày kết thúc giảm trừ"
    )

    dang_hieu_luc = fields.Boolean(
        "Đang được giảm trừ",
        compute="_compute_dang_hieu_luc",
        store=True
    )

    ghi_chu = fields.Text("Ghi chú")

    @api.depends('ngay_bat_dau_giam_tru', 'ngay_ket_thuc_giam_tru')
    def _compute_dang_hieu_luc(self):
        today = fields.Date.today()
        for rec in self:
            # Mặc định là KHÔNG hiệu lực
            rec.dang_hieu_luc = False

            # BẮT BUỘC phải có ngày bắt đầu
            if not rec.ngay_bat_dau_giam_tru:
                continue

            # So sánh an toàn
            if rec.ngay_bat_dau_giam_tru <= today:
                if not rec.ngay_ket_thuc_giam_tru or rec.ngay_ket_thuc_giam_tru >= today:
                    rec.dang_hieu_luc = True


    @api.constrains('ngay_bat_dau_giam_tru', 'ngay_ket_thuc_giam_tru')
    def _check_date(self):
        for rec in self:
            if (
                rec.ngay_bat_dau_giam_tru
                and rec.ngay_ket_thuc_giam_tru
                and rec.ngay_ket_thuc_giam_tru < rec.ngay_bat_dau_giam_tru
            ):
                raise ValidationError("Ngày kết thúc phải sau ngày bắt đầu!")
