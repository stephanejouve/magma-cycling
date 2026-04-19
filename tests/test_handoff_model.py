"""Tests for HandoffSnapshot model."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from magma_cycling.models.handoff import HandoffSnapshot


class TestHandoffSnapshot:
    def test_minimal_snapshot_only_created_at(self):
        now = datetime(2026, 4, 19, 23, 30)
        snap = HandoffSnapshot(created_at=now)
        assert snap.created_at == now
        assert snap.decisions_pending == []
        assert snap.open_questions == []
        assert snap.user_mood == ""
        assert snap.next_actions == []
        assert snap.referenced_files == []
        assert snap.consumed is False

    def test_full_snapshot(self):
        snap = HandoffSnapshot(
            created_at=datetime(2026, 4, 19, 23, 30),
            decisions_pending=["alléger ou déplacer mercredi"],
            open_questions=["TSB bruit ou signal ?"],
            user_mood="Fatigué, cherche à récupérer",
            next_actions=["Décider sortie mercredi", "Planifier test FTP"],
            referenced_files=["/tmp/zwift_20260418.png"],
        )
        assert len(snap.decisions_pending) == 1
        assert snap.user_mood.startswith("Fatigué")

    def test_created_at_is_required(self):
        with pytest.raises(ValidationError):
            HandoffSnapshot()

    def test_json_roundtrip(self):
        original = HandoffSnapshot(
            created_at=datetime(2026, 4, 19, 23, 30),
            decisions_pending=["A", "B"],
            next_actions=["X"],
        )
        json_str = original.model_dump_json()
        restored = HandoffSnapshot.model_validate_json(json_str)
        assert restored == original

    def test_consumed_flag_flips(self):
        snap = HandoffSnapshot(created_at=datetime(2026, 4, 19, 23, 30))
        assert snap.consumed is False
        snap.consumed = True
        assert snap.consumed is True
