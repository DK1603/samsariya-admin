import pytest
from utils.helpers import is_admin

def test_is_admin():
    assert is_admin(123456789) is True
    assert is_admin(111111111) is False 