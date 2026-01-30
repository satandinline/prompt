// 提示词优化工具 - 前端交互逻辑

let conversationHistory = [];
let isProcessing = false;
let isPaused = false;
let currentUserId = null;
let currentUsername = null;
let currentSessionId = null;
let sessions = [];

// API基础URL
const API_BASE = '/api';

// 防抖函数
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 节流函数
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', async function() {
    // 验证登录状态
    const isLoggedIn = await checkLogin();
    if (!isLoggedIn) {
        window.location.href = '/login';
        return;
    }
    
    // 加载用户信息和会话
    await loadUserInfo();
    await loadSessions();
    
    // 添加页面加载动画
    document.body.style.opacity = '0';
    setTimeout(() => {
        document.body.style.transition = 'opacity 0.5s ease';
        document.body.style.opacity = '1';
    }, 100);
    
    // 添加键盘快捷键支持
    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            if (!isProcessing) {
                startOptimize();
            }
        }
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal.show').forEach(modal => {
                modal.classList.remove('show');
            });
        }
    });
});

// 检查登录状态
async function checkLogin() {
    try {
        const response = await fetch(`${API_BASE}/auth/current`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                currentUserId = data.user_id;
                currentUsername = data.username;
                return true;
            }
        }
        return false;
    } catch (error) {
        console.error('检查登录状态失败:', error);
        return false;
    }
}

// 加载用户信息
async function loadUserInfo() {
    const usernameEl = document.getElementById('current-username');
    if (usernameEl && currentUsername) {
        usernameEl.textContent = currentUsername;
    }
}

// 登出
async function logout() {
    try {
        await fetch(`${API_BASE}/auth/logout`, {
            method: 'POST',
            credentials: 'include'
        });
        window.location.href = '/login';
    } catch (error) {
        console.error('登出失败:', error);
        window.location.href = '/login';
    }
}

// 加载会话列表
async function loadSessions() {
    try {
        const response = await fetch(`${API_BASE}/sessions`, {
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (data.success) {
            sessions = data.data || [];
            renderSessionSelect();
            
            // 选择第一个会话
            if (sessions.length > 0) {
                currentSessionId = sessions[0].id;
                await loadSessionData(currentSessionId);
            }
        } else {
            showError('加载会话列表失败: ' + data.error);
        }
    } catch (error) {
        console.error('加载会话失败:', error);
        showError('加载会话失败');
    }
}

// 渲染会话选择器
function renderSessionSelect() {
    const select = document.getElementById('session-select');
    const label = document.getElementById('session-label');
    if (!select) return;
    
    select.innerHTML = '';
    
    if (sessions.length === 0) {
        select.style.display = 'none';
        if (label) label.style.display = 'none';
        return;
    }
    
    select.style.display = 'inline-block';
    if (label) label.style.display = 'inline-block';
    
    sessions.forEach(session => {
        const option = document.createElement('option');
        option.value = session.id;
        option.textContent = session.session_name;
        if (session.id === currentSessionId) {
            option.selected = true;
        }
        select.appendChild(option);
    });
}

// 创建新会话
async function createNewSession() {
    const initialRequirement = prompt('请输入初始需求（系统将自动生成会话名称）：', '');
    if (initialRequirement === null) return;
    
    // 限制输入长度
    if (initialRequirement && initialRequirement.length > 5000) {
        showNotification('初始需求过长，请控制5000字符以内', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/sessions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                initial_requirement: initialRequirement
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            await loadSessions();
            currentSessionId = data.session_id;
            document.getElementById('session-select').value = currentSessionId;
            await loadSessionData(currentSessionId);
            showNotification(`会话“${data.session_name}”创建成功`, 'success');
        } else {
            showError('创建会话失败: ' + data.error);
        }
    } catch (error) {
        console.error('创建会话失败:', error);
        showError('创建会话失败');
    }
}

// 切换会话
async function switchSession() {
    const select = document.getElementById('session-select');
    const sessionId = parseInt(select.value);
    
    if (sessionId && sessionId !== currentSessionId) {
        currentSessionId = sessionId;
        await loadSessionData(sessionId);
    }
}

// 加载会话数据
async function loadSessionData(sessionId, loadInputField = true) {
    try {
        // 只有在切换会话时才加载 initial_requirement
        if (loadInputField) {
            const session = sessions.find(s => s.id === sessionId);
            if (session && session.initial_requirement) {
                document.getElementById('user-input').value = session.initial_requirement;
            } else {
                document.getElementById('user-input').value = '';
            }
        }
        
        // 加载对话历史
        const response = await fetch(`${API_BASE}/conversations/${sessionId}`, {
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (data.success) {
            conversationHistory = data.data.map(conv => ({
                user: conv.user_message,
                ai: conv.ai_response
            }));
            renderHistory();
        } else {
            conversationHistory = [];
            renderHistory();
        }
        
        // 切换会话时才清空结果
        if (loadInputField) {
            clearResults();
        }
    } catch (error) {
        console.error('加载会话数据失败:', error);
        showError('加载会话数据失败');
    }
}

// 渲染对话历史
function renderHistory() {
    const historyList = document.getElementById('history-list');
    
    if (conversationHistory.length === 0) {
        historyList.innerHTML = `
            <div class="empty-state">
                <p>暂无对话历史</p>
                <p class="hint">点击"添加对话"开始记录您与大模型的对话</p>
            </div>
        `;
        return;
    }
    
    historyList.innerHTML = conversationHistory.map((turn, index) => {
        const aiContent = turn.ai;
        const isLong = aiContent.length > 500;
        const displayContent = isLong ? aiContent.substring(0, 500) + '...' : aiContent;
        
        return `
            <div class="history-item">
                <div class="history-item-header">轮次 ${index + 1}</div>
                <div class="history-item-content"><strong>用户:</strong> ${escapeHtml(turn.user)}</div>
                <div class="history-item-content ${isLong ? 'summary' : ''}">
                    <strong>AI:</strong> ${escapeHtml(displayContent)}
                    ${isLong ? `<br><span style="color: var(--text-hint); font-size: 12px;">(完整内容共${aiContent.length}字符，可在编辑历史中查看)</span>` : ''}
                </div>
            </div>
        `;
    }).join('');
}

// 打开添加对话对话框
function openAddDialog() {
    document.getElementById('add-dialog').classList.add('show');
    document.getElementById('dialog-user-input').value = '';
    document.getElementById('dialog-ai-input').value = '';
}

// 关闭添加对话对话框
function closeAddDialog() {
    document.getElementById('add-dialog').classList.remove('show');
}

// 保存对话
async function saveDialog() {
    const userInput = document.getElementById('dialog-user-input').value.trim();
    const aiInput = document.getElementById('dialog-ai-input').value.trim();
    
    if (!userInput || !aiInput) {
        showNotification('请填写完整的用户输入和AI回复', 'warning');
        return;
    }
    
    // 限制输入长度
    if (userInput.length > 10000 || aiInput.length > 50000) {
        showNotification('输入内容过长，用户输入限制10000字，AI回复限制50000字', 'warning');
        return;
    }
    
    if (!currentSessionId) {
        showNotification('请先选择一个会话', 'warning');
        return;
    }
    
    // 添加到数据库
    await addConversation(userInput, aiInput);
    closeAddDialog();
    showNotification('对话已添加', 'success');
}

// 打开编辑对话框
function openEditDialog() {
    if (conversationHistory.length === 0) {
        showNotification('当前没有对话历史', 'warning');
        return;
    }
    
    const editList = document.getElementById('edit-history-list');
    editList.innerHTML = conversationHistory.map((turn, index) => {
        return `
            <div class="edit-history-item" data-index="${index}">
                <div class="edit-history-item-header">
                    <span class="edit-history-item-title">轮次 ${index + 1}</span>
                    <div class="edit-history-item-actions">
                        <button class="btn btn-secondary btn-sm" onclick="editHistoryItem(${index})">编辑</button>
                        <button class="btn btn-secondary btn-sm" onclick="deleteHistoryItem(${index})">删除</button>
                    </div>
                </div>
                <div class="history-item-content"><strong>用户:</strong> ${escapeHtml(turn.user.substring(0, 100))}${turn.user.length > 100 ? '...' : ''}</div>
            </div>
        `;
    }).join('');
    
    document.getElementById('edit-dialog').classList.add('show');
}

// 关闭编辑对话框
function closeEditDialog() {
    document.getElementById('edit-dialog').classList.remove('show');
}

// 编辑历史项
function editHistoryItem(index) {
    const turn = conversationHistory[index];
    
    // 创建编辑对话框
    const editModal = document.createElement('div');
    editModal.className = 'modal show';
    editModal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h2>编辑轮次 ${index + 1}</h2>
                <button class="modal-close" onclick="this.closest('.modal').remove()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="form-group">
                    <label>用户输入</label>
                    <textarea id="edit-user-input" class="textarea" rows="4">${escapeHtml(turn.user)}</textarea>
                </div>
                <div class="form-group">
                    <div class="form-group-header">
                        <label>大模型回复</label>
                        <button class="btn btn-link btn-sm" onclick="summarizeEditContent()">自动总结长回复</button>
                    </div>
                    <textarea id="edit-ai-input" class="textarea" rows="6">${escapeHtml(turn.ai)}</textarea>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">取消</button>
                <button class="btn btn-primary" onclick="saveEditItem(${index})">保存</button>
            </div>
        </div>
    `;
    document.body.appendChild(editModal);
}

// 保存编辑项
async function saveEditItem(index) {
    const userInput = document.getElementById('edit-user-input').value.trim();
    const aiInput = document.getElementById('edit-ai-input').value.trim();
    
    if (!userInput || !aiInput) {
        showNotification('请填写完整的用户输入和AI回复', 'warning');
        return;
    }
    
    conversationHistory[index] = {
        user: userInput,
        ai: aiInput
    };
    
    // 重新保存整个对话历史到数据库
    if (currentSessionId) {
        try {
            // 清空当前会话的所有对话
            await fetch(`${API_BASE}/conversations/${currentSessionId}`, {
                method: 'DELETE',
                credentials: 'include'
            });
            
            // 重新添加所有对话
            for (const turn of conversationHistory) {
                await addConversation(turn.user, turn.ai);
            }
            
            // 重新加载对话历史
            await loadSessionData(currentSessionId, false);
        } catch (error) {
            console.error('保存编辑失败:', error);
            showError('保存编辑失败');
        }
    }
    
    renderHistory();
    
    // 关闭所有编辑对话框
    document.querySelectorAll('.modal').forEach(modal => {
        if (modal.id !== 'edit-dialog') {
            modal.remove();
        }
    });
    closeEditDialog();
}

// 删除历史项
async function deleteHistoryItem(index) {
    if (!confirm('确定要删除这个对话轮次吗？')) {
        return;
    }
    
    conversationHistory.splice(index, 1);
    
    // 重新保存整个对话历史到数据库
    // 需要先清空，然后重新添加
    if (currentSessionId) {
        try {
            // 清空当前会话的所有对话
            await fetch(`${API_BASE}/conversations/${currentSessionId}`, {
                method: 'DELETE',
                credentials: 'include'
            });
            
            // 重新添加剩余的对话
            for (const turn of conversationHistory) {
                await addConversation(turn.user, turn.ai);
            }
            
            // 重新加载对话历史
            await loadSessionData(currentSessionId, false);
            
            // 重新渲染编辑对话框
            openEditDialog();
        } catch (error) {
            console.error('删除对话失败:', error);
            showError('删除对话失败');
        }
    } else {
        renderHistory();
        openEditDialog();
    }
}

// 清空对话历史
async function clearHistory() {
    if (!currentSessionId) {
        showNotification('请先选择一个会话', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/conversations/${currentSessionId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        const data = await response.json();
        if (data.success) {
            conversationHistory = [];
            renderHistory();
            showNotification('对话历史已清空', 'success');
        } else {
            showError('清空对话历史失败: ' + data.error);
        }
    } catch (error) {
        console.error('清空对话历史失败:', error);
        showError('清空对话历史失败');
    }
}

// 清空需求输入
function clearInput() {
    document.getElementById('user-input').value = '';
    showNotification('已清空需求描述', 'success');
}

// 开始优化
async function startOptimize() {
    if (isProcessing) {
        return;
    }
    
    const userText = document.getElementById('user-input').value.trim();
    
    if (!userText && conversationHistory.length === 0) {
        showNotification('请至少提供初始需求或添加对话历史', 'warning');
        return;
    }
    
    // 如果没有当前会话，自动创建一个
    if (!currentSessionId) {
        try {
            showNotification('正在自动创建会话...', 'info');
            const response = await fetch(`${API_BASE}/sessions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    initial_requirement: userText || '新对话'
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                await loadSessions();
                currentSessionId = data.session_id;
                document.getElementById('session-select').value = currentSessionId;
                showNotification(`会话"${data.session_name}"创建成功，开始优化...`, 'success');
            } else {
                showError('创建会话失败: ' + data.error);
                return;
            }
        } catch (error) {
            console.error('创建会话失败:', error);
            showError('创建会话失败，无法开始优化');
            return;
        }
    }
    
    isProcessing = true;
    isPaused = false;
    
    // 更新UI状态
    document.getElementById('optimize-btn').disabled = true;
    document.getElementById('pause-btn').disabled = false;
    updateStatus('处理中...', 0);
    
    // 清空结果并移除活动状态
    document.getElementById('deepseek-result').textContent = '正在处理中...';
    document.getElementById('kimi-result').textContent = '等待中...';
    document.getElementById('qwen-result').textContent = '等待中...';
    document.querySelectorAll('.result-card').forEach(card => {
        card.classList.remove('active');
    });
    
    try {
        const response = await fetch(`${API_BASE}/optimize`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
                user_text: userText,
                conversation_history: conversationHistory
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // 分步更新结果和进度，添加动画效果
            updateStatus('Step 1 完成', 33);
            const deepseekCard = document.querySelector('[data-step="1"]');
            const deepseekResult = document.getElementById('deepseek-result');
            deepseekResult.textContent = data.data.deepseek || '';
            deepseekCard.classList.add('active');
            await animateText(deepseekResult, data.data.deepseek || '');
            
            await new Promise(resolve => setTimeout(resolve, 500));
            
            updateStatus('Step 2 完成', 66);
            const kimiCard = document.querySelector('[data-step="2"]');
            const kimiResult = document.getElementById('kimi-result');
            kimiResult.textContent = data.data.kimi || '';
            kimiCard.classList.add('active');
            await animateText(kimiResult, data.data.kimi || '');
            
            await new Promise(resolve => setTimeout(resolve, 500));
            
            updateStatus('完成！', 100);
            const qwenCard = document.querySelector('[data-step="3"]');
            const qwenResult = document.getElementById('qwen-result');
            qwenResult.textContent = data.data.qwen || '';
            qwenCard.classList.add('active');
            await animateText(qwenResult, data.data.qwen || '');
            
            // 将优化结果保存到数据库
            if (userText) {
                // 只保存用户输入和简短的AI响应摘要
                const aiSummary = `已完成三模型优化：DeepSeek(${data.data.deepseek.length}字) + Kimi(${data.data.kimi.length}字) + Qwen(${data.data.qwen.length}字)`;
                await addConversation(userText, aiSummary);
                await saveOptimizationResult(userText, data.data);
            }
            
            // 滚动到结果区域
            document.querySelector('.results-container').scrollIntoView({ behavior: 'smooth', block: 'start' });
        } else {
            showError('优化失败: ' + data.error);
            updateStatus('错误', 0);
        }
    } catch (error) {
        console.error('优化失败:', error);
        showError('优化失败: ' + error.message);
        updateStatus('错误', 0);
    } finally {
        isProcessing = false;
        document.getElementById('optimize-btn').disabled = false;
        document.getElementById('pause-btn').disabled = true;
    }
}

// 添加对话到数据库
async function addConversation(userMsg, aiMsg) {
    if (!currentSessionId) return;
    
    try {
        const response = await fetch(`${API_BASE}/conversations`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                session_id: currentSessionId,
                user_message: userMsg,
                ai_response: aiMsg
            })
        });
        
        const data = await response.json();
        if (data.success) {
            // 重新加载对话历史，但不加载输入框
            await loadSessionData(currentSessionId, false);
            
            // 如果返回了新的会话名称，更新会话列表
            if (data.new_session_name) {
                // 更新sessions数组中的名称
                const sessionIndex = sessions.findIndex(s => s.id === currentSessionId);
                if (sessionIndex !== -1) {
                    sessions[sessionIndex].session_name = data.new_session_name;
                }
                // 重新渲染会话选择器
                renderSessionSelect();
                // 显示提示
                console.log(`会话名称已更新为: ${data.new_session_name}`);
            }
        }
    } catch (error) {
        console.error('添加对话失败:', error);
    }
}

// 保存优化结果到数据库
async function saveOptimizationResult(originalPrompt, results) {
    if (!currentSessionId) return;
    
    try {
        const response = await fetch(`${API_BASE}/optimization-results`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                session_id: currentSessionId,
                original_prompt: originalPrompt,
                deepseek_result: results.deepseek,
                kimi_result: results.kimi,
                qwen_result: results.qwen
            })
        });
        
        const data = await response.json();
        if (!data.success) {
            console.error('保存优化结果失败:', data.error);
        }
    } catch (error) {
        console.error('保存优化结果失败:', error);
    }
}

// 暂停优化
function pauseOptimize() {
    isPaused = true;
    updateStatus('已暂停', 0);
    document.getElementById('pause-btn').disabled = true;
}

// 清空结果
function clearResults() {
    if (isProcessing) {
        showNotification('请先暂停或等待当前处理完成', 'warning');
        return;
    }
    
    document.getElementById('deepseek-result').textContent = '等待开始优化...';
    document.getElementById('kimi-result').textContent = '等待开始优化...';
    document.getElementById('qwen-result').textContent = '等待开始优化...';
    document.querySelectorAll('.result-card').forEach(card => {
        card.classList.remove('active');
    });
    updateStatus('就绪', 0);
}

// 清空全部
async function resetAll() {
    if (isProcessing) {
        showNotification('请先暂停或等待当前处理完成', 'warning');
        return;
    }
    
    // 清空初始需求输入
    document.getElementById('user-input').value = '';
    
    // 清空对话历史
    if (currentSessionId) {
        try {
            const response = await fetch(`${API_BASE}/conversations/${currentSessionId}`, {
                method: 'DELETE',
                credentials: 'include'
            });
            
            const data = await response.json();
            if (data.success) {
                conversationHistory = [];
                renderHistory();
            } else {
                showError('清空对话历史失败: ' + data.error);
                return;
            }
        } catch (error) {
            console.error('清空对话历史失败:', error);
            showError('清空对话历史失败');
            return;
        }
    }
    
    // 清空优化结果
    clearResults();
    
    showNotification('已清空所有内容', 'success');
}

// 文本打字动画效果
async function animateText(element, text) {
    if (!text) return;
    
    element.textContent = '';
    const words = text.split('');
    for (let i = 0; i < words.length; i++) {
        element.textContent += words[i];
        // 每10个字符暂停一下，让动画更流畅
        if (i % 10 === 0) {
            await new Promise(resolve => setTimeout(resolve, 10));
        }
    }
}

// 复制结果
async function copyResult(type) {
    const resultElement = document.getElementById(`${type}-result`);
    const text = resultElement.textContent;
    
    if (!text || text === '等待开始优化...' || text === '等待中...' || text === '正在处理中...') {
        showNotification('没有可复制的内容', 'warning');
        return;
    }
    
    try {
        await navigator.clipboard.writeText(text);
        showNotification(`${type.toUpperCase()}输出已复制到剪贴板`, 'success');
    } catch (error) {
        // 降级方案
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        showNotification(`${type.toUpperCase()}输出已复制到剪贴板`, 'success');
    }
}

// 显示通知
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    const colors = {
        success: 'rgba(107, 142, 90, 0.95)',
        warning: 'rgba(212, 165, 116, 0.95)',
        error: 'rgba(201, 122, 92, 0.95)',
        info: 'rgba(139, 115, 85, 0.95)'
    };
    
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 16px 24px;
        background: ${colors[type] || colors.info};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 16px rgba(61, 40, 23, 0.2);
        z-index: 10000;
        animation: slideInRight 0.3s ease-out;
        backdrop-filter: blur(10px);
        font-weight: 500;
        border: 1px solid rgba(255, 255, 255, 0.2);
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
}

// 添加CSS动画
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// 总结对话框内容
async function summarizeDialogContent() {
    const aiInput = document.getElementById('dialog-ai-input');
    const content = aiInput.value.trim();
    
    if (!content) {
        showNotification('AI回复内容为空', 'warning');
        return;
    }
    
    if (content.length < 500) {
        showNotification('AI回复内容较短，无需总结', 'info');
        return;
    }
    
    try {
        updateStatus('正在总结...', 0);
        
        const response = await fetch(`${API_BASE}/summarize`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ content: content })
        });
        
        const data = await response.json();
        
        if (data.success) {
            const shouldReplace = confirm(`总结完成（原${data.data.original_length}字符 → 现${data.data.summary_length}字符）\n\n是否替换原内容？`);
            if (shouldReplace) {
                aiInput.value = data.data.summary;
                showNotification('内容已替换', 'success');
            }
        } else {
            showNotification('总结失败: ' + data.error, 'error');
        }
    } catch (error) {
        console.error('总结失败:', error);
        showNotification('总结失败: ' + error.message, 'error');
    } finally {
        updateStatus('就绪', 0);
    }
}

// 总结编辑内容
async function summarizeEditContent() {
    const aiInput = document.getElementById('edit-ai-input');
    const content = aiInput.value.trim();
    
    if (!content) {
        showNotification('AI回复内容为空', 'warning');
        return;
    }
    
    if (content.length < 500) {
        showNotification('AI回复内容较短，无需总结', 'info');
        return;
    }
    
    try {
        updateStatus('正在总结...', 0);
        
        const response = await fetch(`${API_BASE}/summarize`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ content: content })
        });
        
        const data = await response.json();
        
        if (data.success) {
            const shouldReplace = confirm(`总结完成（原${data.data.original_length}字符 → 现${data.data.summary_length}字符）\n\n是否替换原内容？`);
            if (shouldReplace) {
                aiInput.value = data.data.summary;
                showNotification('内容已替换', 'success');
            }
        } else {
            showNotification('总结失败: ' + data.error, 'error');
        }
    } catch (error) {
        console.error('总结失败:', error);
        showNotification('总结失败: ' + error.message, 'error');
    } finally {
        updateStatus('就绪', 0);
    }
}

// 更新状态
function updateStatus(text, progress) {
    document.getElementById('status-text').textContent = text;
    document.getElementById('progress-fill').style.width = progress + '%';
    
    // 根据状态设置颜色
    const statusText = document.getElementById('status-text');
    const progressFill = document.getElementById('progress-fill');
    
    if (text === '完成！') {
        statusText.style.color = 'var(--success)';
        progressFill.style.background = 'var(--success)';
    } else if (text === '错误') {
        statusText.style.color = 'var(--error)';
        progressFill.style.background = 'var(--error)';
    } else if (text.includes('处理') || text.includes('总结')) {
        statusText.style.color = 'var(--warning)';
        progressFill.style.background = 'var(--warning)';
    } else {
        statusText.style.color = 'var(--text-secondary)';
        progressFill.style.background = 'var(--accent-primary)';
    }
}

// 显示错误
function showError(message) {
    showNotification(message, 'error');
}

// HTML转义
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 点击模态框外部关闭
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal')) {
        e.target.classList.remove('show');
    }
});
