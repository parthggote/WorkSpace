CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS auth;

DO $$
BEGIN
    CREATE OR REPLACE FUNCTION auth.uid()
    RETURNS UUID
    LANGUAGE sql
    STABLE
    AS 'SELECT NULLIF(current_setting(''request.jwt.claim.sub'', true), '''')::UUID';
END $$;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

ALTER TABLE messages
    ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'complete',
    ADD COLUMN IF NOT EXISTS token_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS model TEXT,
    ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

ALTER TABLE message_embeddings
    ADD COLUMN IF NOT EXISTS document_id UUID,
    ADD COLUMN IF NOT EXISTS document_chunk_id UUID,
    ADD COLUMN IF NOT EXISTS chunk_index INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS embedding_model TEXT NOT NULL DEFAULT 'BAAI/bge-base-en-v1.5',
    ADD COLUMN IF NOT EXISTS token_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE web_sources
    ADD COLUMN IF NOT EXISTS source_domain TEXT,
    ADD COLUMN IF NOT EXISTS extracted_text_hash TEXT,
    ADD COLUMN IF NOT EXISTS rank_score NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS rerank_score NUMERIC(8,6),
    ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE tool_calls
    ADD COLUMN IF NOT EXISTS provider TEXT,
    ADD COLUMN IF NOT EXISTS message_id UUID,
    ADD COLUMN IF NOT EXISTS input_hash TEXT,
    ADD COLUMN IF NOT EXISTS output_hash TEXT,
    ADD COLUMN IF NOT EXISTS error_message TEXT,
    ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE usage_logs
    ADD COLUMN IF NOT EXISTS message_id UUID,
    ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'openrouter',
    ADD COLUMN IF NOT EXISTS latency_ms INTEGER,
    ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'success',
    ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS original_filename TEXT,
    ADD COLUMN IF NOT EXISTS storage_path TEXT,
    ADD COLUMN IF NOT EXISTS mime_type TEXT,
    ADD COLUMN IF NOT EXISTS byte_size BIGINT,
    ADD COLUMN IF NOT EXISTS sha256 TEXT,
    ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

UPDATE documents
SET original_filename = COALESCE(original_filename, filename)
WHERE original_filename IS NULL;

UPDATE documents
SET storage_path = COALESCE(storage_path, storage_url)
WHERE storage_path IS NULL;

UPDATE documents
SET mime_type = COALESCE(mime_type, file_type, 'application/octet-stream')
WHERE mime_type IS NULL;

CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    document_id UUID NOT NULL,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    content TEXT NOT NULL,
    token_count INTEGER NOT NULL DEFAULT 0 CHECK (token_count >= 0),
    page_number INTEGER CHECK (page_number IS NULL OR page_number > 0),
    section_heading TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (id, workspace_id),
    UNIQUE (document_id, chunk_index),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS retrieval_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    chat_id UUID,
    message_id UUID,
    query TEXT NOT NULL,
    query_embedding_model TEXT NOT NULL DEFAULT 'BAAI/bge-base-en-v1.5',
    top_k_before_rerank INTEGER NOT NULL DEFAULT 20 CHECK (top_k_before_rerank > 0),
    top_k_after_rerank INTEGER NOT NULL DEFAULT 5 CHECK (top_k_after_rerank > 0),
    similarity_threshold NUMERIC(5,4),
    reranker_model TEXT,
    status TEXT NOT NULL DEFAULT 'completed' CHECK (status IN ('completed', 'partial', 'failed')),
    latency_ms INTEGER CHECK (latency_ms IS NULL OR latency_ms >= 0),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (chat_id, workspace_id) REFERENCES chat_sessions(id, workspace_id) ON DELETE CASCADE,
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS retrieval_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    retrieval_run_id UUID NOT NULL REFERENCES retrieval_runs(id) ON DELETE CASCADE,
    embedding_id UUID REFERENCES message_embeddings(id) ON DELETE SET NULL,
    rank_before_rerank INTEGER NOT NULL CHECK (rank_before_rerank > 0),
    rank_after_rerank INTEGER CHECK (rank_after_rerank IS NULL OR rank_after_rerank > 0),
    similarity_score NUMERIC(8,6),
    keyword_score NUMERIC(8,6),
    recency_score NUMERIC(8,6),
    title_match_score NUMERIC(8,6),
    source_type_score NUMERIC(8,6),
    cross_encoder_score NUMERIC(8,6),
    rerank_score NUMERIC(8,6),
    selected_for_context BOOLEAN NOT NULL DEFAULT false,
    citation_label TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS background_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    queue_name TEXT NOT NULL,
    task_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'retrying', 'cancelled')),
    priority INTEGER NOT NULL DEFAULT 0,
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    max_attempts INTEGER NOT NULL DEFAULT 3 CHECK (max_attempts > 0),
    run_after TIMESTAMPTZ NOT NULL DEFAULT now(),
    locked_by TEXT,
    lock_expires_at TIMESTAMPTZ,
    celery_task_id TEXT UNIQUE,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_workspace_sha256
    ON documents(workspace_id, sha256)
    WHERE sha256 IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_document_chunks_workspace_document
    ON document_chunks(workspace_id, document_id, chunk_index);

CREATE INDEX IF NOT EXISTS idx_embeddings_workspace_source
    ON message_embeddings(workspace_id, source_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_embeddings_message_summary_vector
    ON message_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WHERE source_type IN ('chat', 'message', 'summary');

CREATE INDEX IF NOT EXISTS idx_embeddings_document_vector
    ON message_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WHERE source_type = 'document';

CREATE INDEX IF NOT EXISTS idx_retrieval_runs_workspace_created
    ON retrieval_runs(workspace_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_retrieval_results_run_selected
    ON retrieval_results(retrieval_run_id, selected_for_context);

CREATE INDEX IF NOT EXISTS idx_web_sources_workspace_chat
    ON web_sources(workspace_id, chat_id, retrieved_at DESC);

CREATE INDEX IF NOT EXISTS idx_tool_calls_workspace_created
    ON tool_calls(workspace_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_usage_logs_workspace_created
    ON usage_logs(workspace_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_background_jobs_queue_status
    ON background_jobs(queue_name, status, run_after, priority DESC);

CREATE INDEX IF NOT EXISTS idx_background_jobs_workspace_status
    ON background_jobs(workspace_id, status, created_at DESC);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS set_users_updated_at ON users;
CREATE TRIGGER set_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS set_messages_updated_at ON messages;
CREATE TRIGGER set_messages_updated_at
    BEFORE UPDATE ON messages
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS set_background_jobs_updated_at ON background_jobs;
CREATE TRIGGER set_background_jobs_updated_at
    BEFORE UPDATE ON background_jobs
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE FUNCTION current_user_profile_id()
RETURNS UUID
LANGUAGE sql
STABLE
AS $$
    SELECT id
    FROM users
    WHERE supabase_user_id = auth.uid()
$$;

CREATE OR REPLACE FUNCTION user_owns_workspace(target_workspace_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM workspaces w
        JOIN users u ON u.id = w.user_id
        WHERE w.id = target_workspace_id
          AND u.supabase_user_id = auth.uid()
    )
$$;

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE message_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE retrieval_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE retrieval_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE web_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE tool_calls ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE background_jobs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS users_own_profile ON users;
CREATE POLICY users_own_profile ON users
    FOR ALL
    USING (supabase_user_id = auth.uid())
    WITH CHECK (supabase_user_id = auth.uid());

DROP POLICY IF EXISTS users_own_workspaces ON workspaces;
CREATE POLICY users_own_workspaces ON workspaces
    FOR ALL
    USING (user_id = current_user_profile_id())
    WITH CHECK (user_id = current_user_profile_id());

DROP POLICY IF EXISTS workspace_access_chat_sessions ON chat_sessions;
CREATE POLICY workspace_access_chat_sessions ON chat_sessions
    FOR ALL
    USING (user_owns_workspace(workspace_id))
    WITH CHECK (user_owns_workspace(workspace_id));

DROP POLICY IF EXISTS workspace_access_messages ON messages;
CREATE POLICY workspace_access_messages ON messages
    FOR ALL
    USING (user_owns_workspace(workspace_id))
    WITH CHECK (user_owns_workspace(workspace_id));

DROP POLICY IF EXISTS workspace_access_documents ON documents;
CREATE POLICY workspace_access_documents ON documents
    FOR ALL
    USING (user_owns_workspace(workspace_id))
    WITH CHECK (user_owns_workspace(workspace_id));

DROP POLICY IF EXISTS workspace_access_document_chunks ON document_chunks;
CREATE POLICY workspace_access_document_chunks ON document_chunks
    FOR ALL
    USING (user_owns_workspace(workspace_id))
    WITH CHECK (user_owns_workspace(workspace_id));

DROP POLICY IF EXISTS workspace_access_message_embeddings ON message_embeddings;
CREATE POLICY workspace_access_message_embeddings ON message_embeddings
    FOR ALL
    USING (user_owns_workspace(workspace_id))
    WITH CHECK (user_owns_workspace(workspace_id));

DROP POLICY IF EXISTS workspace_access_retrieval_runs ON retrieval_runs;
CREATE POLICY workspace_access_retrieval_runs ON retrieval_runs
    FOR ALL
    USING (user_owns_workspace(workspace_id))
    WITH CHECK (user_owns_workspace(workspace_id));

DROP POLICY IF EXISTS workspace_access_retrieval_results ON retrieval_results;
CREATE POLICY workspace_access_retrieval_results ON retrieval_results
    FOR ALL
    USING (user_owns_workspace(workspace_id))
    WITH CHECK (user_owns_workspace(workspace_id));

DROP POLICY IF EXISTS workspace_access_web_sources ON web_sources;
CREATE POLICY workspace_access_web_sources ON web_sources
    FOR ALL
    USING (user_owns_workspace(workspace_id))
    WITH CHECK (user_owns_workspace(workspace_id));

DROP POLICY IF EXISTS workspace_access_tool_calls ON tool_calls;
CREATE POLICY workspace_access_tool_calls ON tool_calls
    FOR ALL
    USING (user_owns_workspace(workspace_id))
    WITH CHECK (user_owns_workspace(workspace_id));

DROP POLICY IF EXISTS workspace_access_usage_logs ON usage_logs;
CREATE POLICY workspace_access_usage_logs ON usage_logs
    FOR ALL
    USING (user_owns_workspace(workspace_id))
    WITH CHECK (user_owns_workspace(workspace_id));

DROP POLICY IF EXISTS workspace_access_background_jobs ON background_jobs;
CREATE POLICY workspace_access_background_jobs ON background_jobs
    FOR ALL
    USING (workspace_id IS NULL OR user_owns_workspace(workspace_id))
    WITH CHECK (workspace_id IS NULL OR user_owns_workspace(workspace_id));
