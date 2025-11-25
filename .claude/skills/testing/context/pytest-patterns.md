# Pytest Patterns and Best Practices

Common pytest patterns for high-quality test suites in Python projects.

## AAA Pattern (Arrange-Act-Assert)

The fundamental test structure pattern:

```python
def test_user_creation():
    # Arrange - Set up test data and dependencies
    username = "testuser"
    email = "test@example.com"

    # Act - Execute the behavior being tested
    user = create_user(username, email)

    # Assert - Verify expected outcomes
    assert user.username == username
    assert user.email == email
    assert user.is_active is True
```

## Fixture Patterns

### Shared Setup with Function-Scoped Fixtures

```python
@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    return User(username="testuser", email="test@example.com")

def test_user_email(sample_user):
    assert "@" in sample_user.email

def test_user_username(sample_user):
    assert len(sample_user.username) > 0
```

### Module-Scoped Fixtures for Expensive Setup

```python
@pytest.fixture(scope="module")
def database_connection():
    """Create database connection once per module."""
    conn = create_db_connection()
    yield conn
    conn.close()
```

### Session-Scoped for One-Time Setup

```python
@pytest.fixture(scope="session")
def test_database():
    """Create test database once per session."""
    db = create_test_database()
    yield db
    db.teardown()
```

## Parametrization Patterns

### Testing Multiple Inputs

```python
@pytest.mark.parametrize("input,expected", [
    (5, 25),      # 5² = 25
    (0, 0),       # 0² = 0
    (-3, 9),      # (-3)² = 9
    (10, 100),    # 10² = 100
])
def test_square(input, expected):
    assert square(input) == expected
```

### Multiple Parameters

```python
@pytest.mark.parametrize("width,height,expected_area", [
    (5, 10, 50),
    (3, 7, 21),
    (0, 5, 0),
])
def test_rectangle_area(width, height, expected_area):
    rect = Rectangle(width, height)
    assert rect.area() == expected_area
```

### Combining Parameters

```python
@pytest.mark.parametrize("format", ["json", "xml", "csv"])
@pytest.mark.parametrize("compression", [True, False])
def test_export_formats(format, compression):
    # Tests all combinations: (json, True), (json, False), (xml, True), etc.
    result = export_data(format=format, compression=compression)
    assert result is not None
```

## Exception Testing Patterns

### Basic Exception Testing

```python
def test_invalid_input_raises_error():
    with pytest.raises(ValueError):
        process_data(invalid_input)
```

### Testing Exception Messages

```python
def test_error_message():
    with pytest.raises(ValueError, match="must be positive"):
        create_user(age=-5)
```

### Testing Exception Details

```python
def test_exception_details():
    with pytest.raises(ValidationError) as exc_info:
        validate_email("invalid-email")

    assert "email" in str(exc_info.value).lower()
    assert exc_info.type is ValidationError
```

## Mocking Patterns

### Mocking External Dependencies

```python
def test_api_call(mocker):
    # Mock external API call
    mock_get = mocker.patch('requests.get')
    mock_get.return_value.json.return_value = {"status": "success"}

    result = fetch_data_from_api()

    assert result["status"] == "success"
    mock_get.assert_called_once()
```

### Mocking Methods

```python
def test_database_save(mocker):
    mock_save = mocker.patch.object(Database, 'save')

    user = User(username="test")
    user.save_to_db()

    mock_save.assert_called_once_with(user)
```

### Spy Pattern (Partial Mocking)

```python
def test_with_spy(mocker):
    spy = mocker.spy(Calculator, 'add')

    calc = Calculator()
    result = calc.add(2, 3)

    assert result == 5
    spy.assert_called_once_with(2, 3)
```

## Fixture Composition Patterns

### Fixtures Using Other Fixtures

```python
@pytest.fixture
def database():
    return Database()

@pytest.fixture
def user_repository(database):
    return UserRepository(database)

def test_user_creation(user_repository):
    user = user_repository.create("testuser")
    assert user is not None
```

### Factory Fixtures

```python
@pytest.fixture
def user_factory():
    """Factory fixture for creating multiple users."""
    users = []

    def _create_user(username="test", email=None):
        user = User(username=username, email=email or f"{username}@example.com")
        users.append(user)
        return user

    yield _create_user

    # Cleanup all created users
    for user in users:
        user.delete()

def test_multiple_users(user_factory):
    user1 = user_factory("alice")
    user2 = user_factory("bob")

    assert user1.username != user2.username
```

## Marker Patterns

### Custom Markers

```python
@pytest.mark.unit
def test_pure_function():
    assert add(2, 3) == 5

@pytest.mark.integration
def test_database_integration(database):
    result = database.query("SELECT 1")
    assert result is not None

@pytest.mark.slow
def test_expensive_operation():
    result = process_large_dataset()
    assert result is not None
```

### Conditional Skipping

```python
@pytest.mark.skipif(sys.platform == "win32", reason="Unix only test")
def test_unix_specific():
    assert os.path.exists("/etc")

@pytest.mark.skipif(not has_feature("advanced"), reason="Requires advanced feature")
def test_advanced_feature():
    use_advanced_feature()
```

## Test Class Organization

### Grouping Related Tests

```python
class TestUserAuthentication:
    """Group authentication-related tests."""

    def test_valid_login(self):
        user = login("user", "password")
        assert user.is_authenticated

    def test_invalid_password(self):
        with pytest.raises(AuthenticationError):
            login("user", "wrong_password")

    def test_locked_account(self):
        with pytest.raises(AccountLocked):
            login("locked_user", "password")
```

### Shared Fixtures in Test Classes

```python
class TestUserAPI:
    @pytest.fixture(autouse=True)
    def setup(self):
        """Auto-used fixture for all tests in this class."""
        self.client = APIClient()
        self.client.authenticate()
        yield
        self.client.logout()

    def test_get_user(self):
        response = self.client.get("/users/1")
        assert response.status_code == 200

    def test_create_user(self):
        response = self.client.post("/users", data={"username": "new"})
        assert response.status_code == 201
```

## Property-Based Testing Patterns

### Using Hypothesis

```python
from hypothesis import given, strategies as st

@given(st.integers(), st.integers())
def test_addition_commutative(a, b):
    """Test that addition is commutative."""
    assert a + b == b + a

@given(st.lists(st.integers()))
def test_reversing_twice_returns_original(lst):
    """Test that reversing a list twice returns original."""
    assert list(reversed(list(reversed(lst)))) == lst

@given(st.text(min_size=1))
def test_string_uppercase_lowercase(s):
    """Test string case operations."""
    assert s.upper().lower() == s.lower()
```

## Async Testing Patterns

### Testing Async Functions

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_operation()
    assert result is not None

@pytest.mark.asyncio
async def test_async_with_fixture(async_database):
    result = await async_database.query("SELECT 1")
    assert result is not None
```

### Async Fixtures

```python
@pytest.fixture
async def async_client():
    client = AsyncHTTPClient()
    await client.connect()
    yield client
    await client.disconnect()
```

## Temporary File Patterns

### Using tmp_path Fixture

```python
def test_file_creation(tmp_path):
    """Test file creation with temporary directory."""
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("test content")

    assert file_path.exists()
    assert file_path.read_text() == "test content"

def test_directory_operations(tmp_path):
    """Test directory operations."""
    subdir = tmp_path / "subdir"
    subdir.mkdir()

    (subdir / "file.txt").write_text("content")

    assert subdir.is_dir()
    assert len(list(subdir.iterdir())) == 1
```

## Test Data Patterns

### Inline Test Data

```python
def test_with_inline_data():
    test_users = [
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
    ]

    for user_data in test_users:
        user = create_user(**user_data)
        assert user.name == user_data["name"]
```

### External Test Data Files

```python
import json
from pathlib import Path

@pytest.fixture
def test_data():
    data_file = Path(__file__).parent / "test_data.json"
    return json.loads(data_file.read_text())

def test_with_external_data(test_data):
    for item in test_data["items"]:
        assert process_item(item) is not None
```

## Coverage Optimization Patterns

### Testing Error Paths

```python
def test_happy_path():
    result = process_data(valid_input)
    assert result.success

def test_error_path_invalid_input():
    result = process_data(invalid_input)
    assert not result.success
    assert "invalid" in result.error_message.lower()

def test_error_path_missing_data():
    with pytest.raises(ValueError):
        process_data(None)
```

### Boundary Testing

```python
@pytest.mark.parametrize("value,expected", [
    (-1, False),    # Below minimum
    (0, True),      # Minimum boundary
    (50, True),     # Within range
    (100, True),    # Maximum boundary
    (101, False),   # Above maximum
])
def test_value_in_range(value, expected):
    assert is_valid_percentage(value) == expected
```

---

*These patterns ensure high-quality, maintainable test suites with comprehensive coverage.*
