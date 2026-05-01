# -*- coding: utf-8 -*-
{
    'name': "GTU Notify",
    'summary': "Send business notifications to Feishu (飞书) automatically",
    'description': """
        Automatically push Odoo business events to Feishu (飞书).

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
        - Feishu App configuration management
        - Employee Feishu account binding
        - Automatic token refresh mechanism
        - Fail-safe design, won't break business operations
        - Fully based on Odoo standard inheritance, zero source code modification

        === Version 2.4.1 Bug Fixes ===
        🐛 Fixed: Employee binding page error (lark_open_id field not loaded)
        ✅ Fixed: Missing model imports in __init__.py
        ✅ Fixed: Timesheet notifications now work in all languages

        === Version 2.3.0 Features ===
        ✅ Timesheet notifications (create/update/delete)
        ✅ Rich card messages with project context
        ✅ Improved message formatting

        === Supported Events ===
        - CRM Lead: Created, assigned, stage changed, closed
        - Project Task: Assigned, status changed, deadline updated, completed
        - Timesheet: Created, modified, deleted

        === Easy Configuration ===
        1. Configure Feishu App ID and Secret
        2. Bind employee Feishu accounts
        3. Enable notifications
        4. Done!
    """,
    'author': "上海逸广信息科技有限公司 (Shanghai Yiguang Information Technology Co., Ltd.)",
    'website': "https://www.gtucloud.com",
    'category': 'Productivity',
    'version': '19.0.2.4.1',
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
        'views/notify_config_views.xml',
        'views/hr_employee_views.xml',
        'views/res_company.xml',

        # Data
        'data/notify_config.xml',
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
