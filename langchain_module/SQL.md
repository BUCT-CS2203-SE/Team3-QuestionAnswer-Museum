CREATE TABLE chat_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(64) NOT NULL,
    session_id VARCHAR(64) NOT NULL,
    role ENUM('SYSTEM', 'USER', 'AI') NOT NULL,
    content TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_user_session ON chat_history (user_id, session_id);

INSERT INTO chat_history (user_id, session_id, role, content) VALUES
('user123', 'session1', 'SYSTEM', 'You are a helpful assistant'),
('user123', 'session1', 'USER', 'Hello!'),
('user123', 'session1', 'AI', 'Hi! How can I help you?'),
('user456', 'session2', 'SYSTEM', 'You are a technical expert'),
('user456', 'session2', 'USER', 'Explain quantum computing');