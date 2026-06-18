CREATE OR REPLACE FUNCTION is_backend_service()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
AS $$
    SELECT current_setting('app.backend_service', true) = 'on'
$$;

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

DROP POLICY IF EXISTS users_own_profile ON users;
CREATE POLICY users_own_profile ON users
    FOR ALL
    USING (is_backend_service() OR supabase_user_id = auth.uid())
    WITH CHECK (is_backend_service() OR supabase_user_id = auth.uid());

DROP POLICY IF EXISTS users_own_workspaces ON workspaces;
CREATE POLICY users_own_workspaces ON workspaces
    FOR ALL
    USING (is_backend_service() OR user_id = current_user_profile_id())
    WITH CHECK (is_backend_service() OR user_id = current_user_profile_id());

DROP POLICY IF EXISTS workspace_access_chat_sessions ON chat_sessions;
CREATE POLICY workspace_access_chat_sessions ON chat_sessions
    FOR ALL
    USING (is_backend_service() OR user_owns_workspace(workspace_id))
    WITH CHECK (is_backend_service() OR user_owns_workspace(workspace_id));

DROP POLICY IF EXISTS workspace_access_messages ON messages;
CREATE POLICY workspace_access_messages ON messages
    FOR ALL
    USING (is_backend_service() OR user_owns_workspace(workspace_id))
    WITH CHECK (is_backend_service() OR user_owns_workspace(workspace_id));

DROP POLICY IF EXISTS workspace_access_documents ON documents;
CREATE POLICY workspace_access_documents ON documents
    FOR ALL
    USING (is_backend_service() OR user_owns_workspace(workspace_id))
    WITH CHECK (is_backend_service() OR user_owns_workspace(workspace_id));

DROP POLICY IF EXISTS workspace_access_document_chunks ON document_chunks;
CREATE POLICY workspace_access_document_chunks ON document_chunks
    FOR ALL
    USING (is_backend_service() OR user_owns_workspace(workspace_id))
    WITH CHECK (is_backend_service() OR user_owns_workspace(workspace_id));

DROP POLICY IF EXISTS workspace_access_message_embeddings ON message_embeddings;
CREATE POLICY workspace_access_message_embeddings ON message_embeddings
    FOR ALL
    USING (is_backend_service() OR user_owns_workspace(workspace_id))
    WITH CHECK (is_backend_service() OR user_owns_workspace(workspace_id));

DROP POLICY IF EXISTS workspace_access_retrieval_runs ON retrieval_runs;
CREATE POLICY workspace_access_retrieval_runs ON retrieval_runs
    FOR ALL
    USING (is_backend_service() OR user_owns_workspace(workspace_id))
    WITH CHECK (is_backend_service() OR user_owns_workspace(workspace_id));

DROP POLICY IF EXISTS workspace_access_retrieval_results ON retrieval_results;
CREATE POLICY workspace_access_retrieval_results ON retrieval_results
    FOR ALL
    USING (is_backend_service() OR user_owns_workspace(workspace_id))
    WITH CHECK (is_backend_service() OR user_owns_workspace(workspace_id));

DROP POLICY IF EXISTS workspace_access_web_sources ON web_sources;
CREATE POLICY workspace_access_web_sources ON web_sources
    FOR ALL
    USING (is_backend_service() OR user_owns_workspace(workspace_id))
    WITH CHECK (is_backend_service() OR user_owns_workspace(workspace_id));

DROP POLICY IF EXISTS workspace_access_tool_calls ON tool_calls;
CREATE POLICY workspace_access_tool_calls ON tool_calls
    FOR ALL
    USING (is_backend_service() OR user_owns_workspace(workspace_id))
    WITH CHECK (is_backend_service() OR user_owns_workspace(workspace_id));

DROP POLICY IF EXISTS workspace_access_usage_logs ON usage_logs;
CREATE POLICY workspace_access_usage_logs ON usage_logs
    FOR ALL
    USING (is_backend_service() OR user_owns_workspace(workspace_id))
    WITH CHECK (is_backend_service() OR user_owns_workspace(workspace_id));

DROP POLICY IF EXISTS workspace_access_background_jobs ON background_jobs;
CREATE POLICY workspace_access_background_jobs ON background_jobs
    FOR ALL
    USING (is_backend_service() OR workspace_id IS NULL OR user_owns_workspace(workspace_id))
    WITH CHECK (is_backend_service() OR workspace_id IS NULL OR user_owns_workspace(workspace_id));
