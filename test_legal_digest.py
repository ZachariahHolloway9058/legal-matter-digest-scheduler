from datetime import date

from legal_digest_service import Matter, digest_lines


def test_digest_prioritizes_open_intake_signed_delivery_and_near_deadline() -> None:
    lines = digest_lines(
        [
            Matter(reference="MAT-17", intake_complete=False,
                   signed_document_url="https://portal.example/signed/17", deadline=date(2026, 9, 18)),
            Matter(reference="MAT-18", intake_complete=True, deadline=date(2026, 10, 2)),
        ],
        date(2026, 9, 14),
    )
    assert lines == [
        "MAT-17: intake needs completion",
        "MAT-17: signed document https://portal.example/signed/17",
        "MAT-17: deadline follow-up by 2026-09-18",
    ]
