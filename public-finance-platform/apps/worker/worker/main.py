from worker.tasks.ingest import fetch_official_sources


if __name__ == "__main__":
    result = fetch_official_sources.delay()
    print(f"Task queued: {result.id}")
