from app.services.prompt_builder import build_messages, wants_exhaustive_list


def test_world_cup_schedule_query_requests_exhaustive_answer():
    query = "provide the list of all the upcoming 2026 football world cup matches"

    assert wants_exhaustive_list(query) is True

    messages = build_messages(
        query,
        current_history=[],
        memory_chunks=[],
        web_sources=[
            {
                "title": "World Cup 2026 schedule",
                "url": "https://example.com/schedule",
                "content": "June 19: Team A vs Team B",
            }
        ],
    )

    assert any("Do not answer with only a sample" in message["content"] for message in messages)
