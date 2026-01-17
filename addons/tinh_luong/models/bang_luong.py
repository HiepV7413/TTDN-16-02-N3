# -*- coding: utf-8 -*-
from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
from datetime import datetime, time, timedelta,date
from pytz import timezone, UTC
from calendar import monthrange

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
    phu_cap = fields.Float(related='nhan_vien_id.phu_cap', store=True)

    tien_thuong = fields.Float(
        string="Tiền thưởng",
        compute="_compute_tien_thuong",
        store=True,
        readonly=True
    )

    tien_bh_ca_nhan = fields.Float(
        string="BH cá nhân",
        compute="_compute_luong_final",
        store=True
    )

    tien_bh_xa_hoi = fields.Float(
        string="BH xã hội",
        compute="_compute_luong_final",
        store=True
    )



    # --- INPUT TỪ CHẤM CÔNG ---
    so_ngay_di_lam = fields.Float("Số ngày công", compute="_compute_data_cham_cong", store=True)
    so_ngay_vang = fields.Float("Số ngày vắng", compute="_compute_data_cham_cong", store=True)
    tong_phut_di_muon = fields.Float("Tổng phút muộn", compute="_compute_data_cham_cong", store=True)
    tong_phut_ve_som = fields.Float("Tổng phút sớm", compute="_compute_data_cham_cong", store=True)
    tong_gio_tang_ca = fields.Float("Tổng giờ tăng ca", compute="_compute_data_cham_cong", store=True)

    # --- OUTPUT TÍNH LƯƠNG ---
    luong_ngay = fields.Float("Lương 1 ngày", compute="_compute_luong_final", store=True)
    tien_phat = fields.Float("Tiền phạt", compute="_compute_luong_final", store=True)
    tong_luong = fields.Float("Thực lĩnh", compute="_compute_luong_final", store=True)
    tien_tang_ca = fields.Float("Tiền tăng ca (x2)", compute="_compute_luong_final", store=True)
    thue_id = fields.Many2one(
    'thue_thu_nhap',
    string='Thuế áp dụng',
    domain=[('trang_thai', '=', 'dang_ap_dung')]
    )

    tien_thue_tncn = fields.Float(
    string='Thuế TNCN',
    compute='_compute_luong_final',
    store=True
    )
    


    _sql_constraints = [
        ('unique_payroll_month', 'unique(nhan_vien_id, thang, nam)', 'Nhân viên này đã được tính lương cho tháng này rồi!')
    ]

    @api.depends('nhan_vien_id', 'thang', 'nam')
    def _compute_tien_thuong(self):
        for rec in self:
            tong_thuong = 0.0

            if not rec.nhan_vien_id:
                rec.tien_thuong = 0
                continue

            domain = [
                ('trang_thai', '=', 'da_duyet'),
                ('cong_vao_luong', '=', True),
                ('thang', '=', rec.thang),
                ('nam', '=', rec.nam),
                '|',
                '&',
                    ('kieu_thuong', '=', 'mot_nguoi'),
                    ('nhan_vien_id', '=', rec.nhan_vien_id.id),
                ('kieu_thuong', '=', 'tat_ca')
            ]

            thuong_ids = self.env['tien_thuong'].search(domain)

            for thuong in thuong_ids:
                tong_thuong += thuong.so_tien

            rec.tien_thuong = tong_thuong


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

    def _tinh_thue_luy_tien(self, thu_nhap_tinh_thue, thue):
        tong_thue = 0
        for bac in thue.bac_ids.sorted('bac'):
            muc_duoi = bac.muc_thu_nhap_tu
            muc_tren = bac.muc_thu_nhap_den or thu_nhap_tinh_thue

            if thu_nhap_tinh_thue <= muc_duoi:
                break

            phan_chiu_thue = min(thu_nhap_tinh_thue, muc_tren) - muc_duoi
            tong_thue += phan_chiu_thue * bac.thue_suat / 100

        return tong_thue



    @api.depends(
        'luong_co_ban',
        'phu_cap',
        'so_ngay_di_lam',
        'tong_phut_di_muon',
        'tong_phut_ve_som',
        'tong_gio_tang_ca',
        'tien_thuong',
        'thue_id'
    )
    def _compute_luong_final(self):
        NGAY_CONG_CHUAN = 26
        GIO_LAM_NGAY = 8.0

        for rec in self:
            # 1. Tổng thu nhập
            tong_thu_nhap = (
                (rec.luong_co_ban or 0) +
                (rec.phu_cap or 0)
            )

            luong_1_ngay = tong_thu_nhap / NGAY_CONG_CHUAN
            luong_1_gio = luong_1_ngay / GIO_LAM_NGAY
            luong_1_phut = luong_1_gio / 60

            rec.luong_ngay = luong_1_ngay

            # 2. Tăng ca
            rec.tien_tang_ca = rec.tong_gio_tang_ca * luong_1_gio * 2

            # 3. Lương theo công
            luong_theo_cong = luong_1_ngay * rec.so_ngay_di_lam
            
            # 3.5 . Bảo hiểm
            rec.tien_bh_ca_nhan = (
                luong_theo_cong *
                (rec.nhan_vien_id.bao_hiem_ca_nhan or 0) / 100
            )

            rec.tien_bh_xa_hoi = (
                luong_theo_cong *
                (rec.nhan_vien_id.bao_hiem_xa_hoi or 0) / 100
            )

            # 4. Phạt
            rec.tien_phat = (
                (rec.tong_phut_di_muon + rec.tong_phut_ve_som)
                * luong_1_phut
            )

            # 5. Thu nhập trước thuế
            thu_nhap_truoc_thue = (
                luong_theo_cong +
                rec.tien_tang_ca +
                rec.tien_thuong +
                (rec.phu_cap or 0) -
                rec.tien_phat -
                rec.tien_bh_ca_nhan -
                rec.tien_bh_xa_hoi
            )



            # 6. Tính thuế
            rec.tien_thue_tncn = 0
            so_nguoi_pt = rec.nhan_vien_id.so_nguoi_phu_thuoc or 0
            if rec.thue_id:
                tong_giam_tru = (
                    rec.thue_id.giam_tru_ban_than +
                    so_nguoi_pt * rec.thue_id.giam_tru_nguoi_phu_thuoc
                )
                thu_nhap_tinh_thue = max(
                    0,
                    thu_nhap_truoc_thue - tong_giam_tru
                )

                if rec.thue_id.loai_thue == 'luy_tien':
                    rec.tien_thue_tncn = self._tinh_thue_luy_tien(
                        thu_nhap_tinh_thue,
                        rec.thue_id
                    )

                elif rec.thue_id.loai_thue == 'co_dinh':
                    rec.tien_thue_tncn = (
                        thu_nhap_tinh_thue *
                        rec.thue_id.bac_ids[:1].thue_suat / 100
                    )
            rec.tien_thue_tncn = round(rec.tien_thue_tncn, 0)


            # 7. Thực lĩnh
            rec.tong_luong = max(
                0,
                thu_nhap_truoc_thue - rec.tien_thue_tncn
            )

    
    @api.model
    def cron_tao_bang_luong_thang(self):
        today = fields.Date.today()

        # ✅ Chỉ chạy vào ngày 1
        # if today.day != 1:
        #     return

        # ✅ Lấy tháng trước
        thang_truoc = today - relativedelta(months=1)
        thang = thang_truoc.month
        nam = thang_truoc.year

        nhan_vien_ids = self.env['nhan_vien'].search([
            ('hop_dong_hien_tai_id', '!=', False),
            ('hop_dong_hien_tai_id.trang_thai', '=', 'dang_hieu_luc')
        ])

        for nv in nhan_vien_ids:
            # ❌ Chống tạo trùng
            da_ton_tai = self.search_count([
                ('nhan_vien_id', '=', nv.id),
                ('thang', '=', thang),
                ('nam', '=', nam)
            ])
            if da_ton_tai:
                continue

            # 👉 Tạo bản nháp để compute số ngày công
            bang_luong = self.create({
                'nhan_vien_id': nv.id,
                'thang': thang,
                'nam': nam
            })

            # ❌ Nếu không có ngày công thì bỏ
            if bang_luong.so_ngay_di_lam <= 0:
                bang_luong.unlink()

