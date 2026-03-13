-- ═══════════════════════════════════════════════════
-- ParkSmart Database Initialization
-- Creates chatbot-specific tables (Django services handle their own migrations)
-- ═══════════════════════════════════════════════════

-- Grant full access to parksmartuser
GRANT ALL PRIVILEGES ON parksmartdb.* TO 'parksmartuser'@'%';
FLUSH PRIVILEGES;

-- ─── Chatbot Core Tables ────────────────────────────
CREATE TABLE IF NOT EXISTS chatbot_conversation (
    id CHAR(36) PRIMARY KEY,
    user_id CHAR(36) NOT NULL,
    current_state VARCHAR(50) DEFAULT 'idle',
    context JSON DEFAULT NULL,
    total_turns INT DEFAULT 0,
    clarification_count INT DEFAULT 0,
    handoff_requested TINYINT(1) DEFAULT 0,
    satisfaction_score FLOAT DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_conv_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chatbot_chatmessage (
    id CHAR(36) PRIMARY KEY,
    conversation_id CHAR(36) NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    intent VARCHAR(100) DEFAULT '',
    sub_intents JSON DEFAULT NULL,
    entities JSON DEFAULT NULL,
    confidence FLOAT DEFAULT NULL,
    decision_data JSON DEFAULT NULL,
    action_taken VARCHAR(100) DEFAULT '',
    action_result JSON DEFAULT NULL,
    processing_time_ms INT DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_msg_conv (conversation_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── Memory Architecture Tables ─────────────────────
CREATE TABLE IF NOT EXISTS chatbot_user_preferences (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id CHAR(36) NOT NULL UNIQUE,
    favorite_lot_id CHAR(36) DEFAULT NULL,
    favorite_zone_id CHAR(36) DEFAULT NULL,
    favorite_slot_code VARCHAR(20) DEFAULT '',
    default_vehicle_id CHAR(36) DEFAULT NULL,
    last_booked_slot JSON DEFAULT NULL,
    booking_history_summary JSON DEFAULT NULL,
    total_bookings INT DEFAULT 0,
    profile_summary TEXT DEFAULT '',
    summary_updated_at DATETIME DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_pref_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chatbot_user_behavior (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id CHAR(36) NOT NULL UNIQUE,
    typical_arrival_time TIME DEFAULT NULL,
    typical_departure_time TIME DEFAULT NULL,
    typical_duration_minutes INT DEFAULT NULL,
    weekday_frequency JSON DEFAULT NULL,
    prefers_near_exit TINYINT(1) DEFAULT 0,
    prefers_shade TINYINT(1) DEFAULT 0,
    prefers_same_zone TINYINT(1) DEFAULT 1,
    prefers_same_slot TINYINT(1) DEFAULT 0,
    cancel_rate FLOAT DEFAULT 0.0,
    no_show_rate FLOAT DEFAULT 0.0,
    late_arrival_rate FLOAT DEFAULT 0.0,
    overstay_rate FLOAT DEFAULT 0.0,
    data_points INT DEFAULT 0,
    confidence_score FLOAT DEFAULT 0.5,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_behav_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chatbot_user_communication_style (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id CHAR(36) NOT NULL UNIQUE,
    prefers_short TINYINT(1) DEFAULT 1,
    prefers_confirmation TINYINT(1) DEFAULT 0,
    emoji_level INT DEFAULT 1,
    formality VARCHAR(20) DEFAULT 'casual',
    primary_language VARCHAR(10) DEFAULT 'vi',
    frustration_score FLOAT DEFAULT 0.0,
    last_frustration_at DATETIME DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_style_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chatbot_conversation_summary (
    id CHAR(36) PRIMARY KEY,
    conversation_id CHAR(36) NOT NULL,
    user_id CHAR(36) NOT NULL,
    summary TEXT NOT NULL,
    key_decisions JSON DEFAULT NULL,
    unresolved_issues JSON DEFAULT NULL,
    entities_mentioned JSON DEFAULT NULL,
    sentiment VARCHAR(20) DEFAULT 'neutral',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_summ_conv (conversation_id),
    INDEX idx_summ_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── Proactive Intelligence Tables ──────────────────
CREATE TABLE IF NOT EXISTS chatbot_proactive_notification (
    id CHAR(36) PRIMARY KEY,
    user_id CHAR(36) NOT NULL,
    event_type VARCHAR(30) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    event_data JSON DEFAULT NULL,
    suggested_actions JSON DEFAULT NULL,
    user_action VARCHAR(50) DEFAULT '',
    user_action_at DATETIME DEFAULT NULL,
    trigger_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_notif_user (user_id),
    INDEX idx_notif_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chatbot_action_log (
    id CHAR(36) PRIMARY KEY,
    user_id CHAR(36) NOT NULL,
    conversation_id CHAR(36) DEFAULT NULL,
    message_id CHAR(36) DEFAULT NULL,
    action_type VARCHAR(30) NOT NULL,
    action_data JSON DEFAULT NULL,
    result_data JSON DEFAULT NULL,
    is_undoable TINYINT(1) DEFAULT 1,
    is_undone TINYINT(1) DEFAULT 0,
    undone_at DATETIME DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_action_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── AI Observability Table (🔥 2.6) ────────────────
CREATE TABLE IF NOT EXISTS chatbot_ai_metric_log (
    id CHAR(36) PRIMARY KEY,
    metric_type VARCHAR(50) NOT NULL,
    user_id CHAR(36) NOT NULL,
    conversation_id CHAR(36) DEFAULT NULL,
    intent VARCHAR(100) DEFAULT '',
    confidence FLOAT DEFAULT NULL,
    extra_data JSON DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_metric_type (metric_type),
    INDEX idx_metric_user (user_id),
    INDEX idx_metric_conv (conversation_id),
    INDEX idx_metric_time (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
