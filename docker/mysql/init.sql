-- 创建数据库
CREATE DATABASE IF NOT EXISTS aiops CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE aiops;

-- 创建用户会话表
CREATE TABLE IF NOT EXISTS user_sessions (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    session_id VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSON,
    INDEX idx_user_id (user_id),
    INDEX idx_session_id (session_id),
    INDEX idx_created_at (created_at)
);

-- 创建会话消息表
CREATE TABLE IF NOT EXISTS session_messages (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    response TEXT,
    message_type ENUM('user', 'assistant', 'system') DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tokens_used INT DEFAULT 0,
    processing_time FLOAT DEFAULT 0,
    metadata JSON,
    INDEX idx_session_id (session_id),
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (session_id) REFERENCES user_sessions(session_id) ON DELETE CASCADE
);

-- 创建知识库文档表
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id VARCHAR(36) PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    source ENUM('wiki', 'gitlab', 'jira', 'logs') NOT NULL,
    source_id VARCHAR(100),
    category VARCHAR(100),
    tags JSON,
    embedding_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_source (source),
    INDEX idx_category (category),
    INDEX idx_created_at (created_at),
    FULLTEXT idx_title_content (title, content)
);

-- 创建实体表
CREATE TABLE IF NOT EXISTS entities (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    description TEXT,
    properties JSON,
    neo4j_id BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_name_type (name, entity_type),
    INDEX idx_entity_type (entity_type),
    INDEX idx_neo4j_id (neo4j_id)
);

-- 创建关系表
CREATE TABLE IF NOT EXISTS relationships (
    id VARCHAR(36) PRIMARY KEY,
    source_entity_id VARCHAR(36) NOT NULL,
    target_entity_id VARCHAR(36) NOT NULL,
    relationship_type VARCHAR(100) NOT NULL,
    properties JSON,
    confidence FLOAT DEFAULT 1.0,
    neo4j_id BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_source_entity (source_entity_id),
    INDEX idx_target_entity (target_entity_id),
    INDEX idx_relationship_type (relationship_type),
    FOREIGN KEY (source_entity_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (target_entity_id) REFERENCES entities(id) ON DELETE CASCADE
);

-- 创建系统配置表
CREATE TABLE IF NOT EXISTS system_config (
    id VARCHAR(36) PRIMARY KEY,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value JSON NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_config_key (config_key)
);

-- 创建任务队列表
CREATE TABLE IF NOT EXISTS task_queue (
    id VARCHAR(36) PRIMARY KEY,
    task_type VARCHAR(100) NOT NULL,
    task_data JSON NOT NULL,
    status ENUM('pending', 'running', 'completed', 'failed') DEFAULT 'pending',
    priority INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    retry_count INT DEFAULT 0,
    scheduled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    error_message TEXT,
    result JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_task_type (task_type),
    INDEX idx_priority (priority),
    INDEX idx_scheduled_at (scheduled_at)
);

-- 插入默认配置
INSERT INTO system_config (id, config_key, config_value, description) VALUES
(UUID(), 'embedding_model', '"sentence-transformers/all-MiniLM-L6-v2"', '默认嵌入模型'),
(UUID(), 'max_tokens', '4096', 'LLM最大token数量'),
(UUID(), 'temperature', '0.7', 'LLM温度参数'),
(UUID(), 'top_k', '10', '检索结果数量'),
(UUID(), 'similarity_threshold', '0.7', '相似度阈值')
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

-- 创建用于全文搜索的存储过程
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS SearchKnowledgeDocuments(
    IN search_query TEXT,
    IN doc_source VARCHAR(20),
    IN limit_count INT
)
BEGIN
    SET @sql = CONCAT(
        'SELECT id, title, content, source, category, tags, ',
        'MATCH(title, content) AGAINST(? IN NATURAL LANGUAGE MODE) as relevance_score ',
        'FROM knowledge_documents WHERE 1=1'
    );
    
    IF doc_source IS NOT NULL THEN
        SET @sql = CONCAT(@sql, ' AND source = ?');
    END IF;
    
    SET @sql = CONCAT(@sql, ' AND MATCH(title, content) AGAINST(? IN NATURAL LANGUAGE MODE) > 0');
    SET @sql = CONCAT(@sql, ' ORDER BY relevance_score DESC');
    
    IF limit_count IS NOT NULL THEN
        SET @sql = CONCAT(@sql, ' LIMIT ?');
    END IF;
    
    PREPARE stmt FROM @sql;
    
    IF doc_source IS NOT NULL AND limit_count IS NOT NULL THEN
        EXECUTE stmt USING search_query, doc_source, search_query, limit_count;
    ELSEIF doc_source IS NOT NULL THEN
        EXECUTE stmt USING search_query, doc_source, search_query;
    ELSEIF limit_count IS NOT NULL THEN
        EXECUTE stmt USING search_query, search_query, limit_count;
    ELSE
        EXECUTE stmt USING search_query, search_query;
    END IF;
    
    DEALLOCATE PREPARE stmt;
END //
DELIMITER ;