# -*- coding: utf-8 -*-
"""
公司模型扩展
添加飞书应用配置字段和测试连接功能
"""

import logging
from odoo import models, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    """
    扩展公司模型
    添加飞书应用配置
    """
    _inherit = 'res.company'
    
    # 飞书应用配置
    lark_app_id = fields.Char(
        string='飞书App ID',
        help='飞书应用的App ID'
    )
    
    lark_app_secret = fields.Char(
        string='飞书App Secret',
        help='飞书应用的App Secret'
    )
    
    # 通知设置
    lark_notify_enabled = fields.Boolean(
        string='启用飞书通知',
        default=False,
        help='是否启用飞书消息推送'
    )
    
    lark_notify_odoo_url = fields.Char(
        string='Odoo访问地址',
        help='Odoo的公网访问地址，用于生成跳转链接'
    )
    
    def action_test_lark_connection(self):
        """
        测试飞书连接
        验证App ID和App Secret是否正确
        """
        self.ensure_one()
        
        # 检查必填字段
        if not self.lark_app_id or not self.lark_app_secret:
            raise UserError(_('请先填写飞书App ID和App Secret'))
        
        try:
            # 导入飞书SDK
            import lark_oapi as lark
            
            # 创建飞书客户端
            client = lark.Client.builder() \
                .app_id(self.lark_app_id) \
                .app_secret(self.lark_app_secret) \
                .log_level(lark.LogLevel.ERROR) \
                .build()
            
            # 测试获取tenant_access_token
            # 这是验证App ID和Secret的最简单方法
            from lark_oapi.api.auth.v3 import InternalTenantAccessTokenRequest
            
            request = InternalTenantAccessTokenRequest.builder() \
                .request_body(
                    InternalTenantAccessTokenRequest.builder() \
                    .app_id(self.lark_app_id) \
                    .app_secret(self.lark_app_secret) \
                    .build()
                ) \
                .build()
            
            response = client.auth.v3.tenant_access_token.internal(request)
            
            if response.success():
                # 连接成功
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('测试成功'),
                        'message': _('飞书连接成功！App ID和App Secret验证通过。'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                # 连接失败
                error_msg = response.msg if hasattr(response, 'msg') else '未知错误'
                raise UserError(_('测试失败: %s') % error_msg)
                
        except ImportError as e:
            _logger.error(f"Failed to import lark_oapi: {e}")
            raise UserError(_('请确保已安装飞书SDK: pip install lark-oapi'))
        except Exception as e:
            _logger.error(f"Lark connection test failed: {e}", exc_info=True)
            error_msg = str(e)
            
            # 友好的错误提示
            if 'invalid app_id or app_secret' in error_msg.lower():
                error_msg = _('App ID或App Secret不正确')
            elif 'network' in error_msg.lower() or 'timeout' in error_msg.lower():
                error_msg = _('网络连接失败，请检查服务器网络')
            
            raise UserError(_('测试失败: %s') % error_msg)
