# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, time
from pytz import timezone, UTC


class NhanVienInherit(models.Model):
    _inherit = 'nhan_vien'

    cham_cong_ids = fields.One2many(
        'cham_cong', 'nhan_vien_id', string='Lịch sử chấm công'
    )


class BangChamCong(models.Model):
    _name = 'cham_cong'
    _description = 'Bảng chấm công'
    _order = 'ngay_cham_cong desc'
    _rec_name = 'name'

    # =========================
    # THÔNG TIN CƠ BẢN
    # =========================
    name = fields.Char(compute='_compute_name', store=True)

    nhan_vien_id = fields.Many2one(
        'nhan_vien', string='Nhân viên', required=True
    )

    ngay_cham_cong = fields.Date(
        string='Ngày chấm công',
        required=True,
        default=fields.Date.context_today
    )

    # =========================
    # ĐĂNG KÝ CA & ĐƠN TỪ
    # =========================
    dang_ky_ca_lam_id = fields.Many2one(
        'dang_ky_ca_lam_theo_ngay',
        compute='_compute_dang_ky_ca_lam',
        store=True
    )

    ca_lam = fields.Selection(
        related='dang_ky_ca_lam_id.ca_lam',
        store=True
    )

    don_tu_id = fields.Many2one(
        'don_tu',
        compute='_compute_don_tu',
        store=True
    )

    loai_don = fields.Selection(
        related='don_tu_id.loai_don',
        store=True
    )

    thoi_gian_xin = fields.Float(
        related='don_tu_id.thoi_gian_xin',
        store=True
    )

    # =========================
    # GIỜ CA
    # =========================
    gio_vao_ca = fields.Datetime(
        compute='_compute_gio_ca',
        store=True
    )

    gio_ra_ca = fields.Datetime(
        compute='_compute_gio_ca',
        store=True
    )

    # =========================
    # GIỜ THỰC TẾ
    # =========================
    gio_vao = fields.Datetime(string='Giờ vào')
    gio_ra = fields.Datetime(string='Giờ ra')

    # =========================
    # ĐI MUỘN / VỀ SỚM
    # =========================
    phut_di_muon = fields.Float(
        compute='_compute_phut_di_muon',
        store=True
    )

    phut_ve_som = fields.Float(
        compute='_compute_phut_ve_som',
        store=True
    )

    # =========================
    # TRẠNG THÁI
    # =========================
    trang_thai = fields.Selection([
        ('di_lam', 'Đi làm'),
        ('di_muon', 'Đi muộn'),
        ('ve_som', 'Về sớm'),
        ('di_muon_ve_som', 'Đi muộn & về sớm'),
        ('vang_mat', 'Vắng mặt'),
    ], compute='_compute_trang_thai', store=True)

    # ==========================================================
    # COMPUTE METHODS
    # ==========================================================

    @api.depends('nhan_vien_id', 'ngay_cham_cong')
    def _compute_name(self):
        for r in self:
            r.name = (
                f"{r.nhan_vien_id.ho_va_ten} - {r.ngay_cham_cong}"
                if r.nhan_vien_id and r.ngay_cham_cong
                else "Chấm công"
            )

    @api.depends('nhan_vien_id', 'ngay_cham_cong')
    def _compute_dang_ky_ca_lam(self):
        for r in self:
            r.dang_ky_ca_lam_id = self.env['dang_ky_ca_lam_theo_ngay'].search([
                ('nhan_vien_id', '=', r.nhan_vien_id.id),
                ('ngay_lam', '=', r.ngay_cham_cong)
            ], limit=1)

    @api.depends('nhan_vien_id', 'ngay_cham_cong')
    def _compute_don_tu(self):
        for r in self:
            r.don_tu_id = self.env['don_tu'].search([
                ('nhan_vien_id', '=', r.nhan_vien_id.id),
                ('ngay_ap_dung', '=', r.ngay_cham_cong),
                ('trang_thai_duyet', '=', 'da_duyet')
            ], limit=1)

    @api.depends('ca_lam', 'ngay_cham_cong')
    def _compute_gio_ca(self):
        for record in self:
            if not record.ngay_cham_cong or not record.ca_lam:
                record.gio_vao_ca = False
                record.gio_ra_ca = False
                continue

            user_tz = self.env.user.tz or 'UTC'
            tz = timezone(user_tz)

            if record.ca_lam == "Sáng":
                gio_vao = time(7, 30)  # 7:30 AM
                gio_ra = time(11, 30)  # 11:30 AM
            elif record.ca_lam == "Chiều":
                gio_vao = time(13, 30)  # 1:30 PM
                gio_ra = time(17, 30)  # 5:30 PM
            elif record.ca_lam == "Cả ngày":
                gio_vao = time(7, 30)  # 7:30 AM
                gio_ra = time(17, 30)  # 5:30 PM
            else:
                record.gio_vao_ca = False
                record.gio_ra_ca = False
                continue

            # Convert to datetime in user's timezone
            thoi_gian_vao = datetime.combine(record.ngay_cham_cong, gio_vao)
            thoi_gian_ra = datetime.combine(record.ngay_cham_cong, gio_ra)
            
            # Store in UTC
            record.gio_vao_ca = tz.localize(thoi_gian_vao).astimezone(UTC).replace(tzinfo=None)
            record.gio_ra_ca = tz.localize(thoi_gian_ra).astimezone(UTC).replace(tzinfo=None)

    @api.depends('gio_vao', 'gio_vao_ca', 'loai_don', 'thoi_gian_xin')
    def _compute_phut_di_muon(self):
        for r in self:
            if not r.gio_vao or not r.gio_vao_ca:
                r.phut_di_muon = 0
                continue

            goc = max(0, (r.gio_vao - r.gio_vao_ca).total_seconds() / 60)

            if r.loai_don == 'di_muon':
                r.phut_di_muon = max(0, goc - r.thoi_gian_xin)
            else:
                r.phut_di_muon = goc

    @api.depends('gio_ra', 'gio_ra_ca', 'loai_don', 'thoi_gian_xin')
    def _compute_phut_ve_som(self):
        for r in self:
            if not r.gio_ra or not r.gio_ra_ca:
                r.phut_ve_som = 0
                continue

            goc = max(0, (r.gio_ra_ca - r.gio_ra).total_seconds() / 60)

            if r.loai_don == 've_som':
                r.phut_ve_som = max(0, goc - r.thoi_gian_xin)
            else:
                r.phut_ve_som = goc

    @api.depends('gio_vao', 'gio_ra', 'phut_di_muon', 'phut_ve_som')
    def _compute_trang_thai(self):
        for r in self:
            if not r.gio_vao and not r.gio_ra:
                r.trang_thai = 'vang_mat'
            elif r.phut_di_muon > 0 and r.phut_ve_som > 0:
                r.trang_thai = 'di_muon_ve_som'
            elif r.phut_di_muon > 0:
                r.trang_thai = 'di_muon'
            elif r.phut_ve_som > 0:
                r.trang_thai = 've_som'
            else:
                r.trang_thai = 'di_lam'
