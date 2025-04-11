// ============= 项目协作相关函数 =============

// 加载可用的协作者列表
async function loadAvailableCollaborators() {
    try {
        const response = await fetch('/api/available-collaborators');
        const users = await response.json();
        
        if (response.ok) {
            const select = document.querySelector('#addCollaboratorForm select[name="collaborator_id"]');
            // 清空现有选项，保留默认选项
            select.innerHTML = '<option value="">请选择用户</option>';
            
            users.forEach(user => {
                const option = document.createElement('option');
                option.value = user.id;
                option.textContent = user.username;
                select.appendChild(option);
            });
        } else {
            console.error('加载用户列表失败:', users.error);
            showToast('错误', '加载用户列表失败');
        }
    } catch (error) {
        console.error('加载用户列表时出错:', error);
        showToast('错误', '加载用户列表失败');
    }
}

// 加载项目协作者列表
async function loadProjectCollaborations(projectId) {
    try {
        const response = await fetch(`/api/project/${projectId}/collaborations`);
        const collaborations = await response.json();
        
        if (response.ok) {
            displayCollaborations(collaborations);
        } else {
            console.error('加载协作者列表失败:', collaborations.error);
            document.getElementById('collaboratorsList').innerHTML = `
                <div class="text-center py-4">
                    <div class="alert alert-warning border-0" style="background: linear-gradient(135deg, #fff3cd 0%, #fdf2e9 100%); border-radius: 15px;">
                        <i class="fas fa-exclamation-triangle text-warning mb-2" style="font-size: 2rem;"></i>
                        <div class="fw-bold text-dark">${collaborations.error}</div>
                    </div>
                </div>
            `;
        }
    } catch (error) {
        console.error('加载协作者列表时出错:', error);
        document.getElementById('collaboratorsList').innerHTML = `
            <div class="text-center py-4">
                <div class="alert alert-danger border-0" style="background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%); border-radius: 15px;">
                    <i class="fas fa-exclamation-triangle text-danger mb-2" style="font-size: 2rem;"></i>
                    <div class="fw-bold text-dark">加载协作者列表失败</div>
                </div>
            </div>
        `;
    }
}

// 显示协作者列表（美化版本）
function displayCollaborations(collaborations) {
    const container = document.getElementById('collaboratorsList');
    const countElement = document.getElementById('collaboratorsCount');
    
    // 更新协作者数量
    countElement.textContent = collaborations.length;
    
    if (collaborations.length === 0) {
        container.innerHTML = `
            <div class="text-center py-5">
                <div class="empty-state">
                    <div class="mb-4">
                        <div class="empty-icon-wrapper mx-auto" style="width: 80px; height: 80px; background: linear-gradient(135deg, #e9ecef 0%, #f8f9fa 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                            <i class="fas fa-users" style="font-size: 2rem; color: #6c757d;"></i>
                        </div>
                    </div>
                    <h6 class="text-dark mb-2">暂无协作者</h6>
                    <p class="text-muted mb-0">
                        <i class="fas fa-info-circle me-1"></i>
                        添加协作者以共享项目，让团队成员一起参与开发
                    </p>
                </div>
            </div>
        `;
        return;
    }
    
    container.innerHTML = collaborations.map((collab, index) => `
        <div class="collaborator-item" style="background: white; border: 1px solid #e9ecef; border-radius: 12px; padding: 1.2rem; margin-bottom: 1rem; transition: all 0.3s ease; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
            <div class="d-flex justify-content-between align-items-center">
                <div class="d-flex align-items-center flex-grow-1">
                    <!-- 用户头像和信息 -->
                    <div class="collaborator-avatar me-3">
                        <div class="avatar-wrapper" style="width: 50px; height: 50px; background: linear-gradient(135deg, ${getAvatarGradient(index)} 0%, ${getAvatarGradient(index, true)} 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                            <i class="fas fa-user text-white" style="font-size: 1.2rem;"></i>
                        </div>
                    </div>
                    
                    <div class="collaborator-info flex-grow-1">
                        <div class="d-flex align-items-center mb-1">
                            <h6 class="mb-0 text-dark fw-bold me-2">${collab.username}</h6>
                            <span class="permission-badge ${collab.permission} badge px-3 py-1" style="border-radius: 20px; font-size: 0.75rem; color: white;">
                                <i class="fas fa-${collab.permission === 'read' ? 'eye' : 'edit'} me-1"></i>
                                ${collab.permission === 'read' ? '只读' : '读写'}
                            </span>
                        </div>
                        <small class="text-muted">
                            <i class="fas fa-clock me-1"></i>
                            加入时间：${new Date(collab.created_at).toLocaleString('zh-CN', {
                                year: 'numeric',
                                month: '2-digit', 
                                day: '2-digit',
                                hour: '2-digit',
                                minute: '2-digit'
                            })}
                        </small>
                    </div>
                </div>
                
                <!-- 操作按钮 -->
                <div class="collaborator-actions d-flex align-items-center gap-2">
                    <!-- 权限选择 -->
                    <div class="permission-selector">
                        <select class="form-select form-select-sm" 
                                style="width: auto; border-radius: 8px; border: 2px solid #e9ecef; background: white; font-size: 0.85rem; min-width: 90px;" 
                                onchange="updateCollaboratorPermission(${collab.id}, this.value)"
                                title="更改权限">
                            <option value="read" ${collab.permission === 'read' ? 'selected' : ''}>只读</option>
                            <option value="write" ${collab.permission === 'write' ? 'selected' : ''}>读写</option>
                        </select>
                    </div>
                    
                    <!-- 删除按钮 -->
                    <button class="action-btn remove-btn" 
                            onclick="removeCollaborator(${currentProjectId}, ${collab.collaborator_id})"
                            title="移除协作者"
                            style="width: 36px; height: 36px; display: flex; align-items: center; justify-content: center;">
                        <i class="fas fa-trash-alt" style="font-size: 0.85rem;"></i>
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

// 获取头像渐变色
function getAvatarGradient(index, isSecondary = false) {
    const gradients = [
        ['#667eea', '#764ba2'],
        ['#f093fb', '#f5576c'],
        ['#4facfe', '#00f2fe'],
        ['#43e97b', '#38f9d7'],
        ['#fa709a', '#fee140'],
        ['#a8edea', '#fed6e3'],
        ['#ffecd2', '#fcb69f'],
        ['#ff8a80', '#ff5722']
    ];
    
    const gradient = gradients[index % gradients.length];
    return isSecondary ? gradient[1] : gradient[0];
}

// 添加协作者
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('addCollaboratorForm');
    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const data = {
                collaborator_id: parseInt(formData.get('collaborator_id')),
                permission: formData.get('permission')
            };
            
            // 禁用提交按钮并显示加载状态
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>邀请中...';
            
            try {
                const response = await fetch(`/api/project/${currentProjectId}/collaborations`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showToast('成功', result.message);
                    // 重新加载协作者列表
                    loadProjectCollaborations(currentProjectId);
                    // 重新加载可用用户列表
                    loadAvailableCollaborators();
                    // 重置表单
                    this.reset();
                    this.classList.remove('was-validated');
                } else {
                    showToast('错误', result.error);
                }
            } catch (error) {
                console.error('添加协作者时出错:', error);
                showToast('错误', '添加协作者失败');
            } finally {
                // 恢复按钮状态
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            }
        });
    }
});

// 移除协作者
async function removeCollaborator(projectId, collaboratorId) {
    // 直接执行删除操作，去掉确认对话框
    /* 
    const result = await showConfirmDialog(
        '移除协作者',
        '确定要移除此协作者吗？',
        '移除后该用户将无法访问项目内容。'
    );
    
    if (!result) return;
    */
    
    try {
        const response = await fetch(`/api/project/${projectId}/collaborations/${collaboratorId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showToast('成功', result.message);
            // 重新加载协作者列表
            loadProjectCollaborations(projectId);
            // 重新加载可用用户列表
            loadAvailableCollaborators();
        } else {
            showToast('错误', result.error);
        }
    } catch (error) {
        console.error('移除协作者时出错:', error);
        showToast('错误', '移除协作者失败');
    }
}

// 更新协作者权限
async function updateCollaboratorPermission(collaborationId, permission) {
    try {
        const response = await fetch(`/api/project/collaborations/${collaborationId}/permission`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ permission })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showToast('成功', result.message);
            // 重新加载协作者列表以更新UI
            loadProjectCollaborations(currentProjectId);
        } else {
            showToast('错误', result.error);
            // 重新加载协作者列表以恢复原始状态
            loadProjectCollaborations(currentProjectId);
        }
    } catch (error) {
        console.error('更新权限时出错:', error);
        showToast('错误', '更新权限失败');
        // 重新加载协作者列表以恢复原始状态
        loadProjectCollaborations(currentProjectId);
    }
}

// 美化确认对话框
async function showConfirmDialog(title, message, note) {
    return new Promise((resolve) => {
        const modal = document.getElementById('confirmModal');
        document.getElementById('confirmTitle').textContent = title;
        document.getElementById('confirmMessage').textContent = message;
        document.getElementById('confirmNote').textContent = note;
        
        const confirmBtn = document.getElementById('confirmOkBtn');
        
        // 移除之前的事件监听器
        const newConfirmBtn = confirmBtn.cloneNode(true);
        confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);
        
        // 添加新的事件监听器
        newConfirmBtn.addEventListener('click', () => {
            bootstrap.Modal.getInstance(modal).hide();
            resolve(true);
        });
        
        // 监听模态框关闭事件
        const handleClose = () => {
            modal.removeEventListener('hidden.bs.modal', handleClose);
            resolve(false);
        };
        modal.addEventListener('hidden.bs.modal', handleClose);
        
        // 显示模态框
        new bootstrap.Modal(modal).show();
    });
} 