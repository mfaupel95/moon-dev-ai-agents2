import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd

from src.agents.api import MoonDevAPI


class MoonDevAPICacheTests(unittest.TestCase):
    def test_fetch_csv_reuses_cache_within_ttl(self):
        api = MoonDevAPI(api_key='test-key', base_url='http://example.com', cache_ttl_seconds=300)
        api.base_dir = Path(tempfile.mkdtemp())
        api.session = MagicMock()
        api.session.get.return_value = MagicMock(
            content=b"symbol\nSOL\nBTC\n",
            raise_for_status=lambda: None,
        )

        first = api._fetch_csv('liq_data.csv')
        second = api._fetch_csv('liq_data.csv')

        self.assertIsNotNone(first)
        pd.testing.assert_frame_equal(first, second)
        self.assertEqual(api.session.get.call_count, 1)

    def test_fetch_csv_refreshes_after_ttl_expiry(self):
        api = MoonDevAPI(api_key='test-key', base_url='http://example.com', cache_ttl_seconds=0)
        api.base_dir = Path(tempfile.mkdtemp())
        api.session = MagicMock()
        api.session.get.return_value = MagicMock(
            content=b"symbol\nSOL\n",
            raise_for_status=lambda: None,
        )

        first = api._fetch_csv('liq_data.csv')
        second = api._fetch_csv('liq_data.csv')

        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertEqual(api.session.get.call_count, 2)


if __name__ == '__main__':
    unittest.main()
