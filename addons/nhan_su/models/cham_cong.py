from odoo import models, fields, api
from datetime import date
from odoo.exceptions import ValidationError


class ChamCong(models.Model):
    _name = 'cham_cong'
    _description = 'Bảng chứa thông tin chấm công'
    _order = 'ngay_cham_cong desc'

    nhan_vien_id = fields.Many2one(
        'nhan_vien',
        string='Nhân viên',
        required=True,
        ondelete='cascade'
    )

    luong_id = fields.Many2one(
        'luong',
        string='Bảng lương',
        ondelete='set null'
    )

    ngay_cham_cong = fields.Date(
        string='Ngày chấm công',
        required=True,
        default=fields.Date.today
    )

    gio_vao = fields.Float(
        string='Giờ vào',
        help='Ví dụ: 8.0 = 08:00'
    )

    gio_ra = fields.Float(
        string='Giờ ra',
        help='Ví dụ: 17.0 = 17:00'
    )

    so_gio_nghi_trua = fields.Float(
        string='Số giờ nghỉ trưa',
        default=1.0
    )

    so_gio_lam = fields.Float(
        string='Số giờ làm',
        compute='_compute_so_gio_lam',
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

    @api.depends('gio_vao', 'gio_ra', 'so_gio_nghi_trua')
    def _compute_so_gio_lam(self):
        for record in self:
            if record.gio_vao is not None and record.gio_ra is not None:
                tong_gio = record.gio_ra - record.gio_vao
                record.so_gio_lam = max(
                    tong_gio - (record.so_gio_nghi_trua or 0),
                    0
                )
            else:
                record.so_gio_lam = 0

    @api.depends('gio_vao', 'gio_ra')
    def _compute_trang_thai(self):
        for record in self:
            if record.gio_vao is None and record.gio_ra is None:
                record.trang_thai = 'nghi'
            elif record.gio_vao and record.gio_vao > 8:
                record.trang_thai = 'di_muon'
            elif record.gio_ra and record.gio_ra < 17:
                record.trang_thai = 've_som'
            else:
                record.trang_thai = 'di_lam'

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
                    f"chưa có bảng lương tháng {thang}/{nam}. "
                    f"Vui lòng tạo bảng lương trước khi chấm công."
                )

            # Tự động gán bảng lương nếu chưa có
            record.luong_id = luong.id

    @api.constrains('nhan_vien_id', 'luong_id')
    def _check_nhan_vien_luong(self):
        for record in self:
            if record.luong_id and record.nhan_vien_id:
                if record.luong_id.nhan_vien_id != record.nhan_vien_id:
                    raise ValidationError(
                        "Nhân viên chấm công phải trùng với nhân viên của bảng lương."
                    )
