import sys
import types
import unittest
from unittest.mock import Mock

requests = types.ModuleType('requests')
requests.post = Mock(return_value={'id': 'synthetic-order'})
sys.modules['requests'] = requests
from client import create_order


class RequestMigrationTest(unittest.TestCase):
    def test_current_contract_requires_customer_id(self):
        requests.post.reset_mock()
        create_order('synthetic-customer')
        requests.post.assert_called_once_with('https://api.example.com/v1/orders', json={'customer_id': 'synthetic-customer'})
