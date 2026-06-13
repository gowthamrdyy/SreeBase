import os
import pytest
from sreebase.query.executor import Executor
from sreebase.errors import ExecutionError
from reddybase.client.driver import _validate_identifier, _escape_string, ReddyBaseError

@pytest.fixture
def executor(tmp_path):
    data_dir = str(tmp_path / "data")
    os.makedirs(data_dir, exist_ok=True)
    exe = Executor(data_dir=data_dir)
    yield exe
    exe.close()

class TestRBAC:
    def test_bootstrap_first_user(self, executor):
        # Database is empty. Anonymous should be able to create the FIRST user.
        res = executor.execute('create user admin password "secret" role admin\n', role=None)
        assert res["status"] == "ok"
        
        # After bootstrap, anonymous cannot create another user
        with pytest.raises(ExecutionError, match="Authentication required"):
            executor.execute('create user guest password "123" role read\n', role=None)

    def test_anonymous_cannot_write(self, executor):
        with pytest.raises(ExecutionError, match="Authentication required"):
            executor.execute('insert into collection\n    val = 1\n', role=None)

    def test_read_role_limitations(self, executor):
        # Bootstrap first
        executor.execute('create user admin password "secret" role admin\n', role=None)
        
        # Read role CAN read normal collections
        executor.execute('get normal_collection\n', role="read")
        
        # Read role CANNOT write
        with pytest.raises(ExecutionError, match="cannot execute InsertStatement"):
            executor.execute('insert into normal\n    val = 1\n', role="read")
            
        # Read role CANNOT access _system collections
        with pytest.raises(ExecutionError, match="only 'admin' can access system collections"):
            executor.execute('get _system.users\n', role="read")

    def test_login_hashing(self, executor):
        executor.execute('create user admin password "secret" role admin\n', role=None)
        
        # Login with correct password works
        res = executor.execute('login admin password "secret"\n', role=None)
        assert res["status"] == "ok"
        
        # Login with wrong password fails
        with pytest.raises(ExecutionError, match="Invalid username or password"):
            executor.execute('login admin password "wrong"\n', role=None)

class TestSDKInjection:
    def test_escape_string(self):
        malicious = 'hello"\nworld\\'
        escaped = _escape_string(malicious)
        assert escaped == 'hello\\"\\nworld\\\\'

    def test_validate_identifier(self):
        _validate_identifier("valid_name")
        _validate_identifier("_system.collections")
        
        with pytest.raises(ReddyBaseError):
            _validate_identifier("invalid name")
            
        with pytest.raises(ReddyBaseError):
            _validate_identifier("name\n")
