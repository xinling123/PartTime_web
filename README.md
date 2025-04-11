# 兼职项目管理系统

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)
![SQLite](https://img.shields.io/badge/SQLite-3-orange.svg)
![License](https://img.shields.io/badge/license-MIT-brightgreen.svg)

一个功能完善的兼职项目管理系统，基于 Flask 构建的 Web 应用

[功能特性](#功能特性) •
[快速开始](#快速开始) •
[使用指南](#使用指南) •
[技术栈](#技术栈) •
[系统架构](#系统架构)

</div>

---

## 📖 项目简介

PartTime_web 是一个专为兼职项目管理设计的 Web 应用系统，提供完整的项目生命周期管理、团队协作、文件共享等功能。系统采用前后端一体化架构，界面美观现代，操作流畅便捷。

### 🎯 适用场景

- 电子工程团队的兼职项目管理
- 多人协作的硬件开发项目
- 设计文件的版本管理与共享
- 元器件清单和成本核算
- 项目进度跟踪和状态管理

---

## ✨ 功能特性

### 🔐 用户管理

- **双角色系统**：支持普通用户和管理员两种角色
- **安全登录**：密码 SHA-256 加密存储
- **会话管理**：支持 2 小时自动过期，保障账户安全
- **个性化设置**：支持价格隐藏等个性化配置

### 📋 项目管理

- **完整的 CRUD 操作**：创建、读取、更新、删除项目
- **项目分类**：支持多种项目来源（客户委托、内部项目、研发项目等）
- **状态跟踪**：进行中、已完成、审核中、已暂停、已取消等多种状态
- **电路板类型**：单层板、双层板、多层板、柔性板分类管理
- **需求管理**：为项目添加多条需求说明，支持自定义颜色标签
- **备注功能**：详细记录项目相关信息

### 🔧 元器件管理

- **元器件库**：集中管理常用电子元器件
- **价格计算**：自动计算元器件总成本
- **数量跟踪**：记录每个项目使用的元器件数量
- **组件详情**：包含名称、型号、单价等完整信息

### 📁 文件管理

- **文件上传**：支持多文件批量上传（最多 10 个文件）
- **文件大小限制**：单文件最大 300MB
- **目录结构**：自动组织项目文件，支持文件夹层级
- **文件下载**：支持单文件下载和多选文件打包下载
- **断点续传**：采用会话机制，支持大文件上传

### 🔗 分享功能

- **灵活的分享设置**：
  - 密码保护（可选）
  - 过期时间设置（支持永久有效）
  - 访问次数限制
- **分享链接管理**：一键生成/取消分享链接
- **访问统计**：记录分享链接的访问次数
- **安全机制**：访客仅可下载，不可修改项目

### 👥 协作功能

- **多人协作**：支持添加协作者共同管理项目
- **权限管理**：
  - **只读权限**：仅可查看项目内容
  - **读写权限**：可以上传文件和修改项目信息
- **协作者管理**：项目所有者可随时添加/移除协作者
- **权限切换**：灵活调整协作者的访问权限

### 📊 统计分析

- **项目统计**：
  - 总项目数
  - 未完成项目数
  - 项目总价
  - 未完成项目总价
  - 元器件总成本
- **实时更新**：数据自动刷新，保持最新状态

### ⚙️ 管理员后台

- **用户管理**：
  - 创建、编辑、删除用户
  - 设置管理员权限
  - 密码重置
- **系统配置**：
  - 项目状态配置（自定义状态及颜色）
  - 项目来源配置
  - 电路板类型配置
  - 元器件管理
- **数据统计**：查看系统整体数据和使用情况

---

## 🚀 快速开始

### 环境要求

- Python 3.8 或更高版本
- pip 包管理器
- 现代浏览器（Chrome、Firefox、Edge、Safari）

### 安装步骤

1. **克隆项目**

```bash
git clone https://github.com/your-username/PartTime_web.git
cd PartTime_web
```

2. **安装依赖**

```bash
pip install -r requirements.txt
```

主要依赖包：
- Flask: Web 框架
- Werkzeug: WSGI 工具库

3. **初始化数据库**

首次运行时会自动创建数据库和初始数据：

```bash
python main.py
```

4. **访问系统**

打开浏览器访问：`http://localhost:5000`

### 默认账户

系统初始化时会创建以下测试账户：

| 用户名 | 密码 | 角色 | 说明 |
|--------|------|------|------|
| admin  | admin | 管理员 | 拥有所有权限 |
| user1  | user1 | 普通用户 | 包含示例项目 |
| user2  | user2 | 普通用户 | 空白账户 |

> ⚠️ **安全提示**：生产环境部署前请务必修改默认密码！

---

## 📖 使用指南

### 普通用户操作流程

#### 1. 登录系统
- 访问首页，使用用户名和密码登录
- 登录后自动跳转到项目管理面板

#### 2. 创建项目
1. 点击「新建项目」按钮
2. 填写项目基本信息：
   - 项目名称
   - 项目来源
   - 电路板类型
   - 项目状态
   - 项目价格
   - 备注信息
3. 添加元器件（可选）
4. 添加项目需求（可选）
5. 保存项目

#### 3. 上传文件
1. 在项目列表中点击项目卡片
2. 点击「上传文件」按钮
3. 选择文件或拖拽文件到上传区域
4. 等待上传完成

#### 4. 分享项目
1. 打开项目详情
2. 点击「分享」按钮
3. 配置分享选项：
   - 设置访问密码（可选）
   - 设置过期时间
   - 设置访问次数限制
4. 生成分享链接
5. 将链接分享给其他人

#### 5. 添加协作者
1. 打开项目详情
2. 切换到「协作」标签
3. 选择要添加的用户
4. 设置权限（只读/读写）
5. 发送邀请

### 管理员操作

#### 用户管理
- **创建用户**：后台 → 用户管理 → 新建用户
- **编辑用户**：修改用户名、密码、权限
- **删除用户**：删除用户及其所有数据

#### 系统配置
- **状态管理**：自定义项目状态及显示颜色
- **来源管理**：配置项目来源选项
- **类型管理**：管理电路板类型
- **元器件库**：维护元器件数据

---

## 🛠 技术栈

### 后端技术

- **Web 框架**：Flask 3.0+
- **数据库**：SQLite 3
- **密码加密**：hashlib (SHA-256)
- **文件处理**：Werkzeug
- **会话管理**：Flask Session

### 前端技术

- **HTML5** + **CSS3**
- **JavaScript (ES6+)**
- **Bootstrap 5**：响应式 UI 框架
- **Font Awesome**：图标库
- **AJAX**：异步数据交互

### 安全特性

- 密码 SHA-256 加密存储
- Session 防止 CSRF 攻击
- SQL 注入防护（参数化查询）
- 文件上传安全检查
- 路径遍历攻击防护

---

## 📂 系统架构

### 目录结构

```
PartTime_web/
├── main.py                 # Flask 应用主文件
├── database.py             # 数据库操作模块
├── requirements.txt        # Python 依赖包
├── pcb_management.db      # SQLite 数据库文件（自动生成）
├── README.md              # 项目说明文档
│
├── static/                # 静态资源目录
│   └── js/
│       └── collaboration.js  # 协作功能 JS
│
├── templates/             # HTML 模板目录
│   ├── index.html            # 登录页面
│   ├── dashboard.html        # 用户主页
│   ├── admin_login.html      # 管理员登录
│   ├── admin_dashboard.html  # 管理员后台
│   ├── share_download.html   # 分享下载页
│   ├── share_password.html   # 分享密码验证
│   ├── share_error.html      # 分享错误页
│   ├── add_modal.html        # 新建项目模态框
│   └── upload_modal.html     # 文件上传模态框
│
└── uploads/               # 文件上传目录
    └── [username]/        # 按用户名分类
        └── [username-projectname]/  # 项目文件夹
```

### API 接口

#### 项目相关
- `GET /api/jobs` - 获取项目列表
- `GET /api/jobs/<id>` - 获取项目详情
- `POST /api/jobs` - 创建项目
- `PUT /api/jobs/<id>` - 更新项目
- `DELETE /api/jobs/<id>` - 删除项目

#### 文件管理
- `POST /api/upload/start` - 开始上传会话
- `POST /api/upload` - 上传文件
- `POST /api/upload/complete` - 完成上传
- `GET /api/project/<id>/files` - 获取项目文件列表
- `GET /api/project/<id>/download/file` - 下载单个文件
- `POST /api/project/<id>/download/zip` - 下载压缩包

#### 分享功能
- `POST /api/project/<id>/share` - 创建分享
- `GET /api/project/<id>/share` - 获取分享信息
- `DELETE /api/project/<id>/share` - 取消分享
- `GET /share/<share_id>` - 访问分享页面

#### 协作功能
- `GET /api/project/<id>/collaborations` - 获取协作者列表
- `POST /api/project/<id>/collaborations` - 添加协作者
- `DELETE /api/project/<id>/collaborations/<user_id>` - 移除协作者
- `PUT /api/project/collaborations/<id>/permission` - 更新权限

---

## 🔧 配置说明

### 应用配置（main.py）

```python
# 上传配置
UPLOAD_FOLDER = 'uploads'           # 上传文件夹
MAX_FILES_PER_UPLOAD = 10          # 每次最多上传文件数
MAX_FILE_SIZE_MB = 300             # 单文件最大大小(MB)

# 会话配置
PERMANENT_SESSION_LIFETIME = timedelta(hours=2)  # 会话过期时间

# 密钥配置（生产环境请修改）
app.secret_key = 'your_secret_key'
```

### 数据库配置（database.py）

```python
DATABASE_PATH = 'pcb_management.db'  # 数据库文件路径
UPLOAD_FOLDER = 'uploads'            # 上传目录
```

---

## 🎨 界面预览

系统采用现代化的渐变色设计风格，界面美观流畅：

- **登录页面**：简洁优雅的登录界面
- **项目面板**：卡片式布局，状态用不同渐变色区分
- **文件管理**：树形目录结构，支持文件预览
- **分享页面**：直观的文件浏览和下载界面
- **管理后台**：功能完整的管理控制面板

---

## 🚀 部署建议

### 开发环境

```bash
# 开发模式运行
python main.py
```

访问：`http://localhost:5000`

### 生产环境

推荐使用 Gunicorn + Nginx 部署：

1. **安装 Gunicorn**

```bash
pip install gunicorn
```

2. **启动 Gunicorn**

```bash
gunicorn -w 4 -b 0.0.0.0:5000 main:app
```

3. **配置 Nginx 反向代理**

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /uploads {
        alias /path/to/PartTime_web/uploads;
    }
}
```

---

## 🔄 更新日志

### v1.0.0 (2024)
- ✅ 完整的项目管理功能
- ✅ 用户登录和权限管理
- ✅ 文件上传下载
- ✅ 项目分享功能
- ✅ 协作功能
- ✅ 管理员后台
- ✅ 统计分析功能
- ✅ 响应式设计

</div>

