# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date
from dateutil.relativedelta import relativedelta

class BangLuong(models.Model):
    _name = 'bang_luong'
    _description = 'Bảng lương chi tiết'
    _rec_name = 'name'

    name = fields.Char(string="Tên bảng lương", compute="_compute_name", store=True)
    nhan_vien_id = fields.Many2one('nhan_vien', string="Nhân viên", required=True)
    thang = fields.Integer("Tháng", required=True, default=lambda self: date.today().month)
    nam = fields.Integer("Năm", required=True, default=lambda self: date.today().year)

    luong_co_ban = fields.Float(related='nhan_vien_id.luong_co_ban', store=True, string="Lương cơ bản")

    # --- INPUT TỪ CHẤM CÔNG ---
    so_ngay_di_lam = fields.Float("Số ngày công", compute="_compute_data_cham_cong", store=True)
    so_ngay_vang = fields.Float("Số ngày vắng", compute="_compute_data_cham_cong", store=True)
    tong_phut_di_muon = fields.Float("Tổng phút muộn", compute="_compute_data_cham_cong", store=True)
    tong_phut_ve_som = fields.Float("Tổng phút sớm", compute="_compute_data_cham_cong", store=True)

    # --- OUTPUT TÍNH LƯƠNG ---
    luong_ngay_chuan = fields.Float("Lương 1 ngày (Chuẩn)", compute="_compute_luong_final", store=True)
    tien_phat = fields.Float("Tiền phạt", compute="_compute_luong_final", store=True)
    tong_luong_nhan = fields.Float("Thực lĩnh", compute="_compute_luong_final", store=True)

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
            # Reset
            rec.so_ngay_di_lam = 0
            rec.so_ngay_vang = 0
            rec.tong_phut_di_muon = 0
            rec.tong_phut_ve_som = 0

            if not rec.nhan_vien_id or not rec.thang or not rec.nam:
                continue

            # Xử lý ngày đầu tháng và cuối tháng an toàn
            start_date = date(rec.nam, rec.thang, 1)
            end_date = start_date + relativedelta(months=1, days=-1) # Ngày cuối tháng

            # Tìm các record chấm công trong khoảng thời gian
            cham_congs = self.env['cham_cong'].search([
                ('nhan_vien_id', '=', rec.nhan_vien_id.id),
                ('ngay_cham_cong', '>=', start_date),
                ('ngay_cham_cong', '<=', end_date)
            ])

            for cc in cham_congs:
                if cc.trang_thai in ['vang_mat', 'vang_mat_co_phep']:
                    rec.so_ngay_vang += 1
                else:
                    rec.so_ngay_di_lam += 1 # Có thể tính 0.5 công nếu làm nửa ngày tùy logic

                rec.tong_phut_di_muon += cc.phut_di_muon
                rec.tong_phut_ve_som += cc.phut_ve_som

    @api.depends('luong_co_ban', 'so_ngay_di_lam', 'tong_phut_di_muon', 'tong_phut_ve_som')
    def _compute_luong_final(self):
        NGAY_CONG_CHUAN = 26.0
        GIO_LAM_NGAY = 8.0

        for rec in self:
            if not rec.luong_co_ban:
                rec.luong_ngay_chuan = 0
                rec.tien_phat = 0
                rec.tong_luong_nhan = 0
                continue

            # 1. Tính lương theo ngày
            luong_1_ngay = rec.luong_co_ban / NGAY_CONG_CHUAN
            luong_1_phut = luong_1_ngay / (GIO_LAM_NGAY * 60)
            
            rec.luong_ngay_chuan = luong_1_ngay

            # 2. Tính lương thực tế dựa trên ngày công
            luong_theo_cong = luong_1_ngay * rec.so_ngay_di_lam

            # 3. Tính phạt (Trừ trực tiếp tiền theo phút)
            tien_phat_muon = rec.tong_phut_di_muon * luong_1_phut
            tien_phat_som = rec.tong_phut_ve_som * luong_1_phut
            
            rec.tien_phat = tien_phat_muon + tien_phat_som

            # 4. Thực lĩnh
            rec.tong_luong_nhan = max(0, luong_theo_cong - rec.tien_phat)