import sqlite3
import hashlib
import os
import shutil
from datetime import datetime, timedelta, timezone
import json
from contextlib import contextmanager

DATABASE_PATH = 'pcb_management.db'
UPLOAD_FOLDER = 'uploads'

# 北京时间工具函数
def get_beijing_time():
    """获取北京时间（UTC+8）"""
    beijing_tz = timezone(timedelta(hours=8))
    return datetime.now(beijing_tz)

@contextmanager
def get_db():
    """获取数据库连接的上下文管理器"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # 使结果可以像字典一样访问
    # 启用外键约束（SQLite默认关闭）
    conn.execute('PRAGMA foreign_keys = ON')
    try:
        yield conn
    finally:
        conn.close()

def hash_password(password):
    """密码哈希"""
    return hashlib.sha256(password.encode()).hexdigest()

def cleanup_orphaned_records():
    """清理数据库中的孤立记录"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 清理孤立的 project_components 记录（引用不存在的项目）
        cursor.execute('''
            DELETE FROM project_components 
            WHERE project_id NOT IN (SELECT id FROM projects)
        ''')
        orphaned_components = cursor.rowcount
        
        # 清理孤立的 project_requirements 记录
        cursor.execute('''
            DELETE FROM project_requirements 
            WHERE project_id NOT IN (SELECT id FROM projects)
        ''')
        orphaned_requirements = cursor.rowcount
        
        # 清理孤立的 project_collaborations 记录
        cursor.execute('''
            DELETE FROM project_collaborations 
            WHERE project_id NOT IN (SELECT id FROM projects)
        ''')
        orphaned_collaborations = cursor.rowcount
        
        # 清理孤立的 shares 记录
        cursor.execute('''
            DELETE FROM shares 
            WHERE project_id NOT IN (SELECT id FROM projects)
        ''')
        orphaned_shares = cursor.rowcount
        
        # 清理孤立的 upload_sessions 记录
        cursor.execute('''
            DELETE FROM upload_sessions 
            WHERE project_id NOT IN (SELECT id FROM projects)
        ''')
        orphaned_sessions = cursor.rowcount
        
        conn.commit()
        
        print(f"清理了 {orphaned_components} 条孤立的项目元器件记录")
        print(f"清理了 {orphaned_requirements} 条孤立的项目需求记录")
        print(f"清理了 {orphaned_collaborations} 条孤立的项目协作记录")
        print(f"清理了 {orphaned_shares} 条孤立的分享记录")
        print(f"清理了 {orphaned_sessions} 条孤立的上传会话记录")

def init_database():
    """初始化数据库表结构和基础数据"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 项目表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                source TEXT NOT NULL,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                board_type TEXT NOT NULL,
                status TEXT NOT NULL,
                remark TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # 元器件表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS components (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                model TEXT NOT NULL,
                price REAL NOT NULL
            )
        ''')
        
        # 项目元器件关联表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_components (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                component_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
                FOREIGN KEY (component_id) REFERENCES components (id)
            )
        ''')
        
        # 项目需求表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_requirements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                color TEXT NOT NULL DEFAULT '#2196F3',
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
            )
        ''')
        
        # 分享表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shares (
                id TEXT PRIMARY KEY,
                project_id INTEGER NOT NULL,
                owner_id INTEGER NOT NULL,
                password_hash TEXT,
                expire_time TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                max_access_count INTEGER DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
                FOREIGN KEY (owner_id) REFERENCES users (id)
            )
        ''')
        
        # 项目协作表（用户间共享）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_collaborations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                owner_id INTEGER NOT NULL,
                collaborator_id INTEGER NOT NULL,
                permission TEXT NOT NULL DEFAULT 'read', -- read, write
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
                FOREIGN KEY (owner_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (collaborator_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(project_id, collaborator_id)
            )
        ''')
        
        # 上传会话表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS upload_sessions (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                temp_dir TEXT NOT NULL,
                total_files INTEGER NOT NULL,
                uploaded_files INTEGER DEFAULT 0,
                file_list TEXT, -- JSON格式存储文件列表
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (project_id) REFERENCES projects (id)
            )
        ''')
        
        # 项目状态配置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS status_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                value TEXT UNIQUE NOT NULL,
                label TEXT NOT NULL,
                color TEXT NOT NULL,
                sort_order INTEGER DEFAULT 0
            )
        ''')
        
        # 项目来源配置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS source_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                sort_order INTEGER DEFAULT 0
            )
        ''')
        
        # 电路板类型配置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS board_type_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                sort_order INTEGER DEFAULT 0
            )
        ''')
        
        # 用户设置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                hide_prices BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()
        
        # 插入初始数据
        insert_initial_data(conn)
        
        # 确保所有表都已创建
        conn.commit()
        print("Database initialized successfully")
        
        # 迁移：为现有的shares表添加新字段（如果不存在）
        try:
            cursor.execute('SELECT access_count FROM shares LIMIT 1')
        except sqlite3.OperationalError:
            # 字段不存在，需要添加
            cursor.execute('ALTER TABLE shares ADD COLUMN access_count INTEGER DEFAULT 0')
            print("Added access_count column to shares table")
        
        try:
            cursor.execute('SELECT max_access_count FROM shares LIMIT 1')
        except sqlite3.OperationalError:
            # 字段不存在，需要添加
            cursor.execute('ALTER TABLE shares ADD COLUMN max_access_count INTEGER DEFAULT NULL')
            print("Added max_access_count column to shares table")
        
        conn.commit()

def insert_initial_data(conn):
    """插入初始数据"""
    cursor = conn.cursor()
    
    # 插入初始用户（如果不存在）
    users = [
        ('admin', 'admin', True),
        ('user1', 'user1', False),
        ('user2', 'user2', False)
    ]
    
    for username, password, is_admin in users:
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        if not cursor.fetchone():
            password_hash = hash_password(password)
            cursor.execute('''
                INSERT INTO users (username, password_hash, is_admin) 
                VALUES (?, ?, ?)
            ''', (username, password_hash, is_admin))
    
    # 插入项目状态配置（如果表为空）
    cursor.execute('SELECT COUNT(*) FROM status_config')
    if cursor.fetchone()[0] == 0:
        status_options = [
            ("进行中", "进行中", "linear-gradient(135deg, #69ff97 0%, #00e4ff 100%)", 1),
            ("已完成", "已完成", "linear-gradient(135deg, #13f1fc 0%, #0470dc 100%)", 2),
            ("审核中", "审核中", "linear-gradient(135deg, #ffd34f 0%, #ff9b44 100%)", 3),
            ("已暂停", "已暂停", "linear-gradient(135deg, #ff6b6b 0%, #556270 100%)", 4),
            ("已取消", "已取消", "linear-gradient(135deg, #f02fc2 0%, #6094ea 100%)", 5)
        ]
        
        cursor.executemany('''
            INSERT INTO status_config (value, label, color, sort_order) VALUES (?, ?, ?, ?)
        ''', status_options)
    
    # 插入项目来源配置（如果表为空）
    cursor.execute('SELECT COUNT(*) FROM source_config')
    if cursor.fetchone()[0] == 0:
        sources = [
            ("客户委托", 1),
            ("内部项目", 2),
            ("研发项目", 3),
            ("外部合作", 4)
        ]
        
        cursor.executemany('''
            INSERT INTO source_config (name, sort_order) VALUES (?, ?)
        ''', sources)
    
    # 插入电路板类型配置（如果表为空）
    cursor.execute('SELECT COUNT(*) FROM board_type_config')
    if cursor.fetchone()[0] == 0:
        board_types = [
            ("单层板", 1),
            ("双层板", 2),
            ("多层板", 3),
            ("柔性板", 4)
        ]
        
        cursor.executemany('''
            INSERT INTO board_type_config (name, sort_order) VALUES (?, ?)
        ''', board_types)
    
    # 插入元器件数据（如果表为空）
    cursor.execute('SELECT COUNT(*) FROM components')
    if cursor.fetchone()[0] == 0:
        components = [
            ("电阻", "R-100Ω", 0.5),
            ("电容", "C-100uF", 0.8),
            ("电感", "L-10uH", 1.2),
            ("二极管", "1N4007", 0.3),
            ("三极管", "2N2222", 0.6),
            ("运算放大器", "LM358", 2.5),
            ("微控制器", "STM32F103", 15.0),
            ("晶振", "12MHz", 1.0),
            ("LED灯", "5mm-Red", 0.2),
            ("电位器", "10K", 1.5),
            ("光敏电阻", "5mm", 0.8),
            ("温度传感器", "DS18B20", 3.5),
            ("蜂鸣器", "5V", 1.2),
            ("继电器", "5V-10A", 2.0),
            ("按钮开关", "6x6x5mm", 0.3),
            ("LCD显示屏", "1602", 8.0),
            ("电解电容", "1000uF/25V", 1.0),
            ("稳压器", "7805", 1.5),
            ("串口芯片", "CH340", 3.0)
        ]
        
        cursor.executemany('''
            INSERT INTO components (name, model, price) VALUES (?, ?, ?)
        ''', components)
    
    # 插入示例项目（为user1和admin）
    cursor.execute('SELECT id FROM users WHERE username = ?', ('user1',))
    user1_id = cursor.fetchone()
    if user1_id:
        user1_id = user1_id[0]
        cursor.execute('SELECT COUNT(*) FROM projects WHERE user_id = ?', (user1_id,))
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO projects (user_id, source, name, price, board_type, status, remark, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user1_id, "客户委托", "智能家居控制板", 1580.00, "双层板", "进行中", 
                  "客户要求高可靠性，需要支持WiFi和蓝牙双模通信，并预留扩展接口", 
                  "2024-03-20 14:30:00"))
            
            project_id = cursor.lastrowid
            
            # 添加项目元器件
            project_components = [
                (7, 1),  # 微控制器 x1
                (1, 10), # 电阻 x10
                (2, 8),  # 电容 x8
                (6, 2)   # 运算放大器 x2
            ]
            
            for comp_id, quantity in project_components:
                cursor.execute('''
                    INSERT INTO project_components (project_id, component_id, quantity)
                    VALUES (?, ?, ?)
                ''', (project_id, comp_id, quantity))
            
            # 添加项目需求
            requirements = [
                ("尺寸要求", "PCB尺寸不超过10cm x 8cm", "#2196F3"),
                ("性能要求", "支持WiFi 2.4GHz和蓝牙5.0", "#4CAF50"),
                ("接口要求", "预留UART和I2C扩展接口", "#FF9800")
            ]
            
            for title, content, color in requirements:
                cursor.execute('''
                    INSERT INTO project_requirements (project_id, title, content, color)
                    VALUES (?, ?, ?, ?)
                ''', (project_id, title, content, color))
    
    # 为admin用户创建示例项目
    cursor.execute('SELECT id FROM users WHERE username = ?', ('admin',))
    admin_id = cursor.fetchone()
    if admin_id:
        admin_id = admin_id[0]
        cursor.execute('SELECT COUNT(*) FROM projects WHERE user_id = ?', (admin_id,))
        if cursor.fetchone()[0] == 0:
            # 创建第一个项目
            cursor.execute('''
                INSERT INTO projects (user_id, source, name, price, board_type, status, remark, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (admin_id, "内部项目", "LED控制板测试", 680.00, "单层板", "已完成", 
                  "内部测试项目，验证LED驱动电路设计", 
                  "2024-03-15 10:00:00"))
            
            project_id1 = cursor.lastrowid
            
            # 添加第一个项目的元器件
            project_components1 = [
                (1, 5),  # 电阻 x5
                (9, 8),  # LED灯 x8
                (4, 4),  # 二极管 x4
            ]
            
            for comp_id, quantity in project_components1:
                cursor.execute('''
                    INSERT INTO project_components (project_id, component_id, quantity)
                    VALUES (?, ?, ?)
                ''', (project_id1, comp_id, quantity))
            
            # 添加第一个项目的需求
            requirements1 = [
                ("功能要求", "8路LED独立控制", "#4CAF50"),
                ("电源要求", "5V直流供电", "#2196F3")
            ]
            
            for title, content, color in requirements1:
                cursor.execute('''
                    INSERT INTO project_requirements (project_id, title, content, color)
                    VALUES (?, ?, ?, ?)
                ''', (project_id1, title, content, color))
            
            # 创建第二个项目
            cursor.execute('''
                INSERT INTO projects (user_id, source, name, price, board_type, status, remark, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (admin_id, "研发项目", "温度监控系统", 1200.00, "双层板", "进行中", 
                  "多点温度监控，支持数据记录和远程监控", 
                  "2024-03-22 16:20:00"))
            
            project_id2 = cursor.lastrowid
            
            # 添加第二个项目的元器件
            project_components2 = [
                (12, 4),  # 温度传感器 x4
                (7, 1),   # 微控制器 x1
                (1, 15),  # 电阻 x15
                (2, 10),  # 电容 x10
                (16, 1)   # LCD显示屏 x1
            ]
            
            for comp_id, quantity in project_components2:
                cursor.execute('''
                    INSERT INTO project_components (project_id, component_id, quantity)
                    VALUES (?, ?, ?)
                ''', (project_id2, comp_id, quantity))
            
            # 添加第二个项目的需求
            requirements2 = [
                ("传感器要求", "4路温度传感器，精度±0.5°C", "#FF9800"),
                ("显示要求", "LCD实时显示温度数据", "#2196F3"),
                ("通信要求", "支持串口数据输出", "#9C27B0")
            ]
            
            for title, content, color in requirements2:
                cursor.execute('''
                    INSERT INTO project_requirements (project_id, title, content, color)
                    VALUES (?, ?, ?, ?)
                ''', (project_id2, title, content, color))
    
    conn.commit()

# ==================== 用户相关操作 ====================

def authenticate_user(username, password):
    """用户认证"""
    with get_db() as conn:
        cursor = conn.cursor()
        password_hash = hash_password(password)
        cursor.execute('''
            SELECT id, username, is_admin FROM users 
            WHERE username = ? AND password_hash = ?
        ''', (username, password_hash))
        return cursor.fetchone()

def get_user_by_id(user_id):
    """根据ID获取用户信息"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        return cursor.fetchone()

def get_user_by_username(username):
    """根据用户名获取用户信息"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        return cursor.fetchone()

def get_all_users():
    """获取所有用户信息（管理员功能）"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, username, is_admin, created_at FROM users 
            ORDER BY created_at DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]

def create_user(username, password, is_admin=False):
    """创建新用户（管理员功能）"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 检查用户名是否已存在
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            return None, "用户名已存在"
        
        # 创建新用户
        password_hash = hash_password(password)
        try:
            cursor.execute('''
                INSERT INTO users (username, password_hash, is_admin)
                VALUES (?, ?, ?)
            ''', (username, password_hash, is_admin))
            conn.commit()
            return cursor.lastrowid, "用户创建成功"
        except Exception as e:
            return None, f"创建用户失败: {str(e)}"

def update_user(user_id, username=None, password=None, is_admin=None):
    """更新用户信息（管理员功能）"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 检查用户是否存在
        cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
        if not cursor.fetchone():
            return False, "用户不存在"
        
        # 构建更新语句
        update_fields = []
        update_values = []
        
        if username is not None:
            # 检查新用户名是否已被其他用户使用
            cursor.execute('SELECT id FROM users WHERE username = ? AND id != ?', (username, user_id))
            if cursor.fetchone():
                return False, "用户名已被其他用户使用"
            update_fields.append('username = ?')
            update_values.append(username)
        
        if password is not None:
            password_hash = hash_password(password)
            update_fields.append('password_hash = ?')
            update_values.append(password_hash)
        
        if is_admin is not None:
            update_fields.append('is_admin = ?')
            update_values.append(is_admin)
        
        if not update_fields:
            return False, "没有需要更新的字段"
        
        # 执行更新
        update_values.append(user_id)
        sql = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"
        
        try:
            cursor.execute(sql, update_values)
            conn.commit()
            return True, "用户信息更新成功"
        except Exception as e:
            return False, f"更新用户失败: {str(e)}"

def delete_user(user_id):
    """删除用户（管理员功能）"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 检查用户是否存在
        cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        if not user:
            return False, "用户不存在"
        
        username = user['username']
        
        try:
            # 删除用户的所有项目（这会级联删除相关数据）
            cursor.execute('SELECT id FROM projects WHERE user_id = ?', (user_id,))
            project_ids = [row['id'] for row in cursor.fetchall()]
            
            for project_id in project_ids:
                # 调用现有的删除项目函数来清理所有相关数据
                # 注意：这里我们需要临时跳过用户验证
                delete_project_admin(project_id, user_id)
            
            # 删除用户记录
            cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
            conn.commit()
            
            return True, f"用户 {username} 及其所有数据已删除"
        except Exception as e:
            return False, f"删除用户失败: {str(e)}"

def delete_project_admin(project_id, user_id):
    """管理员删除项目（不检查权限）"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 获取项目信息和用户信息
        cursor.execute('''
            SELECT p.*, u.username 
            FROM projects p
            JOIN users u ON p.user_id = u.id
            WHERE p.id = ?
        ''', (project_id,))
        
        project_info = cursor.fetchone()
        if not project_info:
            return False
        
        project_name = project_info['name']
        username = project_info['username']
        
        # 1. 删除项目相关的分享记录
        cursor.execute('DELETE FROM shares WHERE project_id = ?', (project_id,))
        
        # 2. 删除项目相关的上传会话
        cursor.execute('DELETE FROM upload_sessions WHERE project_id = ?', (project_id,))
        
        # 3. 删除项目文件夹及其所有文件
        project_folder_name = f"{username}-{project_name}"
        project_folder_path = os.path.join(UPLOAD_FOLDER, username, project_folder_name)
        
        if os.path.exists(project_folder_path):
            try:
                shutil.rmtree(project_folder_path)
                print(f"已删除项目文件夹: {project_folder_path}")
            except Exception as e:
                print(f"删除项目文件夹时出错: {e}")
        
        # 4. 清理相关的临时上传文件夹
        cleanup_temp_upload_folders(username, project_name)
        
        # 5. 删除项目记录
        cursor.execute('DELETE FROM projects WHERE id = ?', (project_id,))
        
        conn.commit()
        return True

def get_user_stats_admin():
    """获取系统用户统计信息（管理员功能）"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 总用户数
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        # 管理员数量
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_admin = 1')
        admin_count = cursor.fetchone()[0]
        
        # 普通用户数量
        regular_users = total_users - admin_count
        
        # 总项目数
        cursor.execute('SELECT COUNT(*) FROM projects')
        total_projects = cursor.fetchone()[0]
        
        # 活跃项目数
        cursor.execute('SELECT COUNT(*) FROM projects WHERE status = ?', ('进行中',))
        active_projects = cursor.fetchone()[0]
        
        # 总分享数
        cursor.execute('SELECT COUNT(*) FROM shares')
        total_shares = cursor.fetchone()[0]
        
        return {
            'total_users': total_users,
            'admin_count': admin_count,
            'regular_users': regular_users,
            'total_projects': total_projects,
            'active_projects': active_projects,
            'total_shares': total_shares
        }

# ==================== 项目相关操作 ====================

def get_user_projects(user_id):
    """获取用户的所有项目（包含拥有的和协作的项目）"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 获取用户拥有的项目
        cursor.execute('''
            SELECT p.*, 'owner' as user_role,
                   GROUP_CONCAT(DISTINCT pc.component_id || ':' || pc.quantity) as component_data,
                   GROUP_CONCAT(DISTINCT pr.title || '|' || pr.content || '|' || pr.color) as requirements_data
            FROM projects p
            LEFT JOIN project_components pc ON p.id = pc.project_id
            LEFT JOIN project_requirements pr ON p.id = pr.project_id
            WHERE p.user_id = ?
            GROUP BY p.id
            
            UNION ALL
            
            SELECT p.*, pcol.permission as user_role,
                   GROUP_CONCAT(DISTINCT pc.component_id || ':' || pc.quantity) as component_data,
                   GROUP_CONCAT(DISTINCT pr.title || '|' || pr.content || '|' || pr.color) as requirements_data
            FROM projects p
            JOIN project_collaborations pcol ON p.id = pcol.project_id
            LEFT JOIN project_components pc ON p.id = pc.project_id
            LEFT JOIN project_requirements pr ON p.id = pr.project_id
            WHERE pcol.collaborator_id = ?
            GROUP BY p.id
            
            ORDER BY created_at ASC
        ''', (user_id, user_id))
        
        projects = []
        for row in cursor.fetchall():
            project = dict(row)
            
            # 处理元器件数据
            components = []
            if project['component_data']:
                comp_data = project['component_data'].split(',')
                for comp in comp_data:
                    if ':' in comp:
                        comp_id, quantity = comp.split(':')
                        component_info = get_component_by_id(int(comp_id))
                        if component_info:
                            components.append({
                                'id': int(comp_id),
                                'name': component_info['name'],
                                'model': component_info['model'],
                                'price': component_info['price'],
                                'quantity': int(quantity)
                            })
            project['components'] = components
            
            # 处理需求数据
            requirements = []
            if project['requirements_data']:
                req_items = project['requirements_data'].split(',')
                for req_item in req_items:
                    if '|' in req_item:
                        parts = req_item.split('|')
                        if len(parts) >= 3:
                            requirements.append({
                                'title': parts[0],
                                'content': parts[1],
                                'color': parts[2]
                            })
            project['requirements'] = requirements
            
            # 检查共享状态
            project['is_shared_by_me'] = False
            project['is_shared_to_me'] = False
            
            if project['user_role'] == 'owner':
                # 如果是项目所有者，检查是否共享给了别人
                cursor.execute('''
                    SELECT COUNT(*) as count FROM project_collaborations 
                    WHERE project_id = ? AND owner_id = ?
                ''', (project['id'], user_id))
                collab_count = cursor.fetchone()['count']
                project['is_shared_by_me'] = collab_count > 0
            else:
                # 如果是协作者，标记为被共享的项目
                project['is_shared_to_me'] = True
                # 获取项目所有者信息
                cursor.execute('SELECT username FROM users WHERE id = ?', (project['user_id'],))
                owner_info = cursor.fetchone()
                project['owner_username'] = owner_info['username'] if owner_info else '未知用户'
            
            # 清理不需要的字段
            del project['component_data']
            del project['requirements_data']
            
            projects.append(project)
        
        return projects

def get_project_by_id(project_id, user_id=None):
    """获取项目详情"""
    with get_db() as conn:
        cursor = conn.cursor()
        query = 'SELECT * FROM projects WHERE id = ?'
        params = [project_id]
        
        if user_id:
            query += ' AND user_id = ?'
            params.append(user_id)
            
        cursor.execute(query, params)
        project = cursor.fetchone()
        
        if not project:
            return None
        
        project = dict(project)
        
        # 获取元器件信息
        cursor.execute('''
            SELECT c.*, pc.quantity 
            FROM components c
            JOIN project_components pc ON c.id = pc.component_id
            WHERE pc.project_id = ?
        ''', (project_id,))
        
        components = []
        for comp in cursor.fetchall():
            components.append({
                'id': comp['id'],
                'name': comp['name'],
                'model': comp['model'],
                'price': comp['price'],
                'quantity': comp['quantity']
            })
        project['components'] = components
        
        # 获取需求信息
        cursor.execute('''
            SELECT title, content, color FROM project_requirements WHERE project_id = ?
        ''', (project_id,))
        
        requirements = []
        for req in cursor.fetchall():
            requirements.append({
                'title': req['title'],
                'content': req['content'],
                'color': req['color']
            })
        project['requirements'] = requirements
        
        return project

def create_project(user_id, project_data):
    """创建新项目"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 插入项目基本信息
        cursor.execute('''
            INSERT INTO projects (user_id, source, name, price, board_type, status, remark)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, project_data['source'], project_data['name'], 
              project_data['price'], project_data['board_type'], 
              project_data['status'], project_data.get('remark', '')))
        
        project_id = cursor.lastrowid
        
        # 添加元器件
        if 'components' in project_data:
            for comp in project_data['components']:
                cursor.execute('''
                    INSERT INTO project_components (project_id, component_id, quantity)
                    VALUES (?, ?, ?)
                ''', (project_id, comp['id'], comp['quantity']))
        
        # 添加需求
        if 'requirements' in project_data:
            for req in project_data['requirements']:
                cursor.execute('''
                    INSERT INTO project_requirements (project_id, title, content, color)
                    VALUES (?, ?, ?, ?)
                ''', (project_id, req['title'], req['content'], req['color']))
        
        conn.commit()
        return project_id

def update_project(project_id, user_id, project_data):
    """更新项目"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 更新项目基本信息
        cursor.execute('''
            UPDATE projects 
            SET source = ?, name = ?, price = ?, board_type = ?, status = ?, remark = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
        ''', (project_data['source'], project_data['name'], project_data['price'], 
              project_data['board_type'], project_data['status'], 
              project_data.get('remark', ''), project_id, user_id))
        
        if cursor.rowcount == 0:
            return False
        
        # 删除现有的元器件和需求
        cursor.execute('DELETE FROM project_components WHERE project_id = ?', (project_id,))
        cursor.execute('DELETE FROM project_requirements WHERE project_id = ?', (project_id,))
        
        # 重新添加元器件
        if 'components' in project_data:
            for comp in project_data['components']:
                cursor.execute('''
                    INSERT INTO project_components (project_id, component_id, quantity)
                    VALUES (?, ?, ?)
                ''', (project_id, comp['id'], comp['quantity']))
        
        # 重新添加需求
        if 'requirements' in project_data:
            for req in project_data['requirements']:
                cursor.execute('''
                    INSERT INTO project_requirements (project_id, title, content, color)
                    VALUES (?, ?, ?, ?)
                ''', (project_id, req['title'], req['content'], req['color']))
        
        conn.commit()
        return True

def delete_project(project_id, user_id):
    """删除项目，同时删除相关的分享、文件和上传会话"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 获取项目信息和用户信息
        cursor.execute('''
            SELECT p.*, u.username 
            FROM projects p
            JOIN users u ON p.user_id = u.id
            WHERE p.id = ? AND p.user_id = ?
        ''', (project_id, user_id))
        
        project_info = cursor.fetchone()
        if not project_info:
            return False
        
        project_name = project_info['name']
        username = project_info['username']
        
        # 1. 删除项目相关的分享记录
        cursor.execute('DELETE FROM shares WHERE project_id = ?', (project_id,))
        
        # 2. 删除项目相关的上传会话
        cursor.execute('DELETE FROM upload_sessions WHERE project_id = ?', (project_id,))
        
        # 3. 删除项目文件夹及其所有文件
        project_folder_name = f"{username}-{project_name}"
        project_folder_path = os.path.join(UPLOAD_FOLDER, username, project_folder_name)
        
        if os.path.exists(project_folder_path):
            try:
                shutil.rmtree(project_folder_path)
                print(f"已删除项目文件夹: {project_folder_path}")
            except Exception as e:
                print(f"删除项目文件夹时出错: {e}")
                # 即使文件删除失败，也继续删除数据库记录
        
        # 4. 清理相关的临时上传文件夹
        cleanup_temp_upload_folders(username, project_name)
        
        # 5. 删除项目记录（相关的 project_components 和 project_requirements 会自动级联删除）
        cursor.execute('DELETE FROM projects WHERE id = ? AND user_id = ?', (project_id, user_id))
        
        conn.commit()
        return cursor.rowcount > 0

def cleanup_temp_upload_folders(username, project_name):
    """清理项目相关的临时上传文件夹"""
    try:
        user_upload_dir = os.path.join(UPLOAD_FOLDER, username)
        if not os.path.exists(user_upload_dir):
            return
        
        project_folder_prefix = f"temp_.*_{username}-{project_name}"
        
        # 遍历用户上传目录，找到匹配的临时文件夹
        for item in os.listdir(user_upload_dir):
            item_path = os.path.join(user_upload_dir, item)
            if os.path.isdir(item_path) and item.startswith('temp_') and f"{username}-{project_name}" in item:
                try:
                    shutil.rmtree(item_path)
                    print(f"已删除临时文件夹: {item_path}")
                except Exception as e:
                    print(f"删除临时文件夹时出错: {e}")
    except Exception as e:
        print(f"清理临时文件夹时出错: {e}")

# ==================== 元器件相关操作 ====================

def get_all_components():
    """获取所有元器件"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM components ORDER BY name')
        return [dict(row) for row in cursor.fetchall()]

def get_component_by_id(component_id):
    """根据ID获取元器件"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM components WHERE id = ?', (component_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

# ==================== 分享相关操作 ====================

def create_share(share_id, project_id, owner_id, password_hash=None, expire_time=None, max_access_count=None):
    """创建分享"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO shares (id, project_id, owner_id, password_hash, expire_time, max_access_count, access_count)
            VALUES (?, ?, ?, ?, ?, ?, 0)
        ''', (share_id, project_id, owner_id, password_hash, expire_time, max_access_count))
        conn.commit()

def get_share_by_id(share_id):
    """获取分享信息"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.*, p.name as project_name, u.username as owner_username
            FROM shares s
            JOIN projects p ON s.project_id = p.id
            JOIN users u ON s.owner_id = u.id
            WHERE s.id = ?
        ''', (share_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def delete_share(share_id):
    """删除分享"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM shares WHERE id = ?', (share_id,))
        conn.commit()
        return cursor.rowcount > 0

def increment_share_access_count(share_id):
    """增加分享访问计数"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE shares 
            SET access_count = COALESCE(access_count, 0) + 1 
            WHERE id = ?
        ''', (share_id,))
        conn.commit()
        return cursor.rowcount > 0

def get_project_share(project_id, owner_id):
    """获取项目的分享信息"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM shares WHERE project_id = ? AND owner_id = ?
        ''', (project_id, owner_id))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_project_share_by_project_id(project_id):
    """通过项目ID获取分享信息（不限制所有者）"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.*, u.username as owner_username, p.name as project_name
            FROM shares s
            JOIN users u ON s.owner_id = u.id
            JOIN projects p ON s.project_id = p.id
            WHERE s.project_id = ?
        ''', (project_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

# ==================== 上传会话相关操作 ====================

def create_upload_session(session_id, user_id, project_id, temp_dir, total_files):
    """创建上传会话"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO upload_sessions (id, user_id, project_id, temp_dir, total_files, file_list)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session_id, user_id, project_id, temp_dir, total_files, '[]'))
        conn.commit()

def get_upload_session(session_id):
    """获取上传会话"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM upload_sessions WHERE id = ?', (session_id,))
        row = cursor.fetchone()
        if row:
            session_data = dict(row)
            session_data['file_list'] = json.loads(session_data['file_list'])
            return session_data
        return None

def update_upload_session(session_id, uploaded_files_count, file_list):
    """更新上传会话"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE upload_sessions 
            SET uploaded_files = ?, file_list = ?
            WHERE id = ?
        ''', (uploaded_files_count, json.dumps(file_list), session_id))
        conn.commit()

def delete_upload_session(session_id):
    """删除上传会话"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM upload_sessions WHERE id = ?', (session_id,))
        conn.commit()

def cleanup_expired_upload_sessions(hours=24):
    """清理过期的上传会话"""
    with get_db() as conn:
        cursor = conn.cursor()
        expire_time = get_beijing_time() - timedelta(hours=hours)
        cursor.execute('''
            DELETE FROM upload_sessions 
            WHERE created_at < ?
        ''', (expire_time.isoformat(),))
        conn.commit()

# ==================== 统计相关操作 ====================

def get_user_stats(user_id):
    """获取用户统计信息"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 总项目数
        cursor.execute('SELECT COUNT(*) FROM projects WHERE user_id = ?', (user_id,))
        total_projects = cursor.fetchone()[0]
        
        # 未完成项目数 (不是"已完成"状态的项目)
        cursor.execute('SELECT COUNT(*) FROM projects WHERE user_id = ? AND status != ?', (user_id, '已完成'))
        incomplete_projects = cursor.fetchone()[0]
        
        # 总价格
        cursor.execute('SELECT COALESCE(SUM(price), 0) FROM projects WHERE user_id = ?', (user_id,))
        total_price = cursor.fetchone()[0]
        
        # 未完成项目总价格
        cursor.execute('SELECT COALESCE(SUM(price), 0) FROM projects WHERE user_id = ? AND status != ?', (user_id, '已完成'))
        incomplete_price = cursor.fetchone()[0]
        
        # 元器件总价格 (通过项目元器件关联表计算)
        cursor.execute('''
            SELECT COALESCE(SUM(c.price * pc.quantity), 0) 
            FROM project_components pc 
            JOIN components c ON pc.component_id = c.id 
            JOIN projects p ON pc.project_id = p.id 
            WHERE p.user_id = ?
        ''', (user_id,))
        components_total_price = cursor.fetchone()[0]
        
        return {
            'total_projects': total_projects,
            'incomplete_projects': incomplete_projects,
            'total_price': float(total_price),
            'incomplete_price': float(incomplete_price),
            'components_total_price': float(components_total_price)
        }

# ==================== 配置管理相关操作 ====================

def get_status_config():
    """获取项目状态配置"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM status_config ORDER BY sort_order')
        return [dict(row) for row in cursor.fetchall()]

def get_source_config():
    """获取项目来源配置"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM source_config ORDER BY sort_order')
        return [dict(row) for row in cursor.fetchall()]

def get_board_type_config():
    """获取电路板类型配置"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM board_type_config ORDER BY sort_order')
        return [dict(row) for row in cursor.fetchall()]

def add_status_config(value, label, color, sort_order=0):
    """添加项目状态配置"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO status_config (value, label, color, sort_order)
                VALUES (?, ?, ?, ?)
            ''', (value, label, color, sort_order))
            conn.commit()
            return True, "状态配置添加成功"
        except sqlite3.IntegrityError:
            return False, "状态值已存在"
        except Exception as e:
            return False, f"添加失败: {str(e)}"

def update_status_config(config_id, value, label, color, sort_order):
    """更新项目状态配置"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE status_config 
                SET value = ?, label = ?, color = ?, sort_order = ?
                WHERE id = ?
            ''', (value, label, color, sort_order, config_id))
            conn.commit()
            if cursor.rowcount == 0:
                return False, "配置不存在"
            return True, "状态配置更新成功"
        except sqlite3.IntegrityError:
            return False, "状态值已存在"
        except Exception as e:
            return False, f"更新失败: {str(e)}"

def delete_status_config(config_id):
    """删除项目状态配置"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            # 检查是否有项目在使用这个状态
            cursor.execute('SELECT value FROM status_config WHERE id = ?', (config_id,))
            status_row = cursor.fetchone()
            if not status_row:
                return False, "配置不存在"
            
            status_value = status_row['value']
            cursor.execute('SELECT COUNT(*) FROM projects WHERE status = ?', (status_value,))
            if cursor.fetchone()[0] > 0:
                return False, "该状态正在被项目使用，无法删除"
            
            cursor.execute('DELETE FROM status_config WHERE id = ?', (config_id,))
            conn.commit()
            return True, "状态配置删除成功"
        except Exception as e:
            return False, f"删除失败: {str(e)}"

def add_source_config(name, sort_order=0):
    """添加项目来源配置"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO source_config (name, sort_order)
                VALUES (?, ?)
            ''', (name, sort_order))
            conn.commit()
            return True, "来源配置添加成功"
        except sqlite3.IntegrityError:
            return False, "来源名称已存在"
        except Exception as e:
            return False, f"添加失败: {str(e)}"

def update_source_config(config_id, name, sort_order):
    """更新项目来源配置"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE source_config 
                SET name = ?, sort_order = ?
                WHERE id = ?
            ''', (name, sort_order, config_id))
            conn.commit()
            if cursor.rowcount == 0:
                return False, "配置不存在"
            return True, "来源配置更新成功"
        except sqlite3.IntegrityError:
            return False, "来源名称已存在"
        except Exception as e:
            return False, f"更新失败: {str(e)}"

def delete_source_config(config_id):
    """删除项目来源配置"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            # 检查是否有项目在使用这个来源
            cursor.execute('SELECT name FROM source_config WHERE id = ?', (config_id,))
            source_row = cursor.fetchone()
            if not source_row:
                return False, "配置不存在"
            
            source_name = source_row['name']
            cursor.execute('SELECT COUNT(*) FROM projects WHERE source = ?', (source_name,))
            if cursor.fetchone()[0] > 0:
                return False, "该来源正在被项目使用，无法删除"
            
            cursor.execute('DELETE FROM source_config WHERE id = ?', (config_id,))
            conn.commit()
            return True, "来源配置删除成功"
        except Exception as e:
            return False, f"删除失败: {str(e)}"

def add_board_type_config(name, sort_order=0):
    """添加电路板类型配置"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO board_type_config (name, sort_order)
                VALUES (?, ?)
            ''', (name, sort_order))
            conn.commit()
            return True, "电路板类型配置添加成功"
        except sqlite3.IntegrityError:
            return False, "电路板类型名称已存在"
        except Exception as e:
            return False, f"添加失败: {str(e)}"

def update_board_type_config(config_id, name, sort_order):
    """更新电路板类型配置"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE board_type_config 
                SET name = ?, sort_order = ?
                WHERE id = ?
            ''', (name, sort_order, config_id))
            conn.commit()
            if cursor.rowcount == 0:
                return False, "配置不存在"
            return True, "电路板类型配置更新成功"
        except sqlite3.IntegrityError:
            return False, "电路板类型名称已存在"
        except Exception as e:
            return False, f"更新失败: {str(e)}"

def delete_board_type_config(config_id):
    """删除电路板类型配置"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            # 检查是否有项目在使用这个类型
            cursor.execute('SELECT name FROM board_type_config WHERE id = ?', (config_id,))
            type_row = cursor.fetchone()
            if not type_row:
                return False, "配置不存在"
            
            type_name = type_row['name']
            cursor.execute('SELECT COUNT(*) FROM projects WHERE board_type = ?', (type_name,))
            if cursor.fetchone()[0] > 0:
                return False, "该电路板类型正在被项目使用，无法删除"
            
            cursor.execute('DELETE FROM board_type_config WHERE id = ?', (config_id,))
            conn.commit()
            return True, "电路板类型配置删除成功"
        except Exception as e:
            return False, f"删除失败: {str(e)}"

def add_component(name, model, price):
    """添加元器件"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO components (name, model, price)
                VALUES (?, ?, ?)
            ''', (name, model, price))
            conn.commit()
            return True, "元器件添加成功"
        except Exception as e:
            return False, f"添加失败: {str(e)}"

def update_component(component_id, name, model, price):
    """更新元器件"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE components 
                SET name = ?, model = ?, price = ?
                WHERE id = ?
            ''', (name, model, price, component_id))
            conn.commit()
            if cursor.rowcount == 0:
                return False, "元器件不存在"
            return True, "元器件更新成功"
        except Exception as e:
            return False, f"更新失败: {str(e)}"

def delete_component(component_id):
    """删除元器件"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        try:
            # 检查是否有项目在使用这个元器件
            cursor.execute('''
                SELECT COUNT(*) FROM project_components 
                WHERE component_id = ?
            ''', (component_id,))
            
            if cursor.fetchone()[0] > 0:
                return False, "该元器件正在被项目使用，无法删除"
            
            # 删除元器件
            cursor.execute('DELETE FROM components WHERE id = ?', (component_id,))
            conn.commit()
            
            if cursor.rowcount == 0:
                return False, "元器件不存在"
            
            return True, "元器件删除成功"
        except Exception as e:
            return False, f"删除失败: {str(e)}"

# ============= 项目协作相关函数 =============

def add_project_collaboration(project_id, owner_id, collaborator_id, permission='read'):
    """添加项目协作者"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 检查项目是否存在且属于owner
        cursor.execute('''
            SELECT id FROM projects 
            WHERE id = ? AND user_id = ?
        ''', (project_id, owner_id))
        
        if not cursor.fetchone():
            raise ValueError("项目不存在或无权限")
        
        # 检查用户是否存在
        cursor.execute('SELECT id FROM users WHERE id = ?', (collaborator_id,))
        if not cursor.fetchone():
            raise ValueError("用户不存在")
        
        # 检查是否已经是协作者
        cursor.execute('''
            SELECT id FROM project_collaborations 
            WHERE project_id = ? AND collaborator_id = ?
        ''', (project_id, collaborator_id))
        
        if cursor.fetchone():
            raise ValueError("用户已经是该项目的协作者")
        
        # 添加协作关系
        cursor.execute('''
            INSERT INTO project_collaborations 
            (project_id, owner_id, collaborator_id, permission)
            VALUES (?, ?, ?, ?)
        ''', (project_id, owner_id, collaborator_id, permission))
        
        conn.commit()
        return cursor.lastrowid

def remove_project_collaboration(project_id, owner_id, collaborator_id):
    """移除项目协作者"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 如果owner_id为None，表示是协作者自己退出，只需要验证协作关系存在
        if owner_id is None:
            # 检查协作关系是否存在
            cursor.execute('''
                SELECT id FROM project_collaborations 
                WHERE project_id = ? AND collaborator_id = ?
            ''', (project_id, collaborator_id))
            
            if not cursor.fetchone():
                raise ValueError("协作关系不存在")
        else:
            # 检查项目是否存在且属于owner
            cursor.execute('''
                SELECT id FROM projects 
                WHERE id = ? AND user_id = ?
            ''', (project_id, owner_id))
            
            if not cursor.fetchone():
                raise ValueError("项目不存在或无权限")
        
        # 删除协作关系
        cursor.execute('''
            DELETE FROM project_collaborations 
            WHERE project_id = ? AND collaborator_id = ?
        ''', (project_id, collaborator_id))
        
        conn.commit()
        
        if cursor.rowcount == 0:
            raise ValueError("协作关系不存在")
        
        return True

def get_project_collaborations(project_id, owner_id):
    """获取项目的所有协作者"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 检查项目是否存在且属于owner
        cursor.execute('''
            SELECT id FROM projects 
            WHERE id = ? AND user_id = ?
        ''', (project_id, owner_id))
        
        if not cursor.fetchone():
            raise ValueError("项目不存在或无权限")
        
        # 获取协作者列表
        cursor.execute('''
            SELECT pc.id, pc.collaborator_id, pc.permission, pc.created_at,
                   u.username
            FROM project_collaborations pc
            JOIN users u ON pc.collaborator_id = u.id
            WHERE pc.project_id = ?
            ORDER BY pc.created_at DESC
        ''', (project_id,))
        
        collaborations = []
        for row in cursor.fetchall():
            collaborations.append({
                'id': row[0],
                'collaborator_id': row[1],
                'permission': row[2],
                'created_at': row[3],
                'username': row[4]
            })
        
        return collaborations

def get_user_collaborated_projects(user_id):
    """获取用户参与协作的项目列表"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT p.*, u.username as owner_username, pc.permission
            FROM projects p
            JOIN project_collaborations pc ON p.id = pc.project_id
            JOIN users u ON p.user_id = u.id
            WHERE pc.collaborator_id = ?
            ORDER BY pc.created_at ASC
        ''', (user_id,))
        
        projects = []
        for row in cursor.fetchall():
            project = dict(row)
            projects.append(project)
        
        return projects

def update_collaboration_permission(collaboration_id, owner_id, permission):
    """更新协作者权限"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 检查协作关系是否存在且属于owner
        cursor.execute('''
            SELECT pc.project_id 
            FROM project_collaborations pc
            JOIN projects p ON pc.project_id = p.id
            WHERE pc.id = ? AND p.user_id = ?
        ''', (collaboration_id, owner_id))
        
        if not cursor.fetchone():
            raise ValueError("协作关系不存在或无权限")
        
        # 更新权限
        cursor.execute('''
            UPDATE project_collaborations 
            SET permission = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (permission, collaboration_id))
        
        conn.commit()
        
        if cursor.rowcount == 0:
            raise ValueError("更新失败")
        
        return True

def check_project_access(project_id, user_id):
    """检查用户是否有项目访问权限"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 检查是否是项目所有者
        cursor.execute('''
            SELECT id FROM projects 
            WHERE id = ? AND user_id = ?
        ''', (project_id, user_id))
        
        if cursor.fetchone():
            return {'access': True, 'permission': 'owner'}
        
        # 检查是否是协作者
        cursor.execute('''
            SELECT permission FROM project_collaborations 
            WHERE project_id = ? AND collaborator_id = ?
        ''', (project_id, user_id))
        
        result = cursor.fetchone()
        if result:
            return {'access': True, 'permission': result[0]}
        
        return {'access': False, 'permission': None}

def get_available_collaborators(exclude_user_id):
    """获取可添加为协作者的用户列表（排除指定用户）"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, created_at
            FROM users 
            WHERE id != ? AND is_admin = 0
            ORDER BY username
        ''', (exclude_user_id,))
        
        users = []
        for row in cursor.fetchall():
            users.append({
                'id': row[0],
                'username': row[1],
                'created_at': row[2]
            })
        
        return users

# ==================== 用户设置相关操作 ====================

def get_user_settings(user_id):
    """获取用户设置"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM user_settings WHERE user_id = ?', (user_id,))
        settings = cursor.fetchone()
        
        if settings:
            return dict(settings)
        else:
            # 如果用户设置不存在，创建默认设置
            cursor.execute('''
                INSERT INTO user_settings (user_id, hide_prices)
                VALUES (?, FALSE)
            ''', (user_id,))
            conn.commit()
            return {
                'user_id': user_id,
                'hide_prices': False,
                'created_at': get_beijing_time().isoformat(),
                'updated_at': get_beijing_time().isoformat()
            }

def update_user_settings(user_id, hide_prices=None):
    """更新用户设置"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 检查设置是否存在
        cursor.execute('SELECT id FROM user_settings WHERE user_id = ?', (user_id,))
        if cursor.fetchone():
            # 更新现有设置
            if hide_prices is not None:
                cursor.execute('''
                    UPDATE user_settings 
                    SET hide_prices = ?, updated_at = ?
                    WHERE user_id = ?
                ''', (hide_prices, get_beijing_time().isoformat(), user_id))
        else:
            # 创建新设置
            cursor.execute('''
                INSERT INTO user_settings (user_id, hide_prices, updated_at)
                VALUES (?, ?, ?)
            ''', (user_id, hide_prices if hide_prices is not None else False, get_beijing_time().isoformat()))
        
        conn.commit()
        return True

# 初始化数据库（如果数据库文件不存在则创建）
if not os.path.exists(DATABASE_PATH):
    init_database() 