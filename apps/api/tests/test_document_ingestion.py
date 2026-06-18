from app.services.document_ingestion import chunk_text, clean_text_for_postgres


def test_clean_text_for_postgres_removes_null_bytes():
    assert clean_text_for_postgres("alpha\x00beta") == "alphabeta"


def test_chunk_text_removes_null_bytes_before_chunking():
    chunks = chunk_text("alpha\x00 beta", chunk_chars=100, min_chunk_chars=1)

    assert chunks == ["alpha beta"]
