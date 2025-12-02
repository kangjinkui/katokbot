// ====================================
// KaTokBot 대시보드 JavaScript
// ====================================

// 전역 상태 관리
const AppState = {
    currentLevel: 'rooms',
    selectedRoom: null,
    selectedUser: null,
    rooms: [],
    users: [],
    messages: [],
};

// API 기본 URL
const API_BASE_URL = window.location.origin;

// ====================================
// 초기화
// ====================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 KaTokBot 대시보드 초기화');
    loadHeaderStats();
    loadRooms();
});

// ====================================
// 네비게이션 함수
// ====================================

function navigateToRooms() {
    AppState.currentLevel = 'rooms';
    AppState.selectedRoom = null;
    AppState.selectedUser = null;

    updateBreadcrumb();
    showLevel('level-rooms');
    loadRooms();
}

function navigateToUsers(roomName) {
    if (roomName) {
        AppState.selectedRoom = roomName;
    }

    if (!AppState.selectedRoom) {
        alert('방을 선택해주세요');
        return;
    }

    AppState.currentLevel = 'users';
    AppState.selectedUser = null;

    updateBreadcrumb();
    showLevel('level-users');
    loadUsers(AppState.selectedRoom);
}

function navigateToChat(userId, userName, roomName) {
    if (userId) {
        AppState.selectedUser = { id: userId, name: userName, room: roomName };
    }

    if (!AppState.selectedUser) {
        alert('사용자를 선택해주세요');
        return;
    }

    AppState.currentLevel = 'chat';

    updateBreadcrumb();
    showLevel('level-chat');
    loadChatHistory();
    loadUserStats();
}

// ====================================
// UI 업데이트 함수
// ====================================

function updateBreadcrumb() {
    const breadcrumbRooms = document.getElementById('breadcrumb-rooms');
    const breadcrumbUsers = document.getElementById('breadcrumb-users');
    const breadcrumbChat = document.getElementById('breadcrumb-chat');
    const sep1 = document.getElementById('sep-1');
    const sep2 = document.getElementById('sep-2');

    // 초기화
    breadcrumbRooms.classList.remove('active');
    breadcrumbUsers.classList.remove('active');
    breadcrumbChat.classList.remove('active');
    breadcrumbUsers.style.display = 'none';
    breadcrumbChat.style.display = 'none';
    sep1.style.display = 'none';
    sep2.style.display = 'none';

    if (AppState.currentLevel === 'rooms') {
        breadcrumbRooms.classList.add('active');
    } else if (AppState.currentLevel === 'users') {
        breadcrumbUsers.style.display = 'inline-block';
        breadcrumbUsers.classList.add('active');
        breadcrumbUsers.textContent = `👥 ${AppState.selectedRoom}`;
        sep1.style.display = 'inline';
    } else if (AppState.currentLevel === 'chat') {
        breadcrumbUsers.style.display = 'inline-block';
        breadcrumbUsers.textContent = `👥 ${AppState.selectedRoom}`;
        breadcrumbChat.style.display = 'inline-block';
        breadcrumbChat.classList.add('active');
        breadcrumbChat.textContent = `💬 ${AppState.selectedUser.name}`;
        sep1.style.display = 'inline';
        sep2.style.display = 'inline';
    }
}

function showLevel(levelId) {
    const levels = document.querySelectorAll('.level-section');
    levels.forEach(level => {
        level.classList.remove('active');
    });

    const targetLevel = document.getElementById(levelId);
    if (targetLevel) {
        targetLevel.classList.add('active');
    }
}

// ====================================
// 데이터 로딩 함수
// ====================================

async function loadHeaderStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/dashboard/stats/overview`);
        const data = await response.json();

        if (data.success) {
            document.getElementById('total-rooms').textContent = data.stats.total_rooms || '0';
            document.getElementById('total-users').textContent = data.stats.total_users || '0';
            document.getElementById('total-messages').textContent = data.stats.total_messages || '0';
        }
    } catch (error) {
        console.error('통계 로딩 실패:', error);
        document.getElementById('total-rooms').textContent = '-';
        document.getElementById('total-users').textContent = '-';
        document.getElementById('total-messages').textContent = '-';
    }
}

async function loadRooms() {
    const grid = document.getElementById('rooms-grid');
    grid.innerHTML = '<div class="loading">데이터 로딩 중</div>';

    try {
        const response = await fetch(`${API_BASE_URL}/api/dashboard/rooms`);
        const data = await response.json();

        AppState.rooms = data.rooms || [];

        if (AppState.rooms.length === 0) {
            grid.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📭</div>
                    <div class="empty-state-text">아직 등록된 방이 없습니다</div>
                </div>
            `;
            return;
        }

        grid.innerHTML = AppState.rooms.map(room => `
            <div class="card" onclick="navigateToUsers('${room.room_name}')">
                <div class="card-header">
                    <div class="card-title">
                        💬 ${room.room_name}
                    </div>
                    <div class="card-badge active">${room.user_count}명</div>
                </div>
                <div class="card-body">
                    <div class="card-meta">
                        <div class="card-meta-item">
                            📊 총 메시지: ${room.total_messages}개
                        </div>
                        <div class="card-meta-item">
                            🕐 마지막 활동: ${formatDateTime(room.last_active)}
                        </div>
                    </div>
                </div>
                <div class="card-footer">
                    <span>생성일: ${formatDate(room.created_at)}</span>
                    <span>→ 자세히 보기</span>
                </div>
            </div>
        `).join('');

    } catch (error) {
        console.error('방 목록 로딩 실패:', error);
        grid.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <div class="empty-state-text">데이터 로딩 중 오류가 발생했습니다</div>
            </div>
        `;
    }
}

async function loadUsers(roomName) {
    const grid = document.getElementById('users-grid');
    grid.innerHTML = '<div class="loading">사용자 데이터 로딩 중</div>';

    try {
        const response = await fetch(`${API_BASE_URL}/api/dashboard/rooms/${encodeURIComponent(roomName)}/users`);
        const data = await response.json();

        AppState.users = data.users || [];

        if (AppState.users.length === 0) {
            grid.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">👤</div>
                    <div class="empty-state-text">이 방에 사용자가 없습니다</div>
                </div>
            `;
            return;
        }

        grid.innerHTML = AppState.users.map(user => `
            <div class="card" onclick="navigateToChat(${user.user_id}, '${user.author_name}', '${user.room_name}')">
                <div class="card-header">
                    <div class="card-title">
                        👤 ${user.author_name}
                        ${user.nickname ? `<span style="font-size: 14px; color: #7f8c8d;">(${user.nickname})</span>` : ''}
                    </div>
                    <div class="card-badge ${user.is_active ? 'active' : 'inactive'}">
                        ${user.is_active ? '활성' : '비활성'}
                    </div>
                </div>
                <div class="card-body">
                    <div class="card-meta">
                        <div class="card-meta-item">
                            💬 총 메시지: ${user.total_messages}개
                        </div>
                        <div class="card-meta-item">
                            🤖 선호 캐릭터: ${getCharacterName(user.preferred_character)}
                        </div>
                        <div class="card-meta-item">
                            🕐 마지막 활동: ${formatDateTime(user.last_active_at)}
                        </div>
                    </div>
                </div>
                <div class="card-footer">
                    <span>가입일: ${formatDate(user.created_at)}</span>
                    <span>→ 대화 보기</span>
                </div>
            </div>
        `).join('');

    } catch (error) {
        console.error('사용자 목록 로딩 실패:', error);
        grid.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <div class="empty-state-text">데이터 로딩 중 오류가 발생했습니다</div>
            </div>
        `;
    }
}

async function loadChatHistory() {
    const container = document.getElementById('chat-messages');
    container.innerHTML = '<div class="loading">대화 내역 로딩 중</div>';

    try {
        const response = await fetch(`${API_BASE_URL}/api/chat/history`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                room_name: AppState.selectedUser.room,
                author_name: AppState.selectedUser.name,
                limit: 50
            })
        });

        const data = await response.json();
        AppState.messages = data.messages || [];

        if (AppState.messages.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">💬</div>
                    <div class="empty-state-text">아직 대화 내역이 없습니다</div>
                </div>
            `;
            return;
        }

        container.innerHTML = AppState.messages.map(msg => `
            <div class="chat-message">
                <div class="message-header">
                    <span class="message-type-badge ${msg.message_type}">
                        ${msg.message_type.toUpperCase()}
                    </span>
                    <span>${formatDateTime(msg.created_at)}</span>
                    ${msg.tokens_used > 0 ? `<span>🎯 ${msg.tokens_used} tokens</span>` : ''}
                </div>
                <div class="message-content ${msg.message_type}">
                    ${escapeHtml(msg.content)}
                </div>
            </div>
        `).join('');

        // 스크롤을 맨 아래로
        container.scrollTop = container.scrollHeight;

    } catch (error) {
        console.error('대화 내역 로딩 실패:', error);
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <div class="empty-state-text">대화 내역을 불러올 수 없습니다</div>
            </div>
        `;
    }
}

async function loadUserStats() {
    const userInfoDiv = document.getElementById('user-info');
    const statsDiv = document.getElementById('chat-stats');

    try {
        const response = await fetch(`${API_BASE_URL}/api/stats/users/${AppState.selectedUser.id}`);
        const stats = await response.json();

        // 사용자 정보 카드
        userInfoDiv.innerHTML = `
            <div class="user-info-header">
                <div class="user-avatar">👤</div>
                <div>
                    <div class="user-name">${stats.author_name}</div>
                    <div class="user-room">📍 ${stats.room_name}</div>
                </div>
            </div>
            <div class="user-stats">
                <div class="user-stat">
                    <div class="user-stat-value">${stats.total_messages}</div>
                    <div class="user-stat-label">총 메시지</div>
                </div>
                <div class="user-stat">
                    <div class="user-stat-value">${stats.total_tokens_used}</div>
                    <div class="user-stat-label">사용 토큰</div>
                </div>
                <div class="user-stat">
                    <div class="user-stat-value">${formatDate(stats.first_message_at)}</div>
                    <div class="user-stat-label">첫 대화</div>
                </div>
            </div>
        `;

        // 통계 요약
        statsDiv.innerHTML = `
            <div class="stat-card">
                <div class="stat-card-value">${stats.total_messages}</div>
                <div class="stat-card-label">총 메시지</div>
            </div>
            <div class="stat-card">
                <div class="stat-card-value">${stats.total_tokens_used}</div>
                <div class="stat-card-label">사용 토큰</div>
            </div>
            <div class="stat-card">
                <div class="stat-card-value">${AppState.messages.length}</div>
                <div class="stat-card-label">표시된 메시지</div>
            </div>
            <div class="stat-card">
                <div class="stat-card-value">${formatDate(stats.last_message_at)}</div>
                <div class="stat-card-label">마지막 대화</div>
            </div>
        `;

    } catch (error) {
        console.error('사용자 통계 로딩 실패:', error);
    }
}

// ====================================
// 세션 관리
// ====================================

function clearSession() {
    const modal = document.getElementById('modal-confirm');
    modal.classList.add('active');
}

function closeModal() {
    const modal = document.getElementById('modal-confirm');
    modal.classList.remove('active');
}

async function confirmClearSession() {
    try {
        const response = await fetch(
            `${API_BASE_URL}/api/chat/session/${encodeURIComponent(AppState.selectedUser.room)}/${encodeURIComponent(AppState.selectedUser.name)}`,
            { method: 'DELETE' }
        );

        const result = await response.json();

        if (result.success) {
            alert('✅ 대화 세션이 초기화되었습니다');
            closeModal();
            loadChatHistory();
            loadUserStats();
        } else {
            alert('❌ 세션 초기화 실패: ' + result.message);
        }
    } catch (error) {
        console.error('세션 초기화 실패:', error);
        alert('❌ 세션 초기화 중 오류가 발생했습니다');
    }
}

// ====================================
// 유틸리티 함수
// ====================================

function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('ko-KR');
}

function formatDateTime(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString('ko-KR', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function getCharacterName(character) {
    const characters = {
        'tsundere_cat': '츤데레 고양이',
        'kind_teacher': '친절한 선생님',
        'professional': '전문가',
    };
    return characters[character] || character;
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// 검색 기능
document.getElementById('search-rooms')?.addEventListener('input', function(e) {
    const searchTerm = e.target.value.toLowerCase();
    const cards = document.querySelectorAll('#rooms-grid .card');

    cards.forEach(card => {
        const text = card.textContent.toLowerCase();
        card.style.display = text.includes(searchTerm) ? 'block' : 'none';
    });
});
