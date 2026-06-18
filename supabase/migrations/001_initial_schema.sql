CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supabase_user_id UUID UNIQUE NOT NULL,
    name TEXT,
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    color TEXT,
    icon TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (id, user_id)
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    title TEXT,
    summary TEXT,
    last_summarized_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (id, workspace_id)
);

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    chat_id UUID NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    reasoning_summary TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    FOREIGN KEY (chat_id, workspace_id) REFERENCES chat_sessions(id, workspace_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS message_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    chat_id UUID,
    source_type TEXT NOT NULL CHECK (source_type IN ('chat', 'document', 'summary')),
    content_chunk TEXT NOT NULL,
    embedding vector(768) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    FOREIGN KEY (chat_id, workspace_id) REFERENCES chat_sessions(id, workspace_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS web_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    chat_id UUID NOT NULL,
    message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    title TEXT,
    url TEXT NOT NULL,
    snippet TEXT,
    extracted_text TEXT,
    retrieved_at TIMESTAMPTZ DEFAULT now(),
    FOREIGN KEY (chat_id, workspace_id) REFERENCES chat_sessions(id, workspace_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tool_calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    chat_id UUID NOT NULL,
    tool_name TEXT NOT NULL,
    input_json JSONB,
    output_json JSONB,
    latency_ms INTEGER,
    status TEXT CHECK (status IN ('success', 'failed', 'partial')),
    created_at TIMESTAMPTZ DEFAULT now(),
    FOREIGN KEY (chat_id, workspace_id) REFERENCES chat_sessions(id, workspace_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    chat_id UUID,
    model TEXT NOT NULL,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    estimated_cost_usd NUMERIC(10, 6) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    uploaded_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_type TEXT,
    storage_url TEXT,
    status TEXT CHECK (status IN ('uploaded', 'processing', 'ready', 'failed')),
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_workspaces_user_created ON workspaces(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_workspace_updated ON chat_sessions(workspace_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_chat_time ON messages(chat_id, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_messages_workspace_time ON messages(workspace_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_embeddings_workspace_time ON message_embeddings(workspace_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_embeddings_vector_hnsw ON message_embeddings USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_web_sources_chat ON web_sources(chat_id, retrieved_at DESC);
CREATE INDEX IF NOT EXISTS idx_usage_workspace_time ON usage_logs(workspace_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_documents_workspace_time ON documents(workspace_id, created_at DESC);

