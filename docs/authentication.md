# Authentication

Authentication is handled by Supabase Auth. The frontend signs users in with Supabase, then sends the Supabase JWT to the backend.

## Backend Verification

Every backend request must:

1. Verify the Supabase JWT.
2. Sync or load the local `users` row by `supabase_user_id`.
3. Check that the requested `workspace_id` belongs to the authenticated user.
4. Check that any `chat_id`, `message_id`, `document_id`, or retrieval id belongs to that workspace.

## Ownership Rules

```text
auth.uid() -> users.supabase_user_id
users.id -> workspaces.user_id
workspaces.id -> workspace-scoped records
```

The database migration adds RLS policies mirroring these ownership rules. Backend service-role access must still perform explicit checks because service-role credentials bypass RLS.

## Workspace Isolation Constraints

Every query path must include workspace scoping:

- list chats by workspace;
- read messages through `(chat_id, workspace_id)`;
- retrieve embeddings by `workspace_id`;
- attach document chunks to documents in the same workspace;
- attach citations only to messages in the same workspace.

## Service Role Use

The Supabase service role key belongs only in backend hosting secrets. It must never be sent to the browser, committed to source control, logged, or used in frontend build variables.
