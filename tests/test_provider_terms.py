import shutil
from datetime import date
from pathlib import Path

import pytest

from contract.errors import ProviderTermsError
from store import terms

REAL = Path(__file__).resolve().parent.parent / "config"
FILLED = """# Provider terms record
Provider: Anthropic
Read on: 2026-11-20
Sources: https://example.test/terms

- Data retention: noted from the page
- Training use: noted from the page
- Zero data retention: noted from the page
"""


def write(tmp_path, text):
    (tmp_path / "provider_terms.md").write_text(text)
    return tmp_path


TODAY = date(2026, 11, 21)


def test_template_in_the_repo_is_refused_until_filled_in():
    with pytest.raises(ProviderTermsError, match="Read on"):
        terms.require_provider_terms(REAL)


def test_dated_complete_record_passes_and_returns_the_date(tmp_path):
    assert terms.require_provider_terms(write(tmp_path, FILLED), TODAY) == "2026-11-20"
    record = terms.load_provider_terms(tmp_path, TODAY)
    assert set(record.topics) == set(terms.REQUIRED_TOPICS)


@pytest.mark.parametrize("topic", terms.REQUIRED_TOPICS)
def test_each_missing_topic_blocks_with_its_name(tmp_path, topic):
    text = FILLED.replace(f"- {topic}: noted from the page", f"- {topic}: TODO")
    with pytest.raises(ProviderTermsError, match=topic):
        terms.require_provider_terms(write(tmp_path, text), TODAY)


def test_topic_line_removed_or_empty_blocks(tmp_path):
    for text in (
        FILLED.replace("- Training use: noted from the page\n", ""),
        FILLED.replace("noted from the page", ""),
    ):
        with pytest.raises(ProviderTermsError):
            terms.require_provider_terms(write(tmp_path, text), TODAY)


@pytest.mark.parametrize(
    "bad", ["Read on: TODO", "Read on: 2026-13-45", "Read on: 20/11/2026", "Read on: 2027-01-01"]
)
def test_bad_or_future_date_blocks(tmp_path, bad):
    with pytest.raises(ProviderTermsError):
        terms.require_provider_terms(
            write(tmp_path, FILLED.replace("Read on: 2026-11-20", bad)), TODAY
        )


def test_missing_file_blocks(tmp_path):
    with pytest.raises(ProviderTermsError, match="cannot read"):
        terms.require_provider_terms(tmp_path)


def test_filled_copy_of_the_template_starts(tmp_path):
    shutil.copy(REAL / "provider_terms.md", tmp_path)
    text = (tmp_path / "provider_terms.md").read_text()
    text = text.replace("Read on: TODO (YYYY-MM-DD)", "Read on: 2026-11-20").replace(
        "TODO", "recorded"
    )
    (tmp_path / "provider_terms.md").write_text(text)
    assert terms.require_provider_terms(tmp_path, TODAY) == "2026-11-20"
