-- 提示词优化工具数据库初始化脚本
USE prompt;

-- 1. 用户表
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    INDEX idx_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. 会话表
CREATE TABLE IF NOT EXISTS sessions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    session_name VARCHAR(100) DEFAULT '未命名会话',
    initial_requirement TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. 对话记录表
CREATE TABLE IF NOT EXISTS conversations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    session_id INT NOT NULL,
    turn_number INT NOT NULL,
    user_message TEXT NOT NULL,
    ai_response TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    INDEX idx_session_id (session_id),
    INDEX idx_turn_number (turn_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. 优化结果表
CREATE TABLE IF NOT EXISTS optimization_results (
    id INT PRIMARY KEY AUTO_INCREMENT,
    session_id INT NOT NULL,
    deepseek_output TEXT,
    kimi_output TEXT,
    qwen_output TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    INDEX idx_session_id (session_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. 创建视图：用户会话统计
CREATE OR REPLACE VIEW user_session_stats AS
SELECT 
    u.id AS user_id,
    u.username,
    COUNT(DISTINCT s.id) AS total_sessions,
    COUNT(c.id) AS total_conversations,
    MAX(s.updated_at) AS last_activity
FROM users u
LEFT JOIN sessions s ON u.id = s.user_id
LEFT JOIN conversations c ON s.id = c.session_id
GROUP BY u.id, u.username;

-- 6. 创建触发器：自动更新会话名称
DELIMITER $$
CREATE TRIGGER auto_name_session
BEFORE INSERT ON sessions
FOR EACH ROW
BEGIN
    IF NEW.session_name = '未命名会话' OR NEW.session_name IS NULL THEN
        SET NEW.session_name = CONCAT('会话 ', DATE_FORMAT(NOW(), '%Y%m%d%H%i%s'));
    END IF;
END$$
DELIMITER ;

-- 7. 创建存储过程：清理旧会话
DELIMITER $$
CREATE PROCEDURE cleanup_old_sessions(IN days_old INT)
BEGIN
    DELETE FROM sessions 
    WHERE is_active = FALSE 
    AND updated_at < DATE_SUB(NOW(), INTERVAL days_old DAY);
END$$
DELIMITER ;

-- 8. 创建事件：每月自动清理90天前的非活跃会话
CREATE EVENT IF NOT EXISTS monthly_cleanup
ON SCHEDULE EVERY 1 MONTH
STARTS (TIMESTAMP(CURRENT_DATE) + INTERVAL 1 MONTH + INTERVAL 3 HOUR)
DO
    CALL cleanup_old_sessions(90);

SELECT '数据库初始化完成！' AS message;
