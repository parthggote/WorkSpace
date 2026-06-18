from app.schemas.chat import Citation

import datetime


def wants_exhaustive_list(user_query: str) -> bool:
    lowered = user_query.lower()
    list_terms = ["all", "complete", "full", "detailed", "detailled", "list of", "schedule", "fixtures", "matches"]
    schedule_terms = ["world cup", "football", "soccer", "match", "matches", "fixtures", "schedule"]
    return any(term in lowered for term in list_terms) and any(term in lowered for term in schedule_terms)

def get_system_prompt() -> str:
    current_date = datetime.datetime.now().strftime("%B %d, %Y")
    return f"""You are a helpful workspace assistant.
The current date is {current_date}. Pay close attention to dates and years in user queries.
You HAVE full internet access capability via the 'Live web sources' provided to you. Do NOT claim you cannot browse the internet or access live data.
When providing information about live sports, current events, or real-time data, STRICTLY prioritize 'Live web sources' over 'Workspace memory', as memory may contain outdated or hallucinated information from previous chats.
Use provided workspace memory and web sources when relevant.
When document content is provided, prioritize it for answering questions about uploaded files.
Do not claim a source supports something unless it appears in the source text.
If the sources provided do not perfectly match the user's query regarding time, events, or categories (e.g. U-17 vs Men's), inform the user rather than assuming they match.
When using previous chats, cite them as prior workspace conversations.
Keep final answers concise and actionable, and strictly adhere to the facts presented in the live web sources for current events."""

def build_messages(
    user_query: str,
    current_history: list[dict],
    memory_chunks: list[dict],
    web_sources: list[dict],
    document_chunks: list[dict] | None = None,
) -> list[dict[str, str]]:
    context_parts: list[str] = []
    if memory_chunks:
        context_parts.append("Workspace memory:\n" + "\n\n".join(
            f"[memory:{idx}] chat={m.get('chat_title')} message={m.get('message_id')} score={m.get('score')}\n{m.get('content')}"
            for idx, m in enumerate(memory_chunks, start=1)
        ))
    if document_chunks:
        context_parts.append("Uploaded document content:\n" + "\n\n".join(
            f"[doc:{idx}] file={d.get('filename')} score={d.get('score')}\n{d.get('content')}"
            for idx, d in enumerate(document_chunks, start=1)
        ))
    if web_sources:
        context_parts.append("Live web sources:\n" + "\n\n".join(
            f"[web:{idx}] {s.get('title')} {s.get('url')}\n{s.get('content')}"
            for idx, s in enumerate(web_sources, start=1)
        ))

    messages = [{"role": "system", "content": get_system_prompt()}]
    if wants_exhaustive_list(user_query):
        messages.append({
            "role": "system",
            "content": (
                "The user is asking for a complete/detailed list. Do not answer with only a sample, a short teaser, "
                "or a generic link. Extract every relevant item available in the provided sources and present it in a "
                "structured table or grouped list. If the provided sources are incomplete, state exactly which dates "
                "or rounds are covered and which are missing."
            ),
        })
    if context_parts:
        messages.append({"role": "system", "content": "\n\n".join(context_parts)})
    for item in current_history[-8:]:
        if item["role"] in {"user", "assistant"}:
            messages.append({"role": item["role"], "content": item["content"]})
    messages.append({"role": "user", "content": user_query})
    return messages


def build_citations(
    memory_chunks: list[dict],
    web_sources: list[dict],
    document_chunks: list[dict] | None = None,
) -> list[Citation]:
    citations: list[Citation] = []
    for item in memory_chunks:
        content = item.get("content", "")
        citations.append(Citation(
            source="memory",
            title=item.get("chat_title") or "Previous chat",
            chat_id=item.get("chat_id"),
            message_id=item.get("message_id"),
            score=item.get("score"),
            excerpt=content[:250] + "..." if len(content) > 250 else content
        ))
    for item in (document_chunks or []):
        doc_id = item.get("document_id")
        content = item.get("content", "")
        citations.append(Citation(
            source="document",
            title=item.get("filename") or "Uploaded document",
            locator=str(doc_id) if doc_id else None,
            score=item.get("score"),
            excerpt=content[:250] + "..." if len(content) > 250 else content
        ))
    for item in web_sources:
        content = item.get("content", "")
        citations.append(Citation(
            source="web",
            title=item.get("title") or item.get("url") or "Web source",
            url=item.get("url"),
            score=item.get("score"),
            excerpt=content[:250] + "..." if len(content) > 250 else content
        ))
    return citations
