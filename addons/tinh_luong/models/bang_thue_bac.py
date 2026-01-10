from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ThueThuNhapBac(models.Model):
    _name = 'thue_thu_nhap_bac'
    _description = 'Chi tiet bac thue'
    _order = 'bac asc'

    thue_id = fields.Many2one('thue_thu_nhap', ondelete='cascade')
    currency_id = fields.Many2one(related='thue_id.currency_id')
    
    bac = fields.Integer(string='Bậc', required=True)
    muc_thu_nhap_tu = fields.Monetary(string='Thu nhập từ', currency_field='currency_id')
    muc_thu_nhap_den = fields.Monetary(string='Thu nhập đến', currency_field='currency_id', help='Để trống nếu là bậc cuối cùng')
    thue_suat = fields.Float(string='Thuế suất (%)')

    @api.constrains('muc_thu_nhap_tu', 'muc_thu_nhap_den')
    def _check_muc_thu_nhap(self):
        for rec in self:
            if rec.muc_thu_nhap_den and rec.muc_thu_nhap_tu >= rec.muc_thu_nhap_den:
                raise ValidationError("Lỗi: Mức thu nhập 'Đến' phải lớn hơn mức 'Từ'!")
            
    @api.constrains('thue_id', 'muc_thu_nhap_tu', 'muc_thu_nhap_den')
    def _check_overlap(self):
        for rec in self:
            if not rec.thue_id:
                continue

            domain = [
                ('thue_id', '=', rec.thue_id.id),
                ('id', '!=', rec.id),
            ]
            for other in self.search(domain):
                if (
                    (not rec.muc_thu_nhap_den or other.muc_thu_nhap_tu < rec.muc_thu_nhap_den)
                    and
                    (not other.muc_thu_nhap_den or rec.muc_thu_nhap_tu < other.muc_thu_nhap_den)
                ):
                    raise ValidationError(
                        f"Bậc thuế {rec.bac} bị chồng với bậc {other.bac}"
                    )
