# -*- coding: utf-8 -*-

import logging
from odoo import models, api, fields, _

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    """
    扩展联系人模型，添加飞书通知功能
    """
    _inherit = 'res.partner'

    @api.model_create_multi
    def create(self, vals_list):
        """
        新建联系人时发送通知
        """
        partners = super(ResPartner, self).create(vals_list)
        
        for partner in partners:
            try:
                # 跳过非公司联系人的子联系人（避免过多通知）
                if partner.parent_id and not partner.is_company:
                    continue
                
                # 通知对象：负责人（销售员）+ 创建者
                notify_users = self.env['res.users']
                if partner.user_id:
                    notify_users |= partner.user_id
                if partner.create_uid and partner.create_uid != partner.user_id:
                    notify_users |= partner.create_uid
                
                if notify_users:
                    self.env['lark.notifier'].notify_business_event(
                        record=partner,
                        event_type='create',
                        notify_users=notify_users
                    )
            except Exception as e:
                _logger.error(f"Failed to send notification for new partner {partner.id}: {e}")
        
        return partners

    def write(self, vals):
        """
        联系人信息变更时发送通知
        """
        # 记录变更前状态
        old_users = {}
        
        if 'user_id' in vals:
            old_users = {p.id: p.user_id for p in self}
        
        result = super(ResPartner, self).write(vals)
        
        try:
            # 1. 负责人变更（分配）
            if 'user_id' in vals:
                for partner in self:
                    # 跳过非公司联系人的子联系人
                    if partner.parent_id and not partner.is_company:
                        continue
                    
                    old_user = old_users.get(partner.id)
                    new_user = partner.user_id
                    
                    if old_user != new_user and new_user:
                        self.env['lark.notifier'].notify_business_event(
                            record=partner,
                            event_type='assign',
                            notify_users=new_user,
                            changes={
                                'user_id': f"{old_user.name if old_user else '未分配'} → {new_user.name}"
                            }
                        )
            
            # 2. 关键信息变更
            key_fields = ['name', 'phone', 'mobile', 'email', 'street', 'city', 'category_id']
            if any(field in vals for field in key_fields):
                for partner in self:
                    # 跳过非公司联系人的子联系人
                    if partner.parent_id and not partner.is_company:
                        continue
                    
                    changes = {}
                    if 'name' in vals:
                        changes['name'] = vals['name']
                    if 'phone' in vals:
                        changes['phone'] = vals['phone']
                    if 'mobile' in vals:
                        changes['mobile'] = vals['mobile']
                    if 'email' in vals:
                        changes['email'] = vals['email']
                    if 'street' in vals or 'city' in vals:
                        changes['address'] = _('地址已更新')
                    if 'category_id' in vals:
                        changes['category'] = _('标签已更新')
                    
                    if changes and partner.user_id:
                        self.env['lark.notifier'].notify_business_event(
                            record=partner,
                            event_type='write',
                            notify_users=partner.user_id,
                            changes=changes
                        )
        
        except Exception as e:
            _logger.error(f"Error sending notification for partner update: {e}")
        
        return result