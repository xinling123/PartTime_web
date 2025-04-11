import shutil
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, send_file
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta, timezone
import uuid
import zipfile
import tempfile
from flask import after_this_request
import hashlib
from functools import wraps
import database as db

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 设置密钥

# 配置上传文件夹和限制
UPLOAD_FOLDER = 'uploads'
app.config.update(
    UPLOAD_FOLDER=UPLOAD_FOLDER,
    MAX_FILES_PER_UPLOAD=10,  # 每次上传最大文件数
    MAX_FILE_SIZE_MB=300,     # 单个文件最大大小（MB）
    PERMANENT_SESSION_LIFETIME=timedelta(hours=2),  # session过期时间设置为2小时
)

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# 北京时间工具函数
def get_beijing_time():
    """获取北京时间（UTC+8）"""
    beijing_tz = timezone(timedelta(hours=8))
    return datetime.now(beijing_tz)

def beijing_time_from_iso(iso_string):
    """从ISO字符串转换为北京时间"""
    beijing_tz = timezone(timedelta(hours=8))
    dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        # 如果没有时区信息，假设是北京时间
        dt = dt.replace(tzinfo=beijing_tz)
    else:
        # 转换为北京时间
        dt = dt.astimezone(beijing_tz)
    return dt

# Session过期检查装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 检查用户是否登录
        if 'user_id' not in session:
            return redirect(url_for('index'))
        
        # 检查session是否过期
        if 'login_time' in session:
            login_time = beijing_time_from_iso(session['login_time'])
            current_time = get_beijing_time()
            if current_time - login_time > app.config['PERMANENT_SESSION_LIFETIME']:
                session.clear()
                return redirect(url_for('index', error='登录已过期，请重新登录'))
        
        return f(*args, **kwargs)
    return decorated_function

# 管理员session过期检查装饰器
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 检查管理员是否登录
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        
        # 检查session是否过期
        if 'admin_login_time' in session:
            login_time = beijing_time_from_iso(session['admin_login_time'])
            current_time = get_beijing_time()
            if current_time - login_time > app.config['PERMANENT_SESSION_LIFETIME']:
                session.clear()
                return redirect(url_for('admin_login', error='登录已过期，请重新登录'))
        
        return f(*args, **kwargs)
    return decorated_function

# API认证装饰器
def api_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 检查用户是否登录
        if 'user_id' not in session:
            return jsonify({'error': '请先登录'}), 401
        
        # 检查session是否过期
        if 'login_time' in session:
            login_time = beijing_time_from_iso(session['login_time'])
            current_time = get_beijing_time()
            if current_time - login_time > app.config['PERMANENT_SESSION_LIFETIME']:
                session.clear()
                return jsonify({'error': '登录已过期，请重新登录'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

# 管理员API认证装饰器
def api_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 检查管理员是否登录
        if not session.get('admin_logged_in'):
            return jsonify({'error': '管理员权限不足'}), 403
        
        # 检查session是否过期
        if 'admin_login_time' in session:
            login_time = beijing_time_from_iso(session['admin_login_time'])
            current_time = get_beijing_time()
            if current_time - login_time > app.config['PERMANENT_SESSION_LIFETIME']:
                session.clear()
                return jsonify({'error': '登录已过期，请重新登录'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

# 模拟项目数据
projects = [
    {
        "id": 1,
        "source": "客户委托",
        "name": "智能家居控制板",
        "price": 1580.00,
        "board_type": "双层板",
        "status": "进行中",
        "remark": "客户要求高可靠性，需要支持WiFi和蓝牙双模通信，并预留扩展接口",
        "created_at": "2024-03-20 14:30:00",
        "components": [
            {"id": 7, "name": "微控制器", "model": "STM32F103", "price": 15.0, "quantity": 1},
            {"id": 1, "name": "电阻", "model": "R-100Ω", "price": 0.5, "quantity": 10},
            {"id": 2, "name": "电容", "model": "C-100uF", "price": 0.8, "quantity": 8},
            {"id": 6, "name": "运算放大器", "model": "LM358", "price": 2.5, "quantity": 2}
        ],
        "requirements": [
            {"title": "尺寸要求", "content": "PCB尺寸不超过10cm x 8cm", "color": "#2196F3"},
            {"title": "性能要求", "content": "支持WiFi 2.4GHz和蓝牙5.0", "color": "#4CAF50"},
            {"title": "接口要求", "content": "预留UART和I2C扩展接口", "color": "#FF9800"}
        ]
    }
]

# 分享信息存储 (在实际应用中应该使用数据库)
shares = {}

# 路由定义
@app.route('/')
@app.route('/login')
def index():
    error = request.args.get('error')
    return render_template('index.html', error=error)

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    
    # 使用数据库认证用户
    user = db.authenticate_user(username, password)
    if user:
        session.permanent = True  # 设置session为permanent
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['is_admin'] = user['is_admin']
        session['login_time'] = get_beijing_time().isoformat()  # 记录登录时间（北京时间）
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('index', error='用户名或密码错误'))

@app.route('/dashboard')
@login_required
def dashboard():
    # 从数据库获取用户项目
    user_projects = db.get_user_projects(session['user_id'])
    # 获取用户统计信息
    stats = db.get_user_stats(session['user_id'])
    # 获取用户设置
    user_settings = db.get_user_settings(session['user_id'])
    return render_template('dashboard.html', jobs=user_projects, stats=stats, user_settings=user_settings)

@app.route('/admin/login')
def admin_login():
    error = request.args.get('error')
    return render_template('admin_login.html', error=error)

@app.route('/admin/login', methods=['POST'])
def admin_login_process():
    username = request.form['username']
    password = request.form['password']
    
    # 使用数据库认证管理员
    user = db.authenticate_user(username, password)
    if user and user['is_admin']:
        session.permanent = True  # 设置session为permanent
        session['admin_logged_in'] = True
        session['admin_user_id'] = user['id']
        session['admin_username'] = user['username']
        session['admin_login_time'] = get_beijing_time().isoformat()  # 记录登录时间（北京时间）
        return redirect(url_for('admin_dashboard'))
    
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_user_id', None)
    session.pop('admin_username', None)
    return redirect(url_for('admin_login'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# 测试session状态的路由（可选，用于调试）
@app.route('/api/session/status')
@api_login_required
def session_status():
    """获取session状态信息"""
    if 'login_time' in session:
        login_time = beijing_time_from_iso(session['login_time'])
        current_time = get_beijing_time()
        elapsed_time = current_time - login_time
        remaining_time = app.config['PERMANENT_SESSION_LIFETIME'] - elapsed_time
        
        return jsonify({
            'user_id': session['user_id'],
            'username': session['username'],
            'login_time': session['login_time'],
            'current_time': current_time.isoformat(),
            'elapsed_time_seconds': int(elapsed_time.total_seconds()),
            'remaining_time_seconds': int(remaining_time.total_seconds()) if remaining_time.total_seconds() > 0 else 0,
            'is_expired': remaining_time.total_seconds() <= 0,
            'timezone': 'Asia/Shanghai (UTC+8)'
        })
    else:
        return jsonify({'error': '登录时间信息缺失'}), 400

# API 路由
@app.route('/api/sources')
def get_sources():
    """获取所有来源选项"""
    sources = db.get_source_config()
    return jsonify([{"id": s["id"], "name": s["name"]} for s in sources])

@app.route('/api/board-types')
def get_board_types():
    """获取所有电路板类型"""
    board_types = db.get_board_type_config()
    return jsonify([{"id": t["id"], "name": t["name"]} for t in board_types])

@app.route('/api/components')
def get_all_components():
    """获取所有元器件"""
    components = db.get_all_components()
    return jsonify(components)

@app.route('/api/status')
def get_status_options():
    """获取所有状态选项"""
    status_options = db.get_status_config()
    return jsonify([{
        "value": s["value"],
        "label": s["label"],
        "color": s["color"]
    } for s in status_options])

@app.route('/api/dropdown-options')
def get_dropdown_options():
    sources = db.get_source_config()
    board_types = db.get_board_type_config()
    status_options = db.get_status_config()
    
    return jsonify({
        "sources": [{"value": s["name"], "label": s["name"]} for s in sources],
        "types": [{"value": t["name"], "label": t["name"]} for t in board_types],
        "statuses": [{
            "value": s["value"],
            "label": s["label"],
            "color": s["color"]
        } for s in status_options]
    })

@app.route('/api/jobs')
@api_login_required
def get_jobs():
    """获取当前用户的项目列表"""
    user_projects = db.get_user_projects(session['user_id'])
    return jsonify(user_projects)

@app.route('/api/jobs/<int:job_id>')
@api_login_required
def get_job(job_id):
    """获取项目详情"""
    user_id = session['user_id']
    
    # 检查用户是否有访问权限
    access = db.check_project_access(job_id, user_id)
    if not access['access']:
        return jsonify({"error": "项目不存在或无访问权限"}), 404
    
    # 如果是项目所有者，直接获取项目
    if access['permission'] == 'owner':
        job = db.get_project_by_id(job_id, user_id)
    if job:
        return jsonify(job)
        return jsonify({"error": "项目不存在"}), 404
    
    # 如果是协作者，获取项目但不验证所有者
    job = db.get_project_by_id(job_id)
    if job:
        # 添加用户角色信息
        job['user_role'] = access['permission']
        # 如果是协作项目，获取项目所有者信息
        owner_info = db.get_user_by_id(job['user_id'])
        job['owner_username'] = owner_info['username'] if owner_info else '未知用户'
        return jsonify(job)
    
    return jsonify({"error": "项目不存在"}), 404

@app.route('/api/jobs', methods=['POST'])
@api_login_required
def create_job():
    
    try:
        data = request.get_json()
        required_fields = ['source', 'name', 'price', 'board_type', 'status']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"缺少必需字段: {field}"}), 400

        # 验证状态值是否有效
        status_options = db.get_status_config()
        valid_statuses = [s['value'] for s in status_options]
        if data['status'] not in valid_statuses:
            return jsonify({"error": "无效的状态值"}), 400

        # 创建项目
        project_id = db.create_project(session['user_id'], data)
        
        # 获取创建的项目详情
        new_project = db.get_project_by_id(project_id, session['user_id'])
        
        return jsonify({"message": "项目创建成功", "project": new_project}), 201
        
    except Exception as e:
        return jsonify({"error": f"创建项目失败: {str(e)}"}), 500

@app.route('/api/jobs/<int:job_id>', methods=['PUT'])
@api_login_required
def update_job(job_id):
    
    try:
        data = request.get_json()
        
        # 验证状态值是否有效
        if 'status' in data:
            status_options = db.get_status_config()
            valid_statuses = [s['value'] for s in status_options]
            if data['status'] not in valid_statuses:
                return jsonify({"error": "无效的状态值"}), 400

        # 更新项目
        success = db.update_project(job_id, session['user_id'], data)
        
        if not success:
            return jsonify({"error": "项目不存在或无访问权限"}), 404

        # 获取更新后的项目详情
        updated_project = db.get_project_by_id(job_id, session['user_id'])
        
        return jsonify({"message": "项目更新成功", "project": updated_project})
        
    except Exception as e:
        return jsonify({"error": f"更新项目失败: {str(e)}"}), 500

@app.route('/api/jobs/<int:job_id>', methods=['DELETE'])
@api_login_required
def delete_job(job_id):
    
    success = db.delete_project(job_id, session['user_id'])
    
    if success:
        return jsonify({"message": "项目删除成功"}), 200
    return jsonify({"error": "项目不存在或无访问权限"}), 404

@app.route('/api/job/components/<int:job_id>')
@api_login_required
def get_job_components(job_id):
    
    user_id = session['user_id']
    
    # 检查用户是否有访问权限（所有者或协作者都可以查看元件）
    access = db.check_project_access(job_id, user_id)
    if not access['access']:
        return jsonify({"error": "项目不存在或无访问权限"}), 404
    
    # 获取项目详情（不验证所有者）
    job = db.get_project_by_id(job_id)
    if job:
        total_price = sum(c.get('price', 0) * c.get('quantity', 0) for c in job['components'])
        return jsonify({
            "price": total_price,
            "components": job['components']
        })
    return jsonify({"error": "项目不存在"}), 404

@app.route('/api/job/requirements/<int:job_id>')
@api_login_required
def get_job_requirements(job_id):
    
    user_id = session['user_id']
    
    # 检查用户是否有访问权限（所有者或协作者都可以查看要求）
    access = db.check_project_access(job_id, user_id)
    if not access['access']:
        return jsonify({"error": "项目不存在或无访问权限"}), 404
    
    # 获取项目详情（不验证所有者）
    job = db.get_project_by_id(job_id)
    if job:
        return jsonify(job['requirements'])
    return jsonify({"error": "项目不存在"}), 404

@app.route('/api/user/stats')
@api_login_required
def get_user_stats():
    """获取用户统计信息"""
    stats = db.get_user_stats(session['user_id'])
    # 更新用户统计数据加载时间
    session['last_stats_time'] = get_beijing_time()
    return jsonify(stats)

@app.route('/api/upload/start', methods=['POST'])
@api_login_required
def start_upload():
    """开始一个新的上传会话"""

    data = request.get_json()
    project_id = data.get('project_id')
    total_files = data.get('total_files')
    
    if not project_id or not total_files:
        return jsonify({'error': '缺少必要参数'}), 400

    # 验证文件数量限制
    if total_files > app.config['MAX_FILES_PER_UPLOAD']:
        return jsonify({
            'error': f'超出文件数量限制，最多允许上传 {app.config["MAX_FILES_PER_UPLOAD"]} 个文件'
        }), 400

    # 查找项目信息 - 检查用户是否有访问权限
    user_id = session['user_id']
    access = db.check_project_access(project_id, user_id)
    
    if not access['access']:
        return jsonify({'error': '项目不存在或无访问权限'}), 404
    
    # 检查是否有写权限（项目所有者或有写权限的协作者）
    if access['permission'] not in ['owner', 'write']:
        return jsonify({'error': '您没有上传文件的权限，需要写权限'}), 403
    
    # 获取项目信息（不验证所有者）
    project = db.get_project_by_id(project_id)
    if not project:
        return jsonify({'error': '项目不存在'}), 404

    # 获取项目所有者信息来构建文件路径
    owner_info = db.get_user_by_id(project['user_id'])
    if not owner_info:
        return jsonify({'error': '项目所有者不存在'}), 404

    # 创建新的上传会话
    session_id = str(uuid.uuid4())
    username = session['username']
    owner_username = owner_info['username']
    project_folder = f"{owner_username}-{project['name']}"
    temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], owner_username, f"temp_{session_id}_{project_folder}")
    
    # 使用数据库存储上传会话
    db.create_upload_session(session_id, session['user_id'], project_id, temp_dir, total_files)

    return jsonify({
        'session_id': session_id,
        'message': '上传会话已创建'
    })

@app.route('/api/upload', methods=['POST'])
@api_login_required
def upload_files():

    if 'files[]' not in request.files:
        return jsonify({'error': '没有文件被上传'}), 400

    session_id = request.form.get('session_id')
    if not session_id:
        return jsonify({'error': '缺少会话ID'}), 400

    # 从数据库获取上传会话信息
    upload_info = db.get_upload_session(session_id)
    if not upload_info:
        return jsonify({'error': '无效的上传会话'}), 400

    if upload_info['user_id'] != session['user_id']:
        return jsonify({'error': '未授权的上传会话'}), 401

    files = request.files.getlist('files[]')
    temp_dir = upload_info['temp_dir']

    # 验证文件大小限制
    max_size_bytes = app.config['MAX_FILE_SIZE_MB'] * 1024 * 1024  # 转换为字节
    for file in files:
        if file.content_length and file.content_length > max_size_bytes:
            return jsonify({
                'error': f'文件 {file.filename} 超出大小限制 {app.config["MAX_FILE_SIZE_MB"]}MB'
            }), 400

    # 确保临时目录存在
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    uploaded_files = []
    try:
        for file in files:
            if file.filename:
                relative_path = file.filename.replace('\\', '/')
                target_path = os.path.join(temp_dir, relative_path)
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                file.save(target_path)
                
                # 保存后再次检查文件大小（更准确）
                file_size = os.path.getsize(target_path)
                if file_size > max_size_bytes:
                    os.remove(target_path)  # 删除超大文件
                    return jsonify({
                        'error': f'文件 {file.filename} 超出大小限制 {app.config["MAX_FILE_SIZE_MB"]}MB'
                    }), 400
                
                uploaded_files.append(relative_path)
                upload_info['file_list'].append(relative_path)

        # 更新已上传文件计数
        new_uploaded_count = upload_info['uploaded_files'] + len(uploaded_files)
        db.update_upload_session(session_id, new_uploaded_count, upload_info['file_list'])

        # 检查是否所有文件都已上传
        is_complete = new_uploaded_count >= upload_info['total_files']

        return jsonify({
            'message': f'成功上传 {len(uploaded_files)} 个文件',
            'files': uploaded_files,
            'uploaded_count': new_uploaded_count,
            'total_files': upload_info['total_files'],
            'is_complete': is_complete
        })

    except Exception as e:
        return jsonify({'error': f'上传失败: {str(e)}'}), 500

@app.route('/api/upload/complete', methods=['POST'])
@api_login_required
def complete_upload():
    """完成上传会话，移动文件到最终位置"""

    data = request.get_json()
    session_id = data.get('session_id')
    
    if not session_id:
        return jsonify({'error': '缺少会话ID'}), 400

    # 从数据库获取上传会话信息
    upload_info = db.get_upload_session(session_id)
    if not upload_info:
        return jsonify({'error': '无效的上传会话'}), 400

    if upload_info['user_id'] != session['user_id']:
        return jsonify({'error': '未授权的上传会话'}), 401

    # 检查是否所有文件都已上传
    if upload_info['uploaded_files'] < upload_info['total_files']:
        return jsonify({'error': '文件上传不完整'}), 400

    try:
        # 检查用户对项目的访问权限
        user_id = session['user_id']
        access = db.check_project_access(upload_info['project_id'], user_id)
        
        if not access['access']:
            return jsonify({'error': '项目不存在或无访问权限'}), 404
        
        # 检查是否有写权限
        if access['permission'] not in ['owner', 'write']:
            return jsonify({'error': '您没有上传文件的权限'}), 403
        
        # 获取项目信息（不验证所有者）
        project = db.get_project_by_id(upload_info['project_id'])
        if not project:
            return jsonify({'error': '项目不存在'}), 404

        # 获取项目所有者信息来构建文件路径
        owner_info = db.get_user_by_id(project['user_id'])
        if not owner_info:
            return jsonify({'error': '项目所有者不存在'}), 404

        # 构建最终目录路径 - 使用项目所有者的文件夹
        owner_username = owner_info['username']
        project_folder = f"{owner_username}-{project['name']}"
        final_dir = os.path.join(app.config['UPLOAD_FOLDER'], owner_username, project_folder)

        # 如果最终目录存在，则删除
        if os.path.exists(final_dir):
            shutil.rmtree(final_dir)

        # 将临时目录重命名为最终目录
        os.rename(upload_info['temp_dir'], final_dir)

        # 清理会话信息
        db.delete_upload_session(session_id)

        return jsonify({
            'message': '文件上传完成',
            'project_id': upload_info['project_id'],
            'total_files': upload_info['uploaded_files']
        })

    except Exception as e:
        return jsonify({'error': f'完成上传失败: {str(e)}'}), 500

def cleanup_expired_sessions():
    """清理过期的上传会话"""
    try:
        # 使用数据库清理过期会话
        db.cleanup_expired_upload_sessions(hours=24)
    except Exception as e:
        print(f"清理过期会话失败: {e}")

# 每次启动时清理一次过期会话
cleanup_expired_sessions()

@app.route('/api/files/<username>')
def list_user_files(username):
    """获取用户的所有文件夹"""
    user_dir = os.path.join(app.config['UPLOAD_FOLDER'], username)
    
    if not os.path.exists(user_dir):
        return jsonify({'folders': []})
    
    folders = []
    try:
        for item in os.listdir(user_dir):
            item_path = os.path.join(user_dir, item)
            if os.path.isdir(item_path) and not item.startswith('temp_'):
                folders.append({
                    'name': item,
                    'path': item_path,
                    'created': datetime.fromtimestamp(os.path.getctime(item_path), tz=timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
                })
    except Exception as e:
        return jsonify({'error': f'读取文件夹失败: {str(e)}'}), 500
    
    return jsonify({'folders': folders})

@app.route('/api/project/<int:project_id>/files')
@api_login_required
def get_project_files(project_id):
    """获取项目的文件目录结构"""

    user_id = session['user_id']
    
    # 检查用户是否有访问权限
    access = db.check_project_access(project_id, user_id)
    if not access['access']:
        return jsonify({'error': '项目不存在或无访问权限'}), 404

    # 获取项目信息（不验证所有者）
    project = db.get_project_by_id(project_id)
    if not project:
        return jsonify({'error': '项目不存在'}), 404

    # 获取项目所有者信息来构建文件路径
    owner_info = db.get_user_by_id(project['user_id'])
    if not owner_info:
        return jsonify({'error': '项目所有者不存在'}), 404
    
    owner_username = owner_info['username']
    project_folder = f"{owner_username}-{project['name']}"
    project_dir = os.path.join(app.config['UPLOAD_FOLDER'], owner_username, project_folder)

    def build_file_tree(directory_path, base_path=""):
        """递归构建文件树结构"""
        tree = {'folders': [], 'files': []}
        
        if not os.path.exists(directory_path):
            return tree

        try:
            items = sorted(os.listdir(directory_path))
            for item in items:
                item_path = os.path.join(directory_path, item)
                relative_path = os.path.join(base_path, item) if base_path else item
                
                if os.path.isdir(item_path):
                    # 文件夹
                    folder_info = {
                        'name': item,
                        'path': relative_path.replace('\\', '/'),
                        'type': 'folder',
                        'children': build_file_tree(item_path, relative_path)
                    }
                    tree['folders'].append(folder_info)
                else:
                    # 文件
                    file_size = os.path.getsize(item_path)
                    file_modified = datetime.fromtimestamp(os.path.getmtime(item_path), tz=timezone(timedelta(hours=8)))
                    
                    file_info = {
                        'name': item,
                        'path': relative_path.replace('\\', '/'),
                        'type': 'file',
                        'size': file_size,
                        'size_formatted': format_file_size(file_size),
                        'modified': file_modified.strftime('%Y-%m-%d %H:%M:%S'),
                        'extension': os.path.splitext(item)[1].lower()
                    }
                    tree['files'].append(file_info)
        except Exception as e:
            print(f"Error reading directory {directory_path}: {str(e)}")
        
        return tree

    def format_file_size(size_bytes):
        """格式化文件大小"""
        if size_bytes == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        return f"{size_bytes:.1f} {size_names[i]}"

    try:
        file_tree = build_file_tree(project_dir)
        return jsonify({
            'project_id': project_id,
            'project_name': project['name'],
            'tree': file_tree,
            'user_role': access['permission']  # 添加用户角色信息
        })
    except Exception as e:
        return jsonify({'error': f'获取文件列表失败: {str(e)}'}), 500

@app.route('/api/project/<int:project_id>/download/file')
def download_single_file(project_id):
    """下载单个文件"""
    try:
        if 'user_id' not in session:
            return jsonify({"error": "请先登录"}), 401
            
        user_id = session['user_id']
        
        # 检查用户是否有访问权限
        access = db.check_project_access(project_id, user_id)
        if not access['access']:
            return jsonify({"error": "项目不存在或无访问权限"}), 404
            
        file_path = request.args.get('path')
        if not file_path:
            return jsonify({"error": "缺少文件路径参数"}), 400
        
        # 获取项目信息（不验证所有者）
        project = db.get_project_by_id(project_id)
        if not project:
            return jsonify({"error": "项目不存在"}), 404
        
        # 获取项目所有者信息来构建文件路径
        owner_info = db.get_user_by_id(project['user_id'])
        if not owner_info:
            return jsonify({"error": "项目所有者不存在"}), 404
        
        # 构建完整文件路径 - 使用项目所有者的文件夹
        owner_username = owner_info['username']
        project_folder_name = f"{owner_username}-{project['name']}"
        project_folder = os.path.join(UPLOAD_FOLDER, owner_username, project_folder_name)
        full_file_path = os.path.join(project_folder, file_path.lstrip('/'))
        
        # 安全检查：确保文件路径在项目文件夹内
        if not os.path.abspath(full_file_path).startswith(os.path.abspath(project_folder)):
            return jsonify({"error": "非法的文件路径"}), 400
        
        if not os.path.exists(full_file_path):
            return jsonify({"error": "文件不存在"}), 404
        
        if not os.path.isfile(full_file_path):
            return jsonify({"error": "指定路径不是文件"}), 400
        
        # 获取文件名
        filename = os.path.basename(full_file_path)
        
        return send_file(
            full_file_path,
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/project/<int:project_id>/download/zip', methods=['POST'])
def download_zip(project_id):
    """下载压缩包"""
    try:
        if 'user_id' not in session:
            return jsonify({"error": "请先登录"}), 401
            
        user_id = session['user_id']
        
        # 检查用户是否有访问权限
        access = db.check_project_access(project_id, user_id)
        if not access['access']:
            return jsonify({"error": "项目不存在或无访问权限"}), 404
            
        data = request.get_json() if request.is_json else request.form
        file_paths = data.getlist('paths[]') if hasattr(data, 'getlist') else data.get('paths[]', [])
        
        if not file_paths:
            return jsonify({"error": "未选择要下载的文件"}), 400
        
        # 获取项目信息（不验证所有者）
        project = db.get_project_by_id(project_id)
        if not project:
            return jsonify({"error": "项目不存在"}), 404
        
        # 获取项目所有者信息来构建文件路径
        owner_info = db.get_user_by_id(project['user_id'])
        if not owner_info:
            return jsonify({"error": "项目所有者不存在"}), 404
        
        # 构建项目文件夹路径 - 使用项目所有者的文件夹
        owner_username = owner_info['username']
        project_folder_name = f"{owner_username}-{project['name']}"
        project_folder = os.path.join(UPLOAD_FOLDER, owner_username, project_folder_name)
        
        if not os.path.exists(project_folder):
            return jsonify({"error": "项目文件夹不存在"}), 404
        
        # 创建临时文件用于存储zip
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        temp_file.close()
        
        try:
            with zipfile.ZipFile(temp_file.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in file_paths:
                    full_path = os.path.join(project_folder, file_path.lstrip('/'))
                    
                    # 安全检查
                    if not os.path.abspath(full_path).startswith(os.path.abspath(project_folder)):
                        continue
                    
                    if os.path.isfile(full_path):
                        # 添加单个文件
                        zipf.write(full_path, file_path.lstrip('/'))
                    elif os.path.isdir(full_path):
                        # 添加整个文件夹
                        for root, dirs, files in os.walk(full_path):
                            for file in files:
                                file_full_path = os.path.join(root, file)
                                # 计算相对于项目文件夹的路径
                                relative_path = os.path.relpath(file_full_path, project_folder)
                                zipf.write(file_full_path, relative_path)
            
            # 生成zip文件名
            zip_filename = f"{project['name']}_files_{get_beijing_time().strftime('%Y%m%d_%H%M%S')}.zip"
            
            def remove_temp_file():
                try:
                    os.unlink(temp_file.name)
                except:
                    pass
            
            # 发送文件并在发送后删除临时文件
            @after_this_request
            def cleanup(response):
                remove_temp_file()
                return response
            
            return send_file(
                temp_file.name,
                as_attachment=True,
                download_name=zip_filename,
                mimetype='application/zip'
            )
            
        except Exception as e:
            # 清理临时文件
            try:
                os.unlink(temp_file.name)
            except:
                pass
            raise e
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/project/<int:project_id>/share', methods=['POST'])
def create_share(project_id):
    """创建项目分享链接"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': '请先登录'}), 401
        
        user_id = session['user_id']
        
        # 检查用户是否有访问权限（所有者或协作者都可以分享）
        access = db.check_project_access(project_id, user_id)
        if not access['access']:
            return jsonify({'error': '项目不存在或无访问权限'}), 404
        
        # 获取项目信息（不验证所有者）
        project = db.get_project_by_id(project_id)
        if not project:
            return jsonify({'error': '项目不存在'}), 404
        
        data = request.get_json()
        
        # 检查是否已经存在分享链接（使用项目ID检查，而不是用户ID，这样可以保持分享状态同步）
        existing_share = db.get_project_share_by_project_id(project_id)
        if existing_share:
            return jsonify({'error': '该项目已存在分享链接，请先取消分享'}), 400
        
        # 生成唯一的分享ID
        share_id = str(uuid.uuid4())
        
        # 处理过期时间
        expire_hours = data.get('expire_hours', 24)  # 默认24小时
        if expire_hours == -1:  # 永不过期
            expire_time = None
        else:
            expire_time = get_beijing_time() + timedelta(hours=expire_hours)
        
        # 处理密码
        password = data.get('password', '')
        password_hash = None
        if password:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # 处理访问次数限制
        max_access_count = data.get('max_access_count')
        if max_access_count is not None and max_access_count <= 0:
            max_access_count = None  # 0或负数表示无限制
        
        # 创建分享
        db.create_share(
            share_id=share_id,
            project_id=project_id,
            owner_id=project['user_id'],
            password_hash=password_hash,
            expire_time=expire_time.isoformat() if expire_time else None,
            max_access_count=max_access_count
        )
        
        # 构建分享链接
        share_url = f"/share/{share_id}"
        
        return jsonify({
            'message': '分享链接创建成功',
            'share_id': share_id,
            'share_url': share_url,
            'expire_time': expire_time.isoformat() if expire_time else None,
            'has_password': bool(password),
            'max_access_count': max_access_count
        })
        
    except Exception as e:
        return jsonify({'error': f'创建分享失败: {str(e)}'}), 500

@app.route('/api/project/<int:project_id>/share', methods=['DELETE'])
def cancel_share(project_id):
    """取消项目分享"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': '请先登录'}), 401
        
        user_id = session['user_id']
        
        # 检查用户是否有访问权限（所有者或协作者都可以取消分享）
        access = db.check_project_access(project_id, user_id)
        if not access['access']:
            return jsonify({'error': '项目不存在或无访问权限'}), 404
        
        # 查找并删除分享
        existing_share = db.get_project_share_by_project_id(project_id)
        if not existing_share:
            return jsonify({'error': '未找到该项目的分享链接'}), 404
        
        db.delete_share(existing_share['id'])
        
        return jsonify({'message': '分享已取消'})
        
    except Exception as e:
        return jsonify({'error': f'取消分享失败: {str(e)}'}), 500

@app.route('/api/project/<int:project_id>/share', methods=['GET'])
def get_share_info(project_id):
    """获取项目分享信息"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': '请先登录'}), 401
        
        user_id = session['user_id']
        
        # 检查用户是否有访问权限（所有者或协作者都可以查看分享信息）
        access = db.check_project_access(project_id, user_id)
        if not access['access']:
            return jsonify({'error': '项目不存在或无访问权限'}), 404
        
        # 查找分享信息
        share_info = db.get_project_share_by_project_id(project_id)
        if not share_info:
            response = jsonify({'shared': False})
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
        
        # 检查是否过期
        if share_info['expire_time']:
            expire_time = datetime.fromisoformat(share_info['expire_time'])
            # 使用相同时区感知的datetime进行比较
            current_time = get_beijing_time()
            if current_time > expire_time:
                db.delete_share(share_info['id'])
                response = jsonify({'shared': False})
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
                return response
        
        response_data = {
            'shared': True,
            'share_id': share_info['id'],
            'share_url': f"/share/{share_info['id']}",
            'expire_time': share_info['expire_time'],
            'has_password': bool(share_info['password_hash']),
            'access_count': share_info.get('access_count', 0),
            'max_access_count': share_info.get('max_access_count'),
            'created_at': share_info['created_at']
        }
        
        response = jsonify(response_data)
        # 添加缓存控制头，防止缓存
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache' 
        response.headers['Expires'] = '0'
        return response
        
    except Exception as e:
        return jsonify({'error': f'获取分享信息失败: {str(e)}'}), 500

@app.route('/share/<share_id>')
def share_page(share_id):
    """分享页面"""
    # 检查分享是否存在
    share_info = db.get_share_by_id(share_id)
    if not share_info:
        return render_template('share_error.html', error='分享链接不存在或已失效')
    
    # 检查是否过期
    if share_info['expire_time']:
        expire_time = beijing_time_from_iso(share_info['expire_time'])
        if get_beijing_time() > expire_time:
            db.delete_share(share_id)
            return render_template('share_error.html', error='分享链接已过期')
    
    # 检查访问次数限制
    if share_info.get('max_access_count') and share_info.get('access_count', 0) >= share_info['max_access_count']:
        return render_template('share_error.html', error='分享链接访问次数已达上限')
    
    # 如果有密码保护，显示密码输入页面
    if share_info['password_hash'] and not session.get(f'share_verified_{share_id}'):
        return render_template('share_password.html', 
                             share_id=share_id, 
                             project_name=share_info['project_name'])
    
    # 增加访问计数（只在实际访问时计数，不在密码验证页面计数）
    db.increment_share_access_count(share_id)
    
    return render_template('share_download.html', 
                         share_info=share_info)

@app.route('/share/<share_id>/verify', methods=['POST'])
def verify_share_password(share_id):
    """验证分享密码"""
    share_info = db.get_share_by_id(share_id)
    if not share_info:
        return jsonify({'error': '分享链接不存在或已失效'}), 404
    
    password = request.form.get('password', '')
    
    if not share_info['password_hash']:
        return jsonify({'error': '该分享无需密码'}), 400
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    if password_hash == share_info['password_hash']:
        session[f'share_verified_{share_id}'] = True
        return redirect(f'/share/{share_id}')
    else:
        return render_template('share_password.html', 
                             share_id=share_id, 
                             project_name=share_info['project_name'],
                             error='密码错误')

@app.route('/api/share/<share_id>/files')
def get_share_files(share_id):
    """获取分享的文件列表"""
    try:
        # 检查分享是否存在和有效
        share_info = db.get_share_by_id(share_id)
        if not share_info:
            return jsonify({'error': '分享链接不存在或已失效'}), 404
        
        # 检查是否过期
        if share_info['expire_time']:
            expire_time = beijing_time_from_iso(share_info['expire_time'])
            if get_beijing_time() > expire_time:
                db.delete_share(share_id)
                return jsonify({'error': '分享链接已过期'}), 404
        
        # 检查密码验证
        if share_info['password_hash'] and not session.get(f'share_verified_{share_id}'):
            return jsonify({'error': '需要密码验证'}), 401
            
        # 构建项目文件夹路径
        owner_username = share_info['owner_username']
        project_name = share_info['project_name']
        project_folder_name = f"{owner_username}-{project_name}"
        project_dir = os.path.join(UPLOAD_FOLDER, owner_username, project_folder_name)

        def build_file_tree(directory_path, base_path=""):
            """递归构建文件树结构"""
            tree = {'folders': [], 'files': []}
            
            if not os.path.exists(directory_path):
                return tree

            try:
                items = sorted(os.listdir(directory_path))
                for item in items:
                    item_path = os.path.join(directory_path, item)
                    relative_path = os.path.join(base_path, item) if base_path else item
                    
                    if os.path.isdir(item_path):
                        # 文件夹
                        folder_info = {
                            'name': item,
                            'path': relative_path.replace('\\', '/'),
                            'type': 'folder',
                            'children': build_file_tree(item_path, relative_path)
                        }
                        tree['folders'].append(folder_info)
                    else:
                        # 文件
                        file_size = os.path.getsize(item_path)
                        file_modified = datetime.fromtimestamp(os.path.getmtime(item_path), tz=timezone(timedelta(hours=8)))
                        
                        file_info = {
                            'name': item,
                            'path': relative_path.replace('\\', '/'),
                            'type': 'file',
                            'size': file_size,
                            'size_formatted': format_file_size(file_size),
                            'modified': file_modified.strftime('%Y-%m-%d %H:%M:%S'),
                            'extension': os.path.splitext(item)[1].lower()
                        }
                        tree['files'].append(file_info)
            except Exception as e:
                print(f"Error reading directory {directory_path}: {str(e)}")
            
            return tree

        def format_file_size(size_bytes):
            """格式化文件大小"""
            if size_bytes == 0:
                return "0 B"
            size_names = ["B", "KB", "MB", "GB"]
            i = 0
            while size_bytes >= 1024 and i < len(size_names) - 1:
                size_bytes /= 1024.0
                i += 1
            return f"{size_bytes:.1f} {size_names[i]}"

        file_tree = build_file_tree(project_dir)
        return jsonify({
            'share_id': share_id,
            'project_name': share_info['project_name'],
            'tree': file_tree
        })
        
    except Exception as e:
        return jsonify({'error': f'获取文件列表失败: {str(e)}'}), 500

@app.route('/api/share/<share_id>/download/file')
def download_share_file(share_id):
    """下载分享的单个文件"""
    try:
        # 检查分享是否存在和有效
        share_info = db.get_share_by_id(share_id)
        if not share_info:
            return jsonify({"error": "分享链接不存在或已失效"}), 404
        
        # 检查是否过期
        if share_info['expire_time']:
            expire_time = beijing_time_from_iso(share_info['expire_time'])
            if get_beijing_time() > expire_time:
                db.delete_share(share_id)
                return jsonify({"error": "分享链接已过期"}), 404
        
        # 检查密码验证
        if share_info['password_hash'] and not session.get(f'share_verified_{share_id}'):
            return jsonify({"error": "需要密码验证"}), 401
            
        file_path = request.args.get('path')
        if not file_path:
            return jsonify({"error": "缺少文件路径参数"}), 400
        
        # 构建完整文件路径
        owner_username = share_info['owner_username']
        project_name = share_info['project_name']
        project_folder_name = f"{owner_username}-{project_name}"
        project_folder = os.path.join(UPLOAD_FOLDER, owner_username, project_folder_name)
        full_file_path = os.path.join(project_folder, file_path.lstrip('/'))
        
        # 安全检查：确保文件路径在项目文件夹内
        if not os.path.abspath(full_file_path).startswith(os.path.abspath(project_folder)):
            return jsonify({"error": "非法的文件路径"}), 400
        
        if not os.path.exists(full_file_path):
            return jsonify({"error": "文件不存在"}), 404
        
        if not os.path.isfile(full_file_path):
            return jsonify({"error": "指定路径不是文件"}), 400
        
        # 获取文件名
        filename = os.path.basename(full_file_path)
        
        return send_file(
            full_file_path,
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/share/<share_id>/download/zip', methods=['POST'])
def download_share_zip(share_id):
    """下载分享的压缩包"""
    try:
        # 检查分享是否存在和有效
        share_info = db.get_share_by_id(share_id)
        if not share_info:
            return jsonify({"error": "分享链接不存在或已失效"}), 404
        
        # 检查是否过期
        if share_info['expire_time']:
            expire_time = beijing_time_from_iso(share_info['expire_time'])
            if get_beijing_time() > expire_time:
                db.delete_share(share_id)
                return jsonify({"error": "分享链接已过期"}), 404
        
        # 检查密码验证
        if share_info['password_hash'] and not session.get(f'share_verified_{share_id}'):
            return jsonify({"error": "需要密码验证"}), 401
            
        data = request.get_json() if request.is_json else request.form
        file_paths = data.getlist('paths[]') if hasattr(data, 'getlist') else data.get('paths[]', [])
        
        if not file_paths:
            return jsonify({"error": "未选择要下载的文件"}), 400
        
        # 构建项目文件夹路径
        owner_username = share_info['owner_username']
        project_name = share_info['project_name']
        project_folder_name = f"{owner_username}-{project_name}"
        project_folder = os.path.join(UPLOAD_FOLDER, owner_username, project_folder_name)
        
        if not os.path.exists(project_folder):
            return jsonify({"error": "项目文件夹不存在"}), 404
        
        # 创建临时文件用于存储zip
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        temp_file.close()
        
        try:
            # 创建zip文件
            with zipfile.ZipFile(temp_file.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in file_paths:
                    full_path = os.path.join(project_folder, file_path.lstrip('/'))
                    
                    # 安全检查
                    if not os.path.abspath(full_path).startswith(os.path.abspath(project_folder)):
                        continue
                    
                    if os.path.exists(full_path):
                        if os.path.isfile(full_path):
                            # 添加文件
                            zipf.write(full_path, file_path)
                        elif os.path.isdir(full_path):
                            # 添加文件夹及其所有内容
                            for root, dirs, files in os.walk(full_path):
                                for file in files:
                                    file_full_path = os.path.join(root, file)
                                    # 计算相对于项目文件夹的路径
                                    rel_path = os.path.relpath(file_full_path, project_folder)
                                    zipf.write(file_full_path, rel_path)
            
            # 生成下载文件名
            download_name = f"{project_name}_files_{get_beijing_time().strftime('%Y%m%d_%H%M%S')}.zip"
            
            return send_file(
                temp_file.name,
                as_attachment=True,
                download_name=download_name,
                mimetype='application/zip'
            )
            
        except Exception as e:
            # 清理临时文件
            try:
                os.unlink(temp_file.name)
            except:
                pass
            raise e
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== 管理员用户管理API ====================

@app.route('/api/admin/stats')
@api_admin_required
def admin_get_stats():
    """获取系统统计信息"""
    stats = db.get_user_stats_admin()
    return jsonify(stats)

@app.route('/api/admin/users')
@api_admin_required
def admin_get_users():
    """获取所有用户列表"""
    users = db.get_all_users()
    return jsonify(users)

@app.route('/api/admin/users', methods=['POST'])
@api_admin_required
def admin_create_user():
    """创建新用户"""
    
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        is_admin = data.get('is_admin', False)
        
        if not username or not password:
            return jsonify({'error': '用户名和密码不能为空'}), 400
        
        if len(username) < 3:
            return jsonify({'error': '用户名至少需要3个字符'}), 400
        
        if len(password) < 3:
            return jsonify({'error': '密码至少需要3个字符'}), 400
        
        user_id, message = db.create_user(username, password, is_admin)
        
        if user_id:
            return jsonify({'message': message, 'user_id': user_id}), 201
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        return jsonify({'error': f'创建用户失败: {str(e)}'}), 500

@app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
@api_admin_required
def admin_update_user(user_id):
    """更新用户信息"""
    
    try:
        data = request.get_json()
        username = data.get('username', '').strip() if data.get('username') else None
        password = data.get('password', '').strip() if data.get('password') else None
        is_admin = data.get('is_admin') if 'is_admin' in data else None
        
        # 验证输入
        if username is not None and len(username) < 3:
            return jsonify({'error': '用户名至少需要3个字符'}), 400
        
        if password is not None and len(password) < 3:
            return jsonify({'error': '密码至少需要3个字符'}), 400
        
        # 防止管理员删除自己的管理员权限
        if user_id == session.get('admin_user_id') and is_admin is False:
            return jsonify({'error': '不能移除自己的管理员权限'}), 400
        
        success, message = db.update_user(user_id, username, password, is_admin)
        
        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        return jsonify({'error': f'更新用户失败: {str(e)}'}), 500

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@api_admin_required
def admin_delete_user(user_id):
    """删除用户"""
    
    # 防止管理员删除自己
    if user_id == session.get('admin_user_id'):
        return jsonify({'error': '不能删除自己的账户'}), 400
    
    try:
        success, message = db.delete_user(user_id)
        
        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        return jsonify({'error': f'删除用户失败: {str(e)}'}), 500

# ==================== 管理员配置管理API ====================

@app.route('/api/admin/config/status')
@api_admin_required
def admin_get_status_config():
    """获取项目状态配置"""
    
    config = db.get_status_config()
    return jsonify(config)

@app.route('/api/admin/config/status', methods=['POST'])
@api_admin_required
def admin_add_status_config():
    """添加项目状态配置"""
    
    try:
        data = request.get_json()
        value = data.get('value', '').strip()
        label = data.get('label', '').strip()
        color = data.get('color', '').strip()
        sort_order = data.get('sort_order', 0)
        
        if not value or not label or not color:
            return jsonify({'error': '值、标签和颜色不能为空'}), 400
        
        success, message = db.add_status_config(value, label, color, sort_order)
        
        if success:
            return jsonify({'message': message}), 201
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        return jsonify({'error': f'添加状态配置失败: {str(e)}'}), 500

@app.route('/api/admin/config/status/<int:config_id>', methods=['PUT'])
def admin_update_status_config(config_id):
    """更新项目状态配置"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': '管理员权限不足'}), 403
    
    try:
        data = request.get_json()
        value = data.get('value', '').strip()
        label = data.get('label', '').strip()
        color = data.get('color', '').strip()
        sort_order = data.get('sort_order', 0)
        
        if not value or not label or not color:
            return jsonify({'error': '值、标签和颜色不能为空'}), 400
        
        success, message = db.update_status_config(config_id, value, label, color, sort_order)
        
        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        return jsonify({'error': f'更新状态配置失败: {str(e)}'}), 500

@app.route('/api/admin/config/status/<int:config_id>', methods=['DELETE'])
def admin_delete_status_config(config_id):
    """删除项目状态配置"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': '管理员权限不足'}), 403
    
    try:
        success, message = db.delete_status_config(config_id)
        
        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        return jsonify({'error': f'删除状态配置失败: {str(e)}'}), 500

@app.route('/api/admin/config/source')
def admin_get_source_config():
    """获取项目来源配置"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': '管理员权限不足'}), 403
    
    config = db.get_source_config()
    return jsonify(config)

@app.route('/api/admin/config/source', methods=['POST'])
def admin_add_source_config():
    """添加项目来源配置"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': '管理员权限不足'}), 403
    
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        sort_order = data.get('sort_order', 0)
        
        if not name:
            return jsonify({'error': '名称不能为空'}), 400
        
        success, message = db.add_source_config(name, sort_order)
        
        if success:
            return jsonify({'message': message}), 201
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        return jsonify({'error': f'添加来源配置失败: {str(e)}'}), 500

@app.route('/api/admin/config/source/<int:config_id>', methods=['PUT'])
def admin_update_source_config(config_id):
    """更新项目来源配置"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': '管理员权限不足'}), 403
    
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        sort_order = data.get('sort_order', 0)
        
        if not name:
            return jsonify({'error': '名称不能为空'}), 400
        
        success, message = db.update_source_config(config_id, name, sort_order)
        
        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        return jsonify({'error': f'更新来源配置失败: {str(e)}'}), 500

@app.route('/api/admin/config/source/<int:config_id>', methods=['DELETE'])
def admin_delete_source_config(config_id):
    """删除项目来源配置"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': '管理员权限不足'}), 403
    
    try:
        success, message = db.delete_source_config(config_id)
        
        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        return jsonify({'error': f'删除来源配置失败: {str(e)}'}), 500

@app.route('/api/admin/config/board-type')
def admin_get_board_type_config():
    """获取电路板类型配置"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': '管理员权限不足'}), 403
    
    config = db.get_board_type_config()
    return jsonify(config)

@app.route('/api/admin/config/board-type', methods=['POST'])
def admin_add_board_type_config():
    """添加电路板类型配置"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': '管理员权限不足'}), 403
    
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        sort_order = data.get('sort_order', 0)
        
        if not name:
            return jsonify({'error': '名称不能为空'}), 400
        
        success, message = db.add_board_type_config(name, sort_order)
        
        if success:
            return jsonify({'message': message}), 201
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        return jsonify({'error': f'添加电路板类型配置失败: {str(e)}'}), 500

@app.route('/api/admin/config/board-type/<int:config_id>', methods=['PUT'])
def admin_update_board_type_config(config_id):
    """更新电路板类型配置"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': '管理员权限不足'}), 403
    
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        sort_order = data.get('sort_order', 0)
        
        if not name:
            return jsonify({'error': '名称不能为空'}), 400
        
        success, message = db.update_board_type_config(config_id, name, sort_order)
        
        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        return jsonify({'error': f'更新电路板类型配置失败: {str(e)}'}), 500

@app.route('/api/admin/config/board-type/<int:config_id>', methods=['DELETE'])
def admin_delete_board_type_config(config_id):
    """删除电路板类型配置"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': '管理员权限不足'}), 403
    
    try:
        success, message = db.delete_board_type_config(config_id)
        
        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        return jsonify({'error': f'删除电路板类型配置失败: {str(e)}'}), 500

@app.route('/api/admin/config/component', methods=['POST'])
def admin_add_component():
    """添加元器件"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': '管理员权限不足'}), 403
    
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        model = data.get('model', '').strip()
        price = data.get('price', 0)
        
        if not name or not model:
            return jsonify({'error': '名称和型号不能为空'}), 400
        
        if price < 0:
            return jsonify({'error': '价格不能为负数'}), 400
        
        success, message = db.add_component(name, model, price)
        
        if success:
            return jsonify({'message': message}), 201
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        return jsonify({'error': f'添加元器件失败: {str(e)}'}), 500

@app.route('/api/admin/config/component/<int:component_id>', methods=['PUT'])
def admin_update_component(component_id):
    """更新元器件"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': '管理员权限不足'}), 403
    
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        model = data.get('model', '').strip()
        price = data.get('price', 0)
        
        if not name or not model:
            return jsonify({'error': '名称和型号不能为空'}), 400
        
        if price < 0:
            return jsonify({'error': '价格不能为负数'}), 400
        
        success, message = db.update_component(component_id, name, model, price)
        
        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        return jsonify({'error': f'更新元器件失败: {str(e)}'}), 500

@app.route('/api/admin/config/component/<int:component_id>', methods=['DELETE'])
def admin_delete_component(component_id):
    """删除元器件"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': '管理员权限不足'}), 403
    
    try:
        success, message = db.delete_component(component_id)
        
        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        return jsonify({'error': f'删除元器件失败: {str(e)}'}), 500

# ============= 项目协作相关路由 =============

@app.route('/api/project/<int:project_id>/collaborations')
def get_project_collaborations_api(project_id):
    """获取项目协作者列表"""
    if not session.get('user_id'):
        return jsonify({'error': '请先登录'}), 401
    
    user_id = session.get('user_id')
    
    try:
        collaborations = db.get_project_collaborations(project_id, user_id)
        return jsonify(collaborations)
    except ValueError as e:
        return jsonify({'error': str(e)}), 403
    except Exception as e:
        return jsonify({'error': f'获取协作者列表失败: {str(e)}'}), 500

@app.route('/api/project/<int:project_id>/collaborations', methods=['POST'])
def add_project_collaboration_api(project_id):
    """添加项目协作者"""
    if not session.get('user_id'):
        return jsonify({'error': '请先登录'}), 401
    
    user_id = session.get('user_id')
    
    try:
        data = request.get_json()
        collaborator_id = data.get('collaborator_id')
        permission = data.get('permission', 'read')
        
        if not collaborator_id:
            return jsonify({'error': '请选择协作者'}), 400
        
        if permission not in ['read', 'write']:
            return jsonify({'error': '权限类型无效'}), 400
        
        collaboration_id = db.add_project_collaboration(project_id, user_id, collaborator_id, permission)
        return jsonify({'message': '协作者添加成功', 'collaboration_id': collaboration_id}), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'添加协作者失败: {str(e)}'}), 500

@app.route('/api/project/<int:project_id>/collaborations/<int:collaborator_id>', methods=['DELETE'])
def remove_project_collaboration_api(project_id, collaborator_id):
    """移除项目协作者"""
    if not session.get('user_id'):
        return jsonify({'error': '请先登录'}), 401
    
    user_id = session.get('user_id')
    
    try:
        db.remove_project_collaboration(project_id, user_id, collaborator_id)
        return jsonify({'message': '协作者移除成功'}), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'移除协作者失败: {str(e)}'}), 500

@app.route('/api/project/<int:project_id>/collaboration/leave', methods=['DELETE'])
def leave_project_collaboration_api(project_id):
    """协作者主动退出项目协作"""
    if not session.get('user_id'):
        return jsonify({'error': '请先登录'}), 401
    
    user_id = session.get('user_id')
    
    try:
        # 检查用户是否确实是该项目的协作者
        access_info = db.check_project_access(project_id, user_id)
        if not access_info['access'] or access_info['permission'] == 'owner':
            return jsonify({'error': '您不是此项目的协作者或您是项目所有者'}), 403
        
        # 执行退出操作（协作者自己退出，所以owner_id设为None）
        db.remove_project_collaboration(project_id, None, user_id)
        return jsonify({'message': '成功退出项目协作'}), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'退出协作失败: {str(e)}'}), 500

@app.route('/api/project/collaborations/<int:collaboration_id>/permission', methods=['PUT'])
def update_collaboration_permission_api(collaboration_id):
    """更新协作者权限"""
    if not session.get('user_id'):
        return jsonify({'error': '请先登录'}), 401
    
    user_id = session.get('user_id')
    
    try:
        data = request.get_json()
        permission = data.get('permission')
        
        if permission not in ['read', 'write']:
            return jsonify({'error': '权限类型无效'}), 400
        
        db.update_collaboration_permission(collaboration_id, user_id, permission)
        return jsonify({'message': '权限更新成功'}), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'更新权限失败: {str(e)}'}), 500

@app.route('/api/available-collaborators')
def get_available_collaborators_api():
    """获取可添加为协作者的用户列表"""
    if not session.get('user_id'):
        return jsonify({'error': '请先登录'}), 401
    
    user_id = session.get('user_id')
    
    try:
        users = db.get_available_collaborators(user_id)
        return jsonify(users)
    except Exception as e:
        return jsonify({'error': f'获取用户列表失败: {str(e)}'}), 500

@app.route('/api/collaborated-projects')
def get_collaborated_projects_api():
    """获取用户参与协作的项目列表"""
    if not session.get('user_id'):
        return jsonify({'error': '请先登录'}), 401
    
    user_id = session.get('user_id')
    
    try:
        projects = db.get_user_collaborated_projects(user_id)
        return jsonify(projects)
    except Exception as e:
        return jsonify({'error': f'获取协作项目失败: {str(e)}'}), 500

@app.route('/api/user/settings')
@api_login_required
def get_user_settings_api():
    """获取用户设置"""
    try:
        settings = db.get_user_settings(session['user_id'])
        return jsonify(settings)
    except Exception as e:
        return jsonify({"error": f"获取用户设置失败: {str(e)}"}), 500

@app.route('/api/user/settings', methods=['PUT'])
@api_login_required
def update_user_settings_api():
    """更新用户设置"""
    try:
        data = request.get_json()
        hide_prices = data.get('hide_prices')
        
        success = db.update_user_settings(session['user_id'], hide_prices=hide_prices)
        if success:
            return jsonify({"message": "设置更新成功"})
        else:
            return jsonify({"error": "设置更新失败"}), 500
            
    except Exception as e:
        return jsonify({"error": f"更新用户设置失败: {str(e)}"}), 500

# ============= 统计数据更新通知相关路由 =============

@app.route('/api/admin/notify-stats-update', methods=['POST'])
@api_admin_required
def notify_stats_update():
    """管理员修改元器件价格后，通知所有用户刷新统计数据"""
    try:
        # 更新全局统计数据更新时间戳
        app.config['STATS_UPDATE_TIME'] = get_beijing_time()
        return jsonify({"message": "统计数据更新通知已发送"}), 200
    except Exception as e:
        return jsonify({"error": f"发送更新通知失败: {str(e)}"}), 500

@app.route('/api/stats-update-check')
@api_login_required
def check_stats_update():
    """检查统计数据是否需要更新"""
    try:
        # 从session中获取用户上次加载统计数据的时间
        last_stats_time = session.get('last_stats_time')
        current_update_time = app.config.get('STATS_UPDATE_TIME')
        
        needs_update = False
        if current_update_time and last_stats_time:
            # 如果全局更新时间晚于用户的统计数据时间，则需要更新
            if current_update_time > last_stats_time:
                needs_update = True
        elif current_update_time:
            # 如果用户没有统计数据时间记录，但有全局更新时间，则需要更新
            needs_update = True
        
        return jsonify({
            "needs_update": needs_update,
            "update_time": current_update_time.isoformat() if current_update_time else None
        }), 200
    except Exception as e:
        return jsonify({"error": f"检查统计数据更新失败: {str(e)}"}), 500

if __name__ == '__main__':
    # 确保数据库已初始化
    db.init_database()
    app.run(host='0.0.0.0', port=5000, debug=True)