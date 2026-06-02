-- core/logging/schema.sql
-- Postgres schema cho agent action logs (production).
-- Chạy 1 lần khi setup production environment.
-- Dev/test dùng JSONL file — không cần chạy file này.
--
-- Usage:
--   psql $LOGGING_DATABASE_URL -f core/logging/schema.sql

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Bảng chính: mọi agent action
CREATE TABLE IF NOT EXISTS agent_logs (
    id          BIGSERIAL       PRIMARY KEY,
    timestamp   TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    task_id     TEXT            NOT NULL,
    agent       TEXT            NOT NULL,        -- DevAgent, QAAgent, ...
    action      TEXT            NOT NULL,        -- code_generated, test_run, ...
    status      TEXT            NOT NULL,        -- success, fail, error, info
    details     JSONB           NOT NULL DEFAULT '{}'::jsonb
);

-- Indexes cho các query phổ biến
CREATE INDEX IF NOT EXISTS idx_agent_logs_task_id   ON agent_logs(task_id);
CREATE INDEX IF NOT EXISTS idx_agent_logs_agent      ON agent_logs(agent);
CREATE INDEX IF NOT EXISTS idx_agent_logs_status     ON agent_logs(status);
CREATE INDEX IF NOT EXISTS idx_agent_logs_timestamp  ON agent_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_agent_logs_task_agent ON agent_logs(task_id, agent);

-- View tiện dùng: logs của ngày hôm nay
CREATE OR REPLACE VIEW today_logs AS
SELECT *
FROM agent_logs
WHERE timestamp >= CURRENT_DATE::timestamptz
ORDER BY timestamp DESC;

-- View: tổng hợp theo task
CREATE OR REPLACE VIEW task_summary AS
SELECT
    task_id,
    COUNT(*)                                                   AS total_actions,
    COUNT(*) FILTER (WHERE status = 'success')                 AS successes,
    COUNT(*) FILTER (WHERE status = 'fail')                    AS failures,
    MIN(timestamp)                                             AS started_at,
    MAX(timestamp)                                             AS last_action_at,
    ROUND(EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp)))::numeric, 1) AS duration_seconds
FROM agent_logs
GROUP BY task_id
ORDER BY started_at DESC;

-- View: violations (fail + error)
CREATE OR REPLACE VIEW failed_actions AS
SELECT timestamp, task_id, agent, action, details
FROM agent_logs
WHERE status IN ('fail', 'error')
ORDER BY timestamp DESC;

-- Auto-cleanup: xoá logs cũ hơn 30 ngày (chạy bằng pg_cron hoặc script)
-- DELETE FROM agent_logs WHERE timestamp < NOW() - INTERVAL '30 days';
