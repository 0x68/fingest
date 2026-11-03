"""Cloud object fixtures (@aws_bucket_fixture & co.) and seeding configuration."""

import pytest

from fingest import CSVFixture, JSONFixture, XMLFixture
from fingest.cloud.base import _active_by_provider


def test_s3_object_fixture(s3_users, s3_sales):
    assert isinstance(s3_users, JSONFixture)
    assert s3_users[0]["name"] == "John Doe"
    assert isinstance(s3_sales, CSVFixture)
    assert s3_sales.get_column("amount") == ["10.5", "99.0"]


def test_gcs_and_azure_object_fixtures(gcs_events, gcs_products, azure_config):
    assert gcs_events == [{"event": "click", "user": 1}, {"event": "view", "user": 2}]
    assert gcs_products.row_count > 0
    assert isinstance(azure_config, XMLFixture)


def test_object_fixture_alone_does_not_patch_sdks(s3_users):
    assert "s3" not in _active_by_provider


@pytest.fixture
def arranged(fake_s3):
    fake_s3.put("reports", "users.json", [{"name": "Arranged"}])


def test_object_fixture_sees_arranged_state(arranged, fake_s3, s3_users):
    assert s3_users[0]["name"] == "Arranged"


def test_seed_roots_are_configurable(pytester):
    pytester.makeini(
        "[pytest]\nfingest_s3_root = buckets/aws\nfingest_gcs_root = /nonexistent\n"
    )
    pytester.mkdir("buckets")
    bucket = pytester.mkdir("buckets/aws").joinpath("b")
    bucket.mkdir()
    bucket.joinpath("x.json").write_text('{"ok": true}')
    pytester.makepyfile(
        """
        def test_seed(fake_s3, fake_gcs):
            assert fake_s3.snapshot() == {"b": {"x.json": b'{"ok": true}'}}
            assert fake_gcs.buckets() == []
        """
    )
    pytester.runpytest("-p", "no:cacheprovider").assert_outcomes(passed=1)


def test_live_flag_switches_unset_mock_only(pytester):
    pytester.makeconftest(
        """
        import fingest.cloud.decorators as d
        from fingest import aws_bucket_fixture

        d._LIVE_READERS["s3"] = lambda bucket, key: b'"live"'

        @aws_bucket_fixture("b", "k.json")
        def follows_flag(data):
            return data

        @aws_bucket_fixture("b", "k.json", mock=True)
        def always_mocked(data):
            return data
        """
    )
    pytester.mkdir("data")
    pytester.path.joinpath("data", "s3", "b").mkdir(parents=True)
    pytester.path.joinpath("data", "s3", "b", "k.json").write_text('"mock"')
    pytester.makepyfile(
        """
        def test_it(follows_flag, always_mocked, pytestconfig):
            live = pytestconfig.getoption("fingest_live")
            assert follows_flag == ("live" if live else "mock")
            assert always_mocked == "mock"
        """
    )
    pytester.runpytest("-p", "no:cacheprovider").assert_outcomes(passed=1)
    result = pytester.runpytest("-p", "no:cacheprovider", "--fingest-live")
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines(["fingest: LIVE mode*"])


def test_missing_cloud_object_error(pytester):
    pytester.makeconftest(
        """
        from fingest import gcs_fixture

        @gcs_fixture("nobucket", "k.json")
        def missing(data):
            return data
        """
    )
    pytester.makepyfile("def test_it(missing): pass\n")
    result = pytester.runpytest("-p", "no:cacheprovider")
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*bucket 'nobucket' does not exist*"])
