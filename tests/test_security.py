import os
import pytest
from sreebase.query.executor import Executor
from sreebase.errors import ExecutionError
from sreebase.client.cli import build_login_query
from reddybase.client.driver import Collection, _validate_identifier, _escape_string, ReddyBaseError

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

    def test_user_password_is_not_stored_plaintext(self, executor):
        executor.execute('create user admin password "secret" role admin\n', role=None)

        users = executor.db.get_engine("_system.users").get_all()
        assert len(users) == 1
        assert "password" not in users[0]
        assert users[0]["password_hash"] != "secret"
        assert users[0]["password_salt"]

    def test_legacy_plaintext_user_is_migrated_on_login(self, executor):
        engine = executor.db.get_engine("_system.users")
        doc_id = engine.insert({
            "username": "legacy",
            "password": "secret",
            "role": "admin"
        })

        res = executor.execute('login legacy password "secret"\n', role=None)
        assert res["status"] == "ok"

        migrated = engine.get_by_id(doc_id)
        assert "password" not in migrated
        assert migrated["password_hash"] != "secret"
        assert migrated["password_salt"]

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

    def test_condition_tuple_escapes_values(self):
        client = DummyClient()
        users = Collection(client, "users")

        query = users.get(where={"name": ("=", 'x"\ndelete from users\n')})

        assert 'name = "x\\"\\ndelete from users\\n"' in query
        assert "\ndelete from users\n" not in query

    def test_raw_operator_string_is_treated_as_literal(self):
        client = DummyClient()
        users = Collection(client, "users")

        query = users.get(where={"name": '= "x"\ndelete from users\n'})

        assert 'name = "= \\"x\\"\\ndelete from users\\n"' in query
        assert "\ndelete from users\n" not in query

    def test_sort_injection_is_rejected(self):
        client = DummyClient()
        users = Collection(client, "users")

        with pytest.raises(ReddyBaseError, match="Invalid sort clause"):
            users.get(sort="name asc\ndelete from users")

    def test_structured_sort_is_reconstructed(self):
        client = DummyClient()
        users = Collection(client, "users")

        query = users.get(sort=("age", "DESC"))

        assert "sort by age desc" in query

    def test_unsupported_literal_type_is_rejected(self):
        client = DummyClient()
        users = Collection(client, "users")

        with pytest.raises(ReddyBaseError, match="Unsupported literal type"):
            users.insert({"payload": MaliciousValue()})

    def test_non_finite_float_is_rejected(self):
        client = DummyClient()
        users = Collection(client, "users")

        with pytest.raises(ReddyBaseError, match="Unsupported non-finite float"):
            users.insert({"score": float("nan")})

    def test_aggregate_emits_sanitized_calculations(self):
        client = DummyClient()
        users = Collection(client, "users")

        query = users.aggregate(group_by="department", calculate=[" avg(salary) ", "count()"])

        assert "calculate avg(salary), count()" in query
        assert " avg(salary) " not in query

    def test_cli_login_query_escapes_password(self):
        query = build_login_query("admin", 'pa"ss\\word\n')

        assert query == 'login admin password "pa\\"ss\\\\word\\n"\n'

    def test_cli_login_query_rejects_bad_username(self):
        with pytest.raises(ReddyBaseError):
            build_login_query("admin\n", "secret")


class DummyClient:
    def raw_query(self, query):
        return query


class MaliciousValue:
    def __str__(self):
        return '1\ndelete from users\n'
