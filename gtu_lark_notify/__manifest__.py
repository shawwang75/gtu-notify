# -*- coding: utf-8 -*-
{
    'name': "GTU Lark Business Notifications",
    'summary': "Send business notifications to Lark/Feishu (飞书) automatically",
    'description': """
        Automatically push Odoo business events to Lark (Feishu/飞书).

        Automatically push Odoo business events to Lark (飞书).

        === Key Features ===

        【Business Event Notifications】
        - Contacts: Create, update, assign
        - CRM: Lead create, assign, stage change, amount change, close
        - Projects: Project create, task create, assign, status change, deadline change, complete
        - Timesheets: Create, update, delete

        【Notification Control】
        - Three-level notification switches (global/module/event)
        - User-level notification preferences
        - Message cards with direct links to Odoo

        【Technical Advantages】
        - Fully standalone, zero dependencies (no other Lark modules required)
        - Lark App configuration management
        - Employee Lark account binding
        - Automatic token refresh mechanism
        - Fail-safe design, won't break business operations
        - Fully based on Odoo standard inheritance, zero source code modification

        === Version 2.3.0 Features ===
        ✅ Timesheet notifications (create/update/delete)
        ✅ Rich card messages with project context
        ✅ Improved message formatting

        === Supported Events ===
        - CRM Lead: Created, assigned, stage changed, closed
        - Project Task: Assigned, status changed, deadline updated, completed
        - Timesheet: Created, modified, deleted

        === Easy Configuration ===
        1. Configure Lark App ID and Secret
        2. Bind employee Lark accounts
        3. Enable notifications
        4. Done!
    """,
    'author': "上海逸广信息科技有限公司 (Shanghai Yiguang Information Technology Co., Ltd.)",
    'website': "https://www.gtucloud.com",
    'category': 'Productivity',
    'version': '19.0.2.4.0',
    'license': 'OPL-1',
    'price': 59.00,
    'currency': 'EUR',

    # Dependencies
    'depends': [
        'hr',           # Employee management
        'crm',          # CRM leads
        'project',      # Project management
        'mail',         # Mail thread
    ],

    # Always loaded
    'data': [
        # Security
        'security/groups.xml',
        'security/ir.model.access.csv',

        # Views
        'views/menu_views.xml',
        'views/lark_config_views.xml',
        'views/hr_employee_views.xml',
        'views/res_company.xml',

        # Data
        'data/lark_notification_config.xml',
    ],

    # Application
    'application': True,
    'installable': True,
    'auto_install': False,

    # Images for Odoo Apps store
    'images': [
        'static/description/banner.png',
    ],

    # Support
    'support': 'support@gtucloud.com',
}
