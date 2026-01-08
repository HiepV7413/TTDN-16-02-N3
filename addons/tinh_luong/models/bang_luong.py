# -*- coding: utf-8 -*-
from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
from datetime import datetime, time, timedelta,date
from pytz import timezone, UTC

# Trong module tinh_luong/models/bang_luong.py

class NhanVienInheritSalary(models.Model):
    _inherit = 'nhan_vien'

    luong_ids = fields.One2many('bang_luong', 'nhan_vien_id', string='Lịch sử lương')

class BangLuong(models.Model):
    _name = 'bang_luong'
    _description = 'Bảng lương chi tiết'
    _rec_name = 'name'

    name = fields.Char(string="Tên bảng lương", compute="_compute_name", store=True)
    nhan_vien_id = fields.Many2one('nhan_vien', string="Nhân viên", required=True)
    thang = fields.Integer("Tháng", required=True, default=lambda self: date.today().month)
    nam = fields.Integer("Năm", required=True, default=lambda self: date.today().year)

    luong_co_ban = fields.Float(
        related='nhan_vien_id.luong_co_ban', 
        store=True, 
        string="Lương cơ bản (từ HĐ)"
    )
    bao_hiem_ca_nhan = fields.Float(related='nhan_vien_id.bao_hiem_ca_nhan', store=True)
    bao_hiem_xa_hoi = fields.Float(related='nhan_vien_id.bao_hiem_xa_hoi', store=True)

    # --- INPUT TỪ CHẤM CÔNG ---
    so_ngay_di_lam = fields.Float("Số ngày công", compute="_compute_data_cham_cong", store=True)
    so_ngay_vang = fields.Float("Số ngày vắng", compute="_compute_data_cham_cong", store=True)
    tong_phut_di_muon = fields.Float("Tổng phút muộn", compute="_compute_data_cham_cong", store=True)
    tong_phut_ve_som = fields.Float("Tổng phút sớm", compute="_compute_data_cham_cong", store=True)
    tong_gio_tang_ca = fields.Float("Tổng giờ tăng ca", compute="_compute_data_cham_cong", store=True)

    # --- OUTPUT TÍNH LƯƠNG ---
    luong_ngay = fields.Float("Lương 1 ngày (Chuẩn)", compute="_compute_luong_final", store=True)
    tien_phat = fields.Float("Tiền phạt", compute="_compute_luong_final", store=True)
    tong_luong = fields.Float("Thực lĩnh", compute="_compute_luong_final", store=True)
    tien_tang_ca = fields.Float("Tiền tăng ca (x2)", compute="_compute_luong_final", store=True)

    _sql_constraints = [
        ('unique_payroll_month', 'unique(nhan_vien_id, thang, nam)', 'Nhân viên này đã được tính lương cho tháng này rồi!')
    ]

    @api.depends('nhan_vien_id', 'thang', 'nam')
    def _compute_name(self):
        for rec in self:
            rec.name = f"Lương T{rec.thang}/{rec.nam} - {rec.nhan_vien_id.ho_va_ten or ''}"

    @api.depends('nhan_vien_id', 'thang', 'nam')
    def _compute_data_cham_cong(self):
        for rec in self:
            rec.so_ngay_di_lam = rec.so_ngay_vang = 0
            rec.tong_phut_di_muon = rec.tong_phut_ve_som = 0
            tong_ot_hours = 0

            start_date = date(rec.nam, rec.thang, 1)
            end_date = start_date + relativedelta(months=1, days=-1)

            cham_congs = self.env['cham_cong'].search([
                ('nhan_vien_id', '=', rec.nhan_vien_id.id),
                ('ngay_cham_cong', '>=', start_date),
                ('ngay_cham_cong', '<=', end_date)
            ])

            for cc in cham_congs:
                if cc.trang_thai == 'vang_mat':
                    rec.so_ngay_vang += 1
                else:
                    rec.so_ngay_di_lam += 1
                
                # TÍNH TOÁN GIỜ TĂNG CA TỪ DATETIME
                if cc.don_tu_id.loai_don == 'tang_ca' and cc.don_tu_id.trang_thai_duyet == 'da_duyet':
                    if cc.don_tu_id.so_gio_tang_ca:
                        # Lấy giờ ra gốc (trước khi cộng tăng ca) để tính thời lượng làm thêm
                        # Giả sử ca chiều/cả ngày kết thúc lúc 17:30 (5.5 giờ UTC nếu là VN GMT+7)
                        # Ở đây ta tính logic đơn giản: (Giờ kết thúc đơn) - (Giờ ra ca quy định thực tế)
                        
                        start_ot = cc.gio_ra_ca # Mốc này đã bao gồm tăng ca ở logic compute trên
                        # Để tính chuẩn số giờ, ta lấy mốc kết thúc trừ đi mốc ra ca mặc định
                        # Ví dụ ca hành chính ra lúc 17:30
                        user_tz = self.env.user.tz or 'UTC'
                        tz = timezone(user_tz)
                        
                        # Xác định mốc ra ca gốc (không tính OT)
                        gio_ra_goc_time = time(11, 30) if cc.ca_lam == 'Sáng' else time(17, 30)
                        dt_ra_goc = tz.localize(datetime.combine(cc.ngay_cham_cong, gio_ra_goc_time)).astimezone(UTC).replace(tzinfo=None)
                        
                        # Tính số giờ chênh lệch
                        diff = cc.don_tu_id.so_gio_tang_ca - dt_ra_goc
                        duration_hours = max(0, diff.total_seconds() / 3600.0)
                        tong_ot_hours += duration_hours

                rec.tong_phut_di_muon += cc.phut_di_muon
                rec.tong_phut_ve_som += cc.phut_ve_som
            
            rec.tong_gio_tang_ca = tong_ot_hours

    @api.depends('luong_co_ban', 'so_ngay_di_lam', 'tong_phut_di_muon', 'tong_gio_tang_ca')
    def _compute_luong_final(self):
        NGAY_CONG_CHUAN = 26.0
        GIO_LAM_NGAY = 8.0
        for rec in self:
            # 1. Tính lương cơ sở
            tong_thu_nhap_thang = (rec.luong_co_ban or 0) + (rec.bao_hiem_ca_nhan or 0) + (rec.bao_hiem_xa_hoi or 0)
            luong_1_ngay = tong_thu_nhap_thang / NGAY_CONG_CHUAN
            luong_1_gio = luong_1_ngay / GIO_LAM_NGAY
            luong_1_phut = luong_1_gio / 60

            # 2. Tiền tăng ca (Hệ số 2)
            rec.tien_tang_ca = rec.tong_gio_tang_ca * luong_1_gio * 2

            # 3. Các khoản khác
            luong_theo_cong = luong_1_ngay * rec.so_ngay_di_lam
            rec.tien_phat = (rec.tong_phut_di_muon + rec.tong_phut_ve_som) * luong_1_phut

            # 4. Tổng thực lĩnh mới
            rec.tong_luong = max(0, luong_theo_cong + rec.tien_tang_ca - rec.tien_phat)