# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, time, timedelta
from pytz import timezone, UTC

class BangChamCong(models.Model):
    _name = 'cham_cong'
    _description = "Bảng chấm công chi tiết"
    _rec_name = 'name'
    _order = 'ngay_cham_cong desc'

    name = fields.Char(string="Mã chấm công", compute="_compute_name", store=True)
    nhan_vien_id = fields.Many2one('nhan_vien', string="Nhân viên", required=True)
    ngay_cham_cong = fields.Date("Ngày chấm công", required=True, default=fields.Date.context_today)
    
    # --- LIÊN KẾT ---
    dang_ky_ca_lam_id = fields.Many2one('dang_ky_ca_lam_theo_ngay', string="Đăng ký ca làm")
    ca_lam = fields.Selection(related='dang_ky_ca_lam_id.ca_lam', store=True, string="Ca làm")
    don_tu_id = fields.Many2one('don_tu', string="Đơn từ giải trình")
    
    # --- GIỜ GIẤC ---
    gio_vao_ca = fields.Datetime("Giờ vào ca (Chuẩn)", compute='_compute_gio_ca', store=True)
    gio_ra_ca = fields.Datetime("Giờ ra ca (Chuẩn)", compute='_compute_gio_ca', store=True)
    
    gio_vao = fields.Datetime("Giờ vào thực tế")
    gio_ra = fields.Datetime("Giờ ra thực tế")

    # --- TÍNH TOÁN VI PHẠM ---
    phut_di_muon = fields.Float("Phút đi muộn", compute="_compute_vi_pham", store=True)
    phut_ve_som = fields.Float("Phút về sớm", compute="_compute_vi_pham", store=True)
    
    trang_thai = fields.Selection([
        ('di_lam', 'Đúng giờ'),
        ('di_muon', 'Đi muộn'),
        ('ve_som', 'Về sớm'),
        ('di_muon_ve_som', 'Đi muộn & Về sớm'),
        ('vang_mat', 'Vắng mặt'),
        ('vang_mat_co_phep', 'Vắng mặt có phép'),
    ], string="Trạng thái", compute="_compute_trang_thai", store=True)

    _sql_constraints = [
        ('unique_attendance_day', 'unique(nhan_vien_id, ngay_cham_cong)', 'Nhân viên này đã có bảng chấm công cho ngày này rồi!')
    ]

    @api.depends('nhan_vien_id', 'ngay_cham_cong')
    def _compute_name(self):
        for rec in self:
            if rec.nhan_vien_id and rec.ngay_cham_cong:
                rec.name = f"{rec.nhan_vien_id.ma_dinh_danh}_{rec.ngay_cham_cong}"
            else:
                rec.name = "Draft"

    @api.depends('ca_lam', 'ngay_cham_cong')
    def _compute_gio_ca(self):
        """ Tính giờ chuẩn theo múi giờ người dùng nhưng lưu vào DB dưới dạng UTC """
        for rec in self:
            if not rec.ngay_cham_cong or not rec.ca_lam:
                rec.gio_vao_ca = rec.gio_ra_ca = False
                continue

            # Config giờ làm việc (Nên đưa vào setting hệ thống)
            ca_map = {
                "Sáng": (time(7, 30), time(11, 30)),
                "Chiều": (time(13, 30), time(17, 30)),
                "Cả ngày": (time(7, 30), time(17, 30))
            }
            times = ca_map.get(rec.ca_lam)
            if not times:
                rec.gio_vao_ca = rec.gio_ra_ca = False
                continue

            # Xử lý múi giờ
            user_tz = timezone(self.env.user.tz or 'Asia/Ho_Chi_Minh')
            
            # Tạo datetime local
            dt_vao = datetime.combine(rec.ngay_cham_cong, times[0])
            dt_ra = datetime.combine(rec.ngay_cham_cong, times[1])
            
            # Localize và chuyển về UTC
            rec.gio_vao_ca = user_tz.localize(dt_vao).astimezone(UTC).replace(tzinfo=None)
            rec.gio_ra_ca = user_tz.localize(dt_ra).astimezone(UTC).replace(tzinfo=None)

    @api.depends('gio_vao', 'gio_ra', 'gio_vao_ca', 'gio_ra_ca', 'don_tu_id.trang_thai_duyet')
    def _compute_vi_pham(self):
        for rec in self:
            muon = 0.0
            som = 0.0
            
            # 1. Tính toán gốc
            if rec.gio_vao and rec.gio_vao_ca and rec.gio_vao > rec.gio_vao_ca:
                delta = rec.gio_vao - rec.gio_vao_ca
                muon = delta.total_seconds() / 60
            
            if rec.gio_ra and rec.gio_ra_ca and rec.gio_ra < rec.gio_ra_ca:
                delta = rec.gio_ra_ca - rec.gio_ra
                som = delta.total_seconds() / 60

            # 2. Trừ đơn từ (nếu đã duyệt)
            if rec.don_tu_id and rec.don_tu_id.trang_thai_duyet == 'da_duyet':
                tg_xin = rec.don_tu_id.thoi_gian_xin or 0
                loai = rec.don_tu_id.loai_don
                if loai == 'di_muon':
                    muon = max(0, muon - tg_xin)
                elif loai == 've_som':
                    som = max(0, som - tg_xin)

            rec.phut_di_muon = muon
            rec.phut_ve_som = som

    @api.depends('gio_vao', 'gio_ra', 'phut_di_muon', 'phut_ve_som')
    def _compute_trang_thai(self):
        for rec in self:
            if not rec.gio_vao and not rec.gio_ra:
                rec.trang_thai = 'vang_mat'
            elif rec.phut_di_muon > 0 and rec.phut_ve_som > 0:
                rec.trang_thai = 'di_muon_ve_som'
            elif rec.phut_di_muon > 0:
                rec.trang_thai = 'di_muon'
            elif rec.phut_ve_som > 0:
                rec.trang_thai = 've_som'
            else:
                rec.trang_thai = 'di_lam'