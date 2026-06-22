from loxone_bridge.services import ActivityLog


def test_activity_log_records_messages_to_file(tmp_path):
    log_file_path = tmp_path / "activity" / "bridge.log"
    activity_log = ActivityLog(log_file_path)

    entry = activity_log.record("GUI started.")

    assert entry.endswith("GUI started.")
    assert log_file_path.read_text(encoding="utf-8").endswith("GUI started.\n")
