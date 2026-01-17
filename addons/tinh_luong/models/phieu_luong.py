# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class PhieuLuong(models.Model):
    _name = 'phieu_luong'
    _description = 'Phiếu lương'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'nam desc, thang desc'

    # ======================
    # THÔNG TIN CHUNG
    # ======================
    name = fields.Char(
        string='Số phiếu lương',
        compute='_compute_name',
        store=True
    )
    so_ngay_di_lam = fields.Float(
        string='Số ngày đi làm',
        related='bang_luong_id.so_ngay_di_lam',
        store=True,
        readonly=True
    )
    luong_co_ban = fields.Float(
        string='Lương cơ bản',
        related='bang_luong_id.luong_co_ban',
        store=True,
        readonly=True
    )
    tien_phu_cap = fields.Float(
        string='Tiền phụ cấp',
        related='bang_luong_id.phu_cap',
        store=True,
        readonly=True
    )
    bao_hiem_ca_nhan = fields.Float(
        string='Tiền bảo hiểm',
        related='bang_luong_id.tien_bh_ca_nhan',
        store=True,
        readonly=True
    )
    bao_hiem_xa_hoi = fields.Float(
        string='Tiền bảo hiểm xã hội',
        related='bang_luong_id.tien_bh_xa_hoi',
        store=True,
        readonly=True
    )
    tien_thuong = fields.Float(
        string='Tiền thưởng',
        related='bang_luong_id.tien_thuong',
        store=True,
        readonly=True
    )


    nhan_vien_id = fields.Many2one(
        'nhan_vien',
        string='Nhân viên',
        required=True,
        tracking=True
    )

    thang = fields.Integer(
        'Tháng',
        required=True
    )
    nam = fields.Integer(
        'Năm',
        required=True
    )

    bang_luong_id = fields.Many2one(
        'bang_luong',
        string='Nguồn bảng lương',
        required=True,
        ondelete='restrict'
    )

    # ======================
    # CHI TIẾT TIỀN
    # ======================
    luong_theo_cong = fields.Float(
        related='bang_luong_id.tong_luong',
        store=True,
        readonly=True
    )


    tien_tang_ca = fields.Float(
        related='bang_luong_id.tien_tang_ca',
        store=True,
        readonly=True
    )

    tien_phat = fields.Float(
        related='bang_luong_id.tien_phat',
        store=True,
        readonly=True
    )

    tien_thue_tncn = fields.Float(
        related='bang_luong_id.tien_thue_tncn',
        store=True,
        readonly=True
    )


    tong_thuc_linh = fields.Float(
        related='bang_luong_id.tong_luong',
        store=True,
        readonly=True
    )


    # ======================
    # TRẠNG THÁI
    # ======================
    trang_thai = fields.Selection([
        ('nhap', 'Nháp'),
        ('xac_nhan', 'Đã xác nhận'),
        ('da_tra', 'Đã trả lương'),
    ], default='nhap', tracking=True)

    ngay_tra = fields.Date('Ngày trả lương')
    da_gui_email = fields.Boolean(
        string="Đã gửi email",
        default=False,
        tracking=True
    )


    ghi_chu = fields.Text('Ghi chú')

    # ======================
    # CONSTRAINT
    # ======================
    _sql_constraints = [
        (
            'unique_phieu_luong',
            'unique(nhan_vien_id, thang, nam)',
            'Nhân viên này đã có phiếu lương cho kỳ này!'
        )
    ]

    # ======================
    # COMPUTE
    # ======================
    @api.depends('nhan_vien_id', 'thang', 'nam')
    def _compute_name(self):
        for rec in self:
            rec.name = f"PL-{rec.thang:02d}/{rec.nam}-{rec.nhan_vien_id.ma_dinh_danh or ''}"

    @api.constrains('nhan_vien_id', 'bang_luong_id')
    def _check_nhan_vien_trung(self):
        for rec in self:
            if rec.bang_luong_id and rec.nhan_vien_id != rec.bang_luong_id.nhan_vien_id:
                raise ValidationError(
                    "Nhân viên trên Phiếu lương phải trùng với Nhân viên của Bảng lương!"
                )
            
    @api.onchange('bang_luong_id')
    def _onchange_bang_luong(self):
        if self.bang_luong_id:
            self.nhan_vien_id = self.bang_luong_id.nhan_vien_id
            self.thang = self.bang_luong_id.thang
            self.nam = self.bang_luong_id.nam



    # ======================
    # ACTIONS
    # ======================
    def action_xac_nhan(self):
        for rec in self:
            if rec.trang_thai != 'nhap':
                continue
            rec.trang_thai = 'xac_nhan'

    def _email_da_gui(self):
        self.ensure_one()
        Mail = self.env['mail.mail']
        mail = Mail.search([
            ('model', '=', 'phieu_luong'),
            ('res_id', '=', self.id),
            ('state', '=', 'sent'),
        ], limit=1)
        return bool(mail)


    def action_da_tra(self):
        for rec in self:
            if rec.trang_thai != 'xac_nhan':
                raise ValidationError("Phiếu lương phải được xác nhận trước khi trả!")

            if rec._email_da_gui():
                raise ValidationError("Email phiếu lương đã được gửi thành công trước đó!")

            rec.trang_thai = 'da_tra'
            rec.ngay_tra = fields.Date.today()
            rec._gui_email_phieu_luong()


    def _gui_email_phieu_luong(self):
        # Lấy template bằng XML ID
        template = self.env.ref('tinh_luong.email_template_phieu_luong', raise_if_not_found=False)
        if not template:
            return False
            
        for rec in self:
            if not rec.nhan_vien_id.email:
                # Thay vì raise lỗi làm gián đoạn cả quá trình, hãy ghi chú lại
                rec.message_post(body="Không thể gửi email: Nhân viên không có địa chỉ email.")
                continue
            
            # Gửi email: 
            # Dùng force_send=True để gửi ngay lập tức thay vì chờ Queue Job
            try:
                template.send_mail(rec.id, force_send=True, raise_exception=True)
                rec.da_gui_email = True
                rec.message_post(body="Đã gửi email phiếu lương thành công.")
            except Exception as e:
                rec.message_post(body=f"Gửi email thất bại: {str(e)}")
        return True



    

