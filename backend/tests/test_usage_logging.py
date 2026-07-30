import threading

from app.services.usage_logging import (
    UsageLogDispatcher,
    UsageRecord,
    split_model_identifier,
)


def test_model_identifier_is_split_into_provider_and_model():
    assert split_model_identifier("openai/gpt-4.1-mini") == (
        "openai",
        "gpt-4.1-mini",
    )
    assert split_model_identifier("custom-model") == ("unknown", "custom-model")


def test_usage_dispatcher_serializes_writes_on_one_worker():
    """Concurrent submissions must use one database-writer thread."""
    thread_ids = []
    records = []

    def writer(record: UsageRecord):
        thread_ids.append(threading.get_ident())
        records.append(record)

    dispatcher = UsageLogDispatcher(writer=writer)
    try:
        futures = [
            dispatcher.submit(
                UsageRecord(
                    operation="cv_generation",
                    provider="openai",
                    model="gpt-4.1-mini",
                )
            )
            for _ in range(4)
        ]
        for future in futures:
            future.result(timeout=2)
    finally:
        dispatcher.shutdown()

    assert len(records) == 4
    assert len(set(thread_ids)) == 1
