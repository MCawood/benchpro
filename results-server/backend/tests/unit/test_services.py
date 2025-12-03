"""Unit tests for service layer."""

import pytest
from uuid import uuid4

from app.db.models import (
    Application,
    BenchmarkDefinition,
    FigureOfMerit,
    FomValueType,
    TaskRun,
    TaskStatus,
    User,
    UserRole,
)
from app.schemas.application import ApplicationCreate
from app.schemas.benchmark_definition import BenchmarkDefinitionCreate
from app.schemas.figure_of_merit import FigureOfMeritCreate
from app.services import (
    application_service,
    benchmark_definition_service,
    user_service,
    api_token_service,
)


class TestUserService:
    """Tests for UserService."""

    @pytest.mark.asyncio
    async def test_get_by_external_id(self, db_session, test_user):
        """Test fetching user by external ID."""
        user = await user_service.get_by_external_id(db_session, "test_user")
        assert user is not None
        assert user.external_id == "test_user"
        assert user.display_name == "Test User"

    @pytest.mark.asyncio
    async def test_get_by_external_id_not_found(self, db_session):
        """Test fetching non-existent user returns None."""
        user = await user_service.get_by_external_id(db_session, "nonexistent")
        assert user is None

    @pytest.mark.asyncio
    async def test_get_or_create_existing(self, db_session, test_user):
        """Test get_or_create returns existing user."""
        user, created = await user_service.get_or_create(
            db_session, external_id="test_user"
        )
        assert user.id == test_user.id
        assert created is False

    @pytest.mark.asyncio
    async def test_get_or_create_new(self, db_session):
        """Test get_or_create creates new user."""
        user, created = await user_service.get_or_create(
            db_session,
            external_id="new_user",
            display_name="New User",
            email="new@example.com",
        )
        assert user is not None
        assert user.external_id == "new_user"
        assert created is True


class TestApiTokenService:
    """Tests for ApiTokenService."""

    @pytest.mark.asyncio
    async def test_create_token(self, db_session, test_user):
        """Test creating a new API token."""
        from app.schemas.api_token import ApiTokenCreate

        token_create = ApiTokenCreate(name="Test Token")
        db_token, plain_token = await api_token_service.create(
            db_session, user_id=test_user.id, obj_in=token_create
        )

        assert db_token is not None
        assert db_token.name == "Test Token"
        assert db_token.user_id == test_user.id
        assert plain_token.startswith("bp_")
        assert db_token.revoked_at is None

    @pytest.mark.asyncio
    async def test_verify_token(self, db_session, test_user):
        """Test token verification."""
        from app.schemas.api_token import ApiTokenCreate

        token_create = ApiTokenCreate(name="Verify Test")
        db_token, plain_token = await api_token_service.create(
            db_session, user_id=test_user.id, obj_in=token_create
        )

        # Verify correct token
        assert api_token_service.verify_token(plain_token, db_token.token_hash)

        # Verify incorrect token
        assert not api_token_service.verify_token("wrong_token", db_token.token_hash)

    @pytest.mark.asyncio
    async def test_revoke_token(self, db_session, test_user):
        """Test revoking a token."""
        from app.schemas.api_token import ApiTokenCreate

        token_create = ApiTokenCreate(name="Revoke Test")
        db_token, _ = await api_token_service.create(
            db_session, user_id=test_user.id, obj_in=token_create
        )

        assert db_token.revoked_at is None

        revoked = await api_token_service.revoke(db_session, id=db_token.id)
        assert revoked is not None
        assert revoked.revoked_at is not None


class TestApplicationService:
    """Tests for ApplicationService."""

    @pytest.mark.asyncio
    async def test_create_application(self, db_session):
        """Test creating an application."""
        app_create = ApplicationCreate(
            label="test_app",
            version="1.0.0",
            system="test_system",
            architecture="x86_64",
        )
        app = await application_service.create(db_session, obj_in=app_create)

        assert app is not None
        assert app.label == "test_app"
        assert app.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_find_or_create_existing(self, db_session):
        """Test find_or_create returns existing application."""
        app_create = ApplicationCreate(
            label="find_test",
            version="1.0.0",
            system="test_system",
        )

        # Create first
        app1, created1 = await application_service.find_or_create(
            db_session, obj_in=app_create
        )
        assert created1 is True

        # Find existing
        app2, created2 = await application_service.find_or_create(
            db_session, obj_in=app_create
        )
        assert created2 is False
        assert app1.id == app2.id


class TestBenchmarkDefinitionService:
    """Tests for BenchmarkDefinitionService."""

    @pytest.mark.asyncio
    async def test_create_benchmark(self, db_session):
        """Test creating a benchmark definition."""
        bench_create = BenchmarkDefinitionCreate(
            label="test_benchmark",
            description="A test benchmark",
            default_primary_fom_name="performance",
        )
        bench = await benchmark_definition_service.create(db_session, obj_in=bench_create)

        assert bench is not None
        assert bench.label == "test_benchmark"
        assert bench.default_primary_fom_name == "performance"

    @pytest.mark.asyncio
    async def test_get_by_label(self, db_session):
        """Test fetching benchmark by label."""
        bench_create = BenchmarkDefinitionCreate(label="label_test")
        await benchmark_definition_service.create(db_session, obj_in=bench_create)

        found = await benchmark_definition_service.get_by_label(db_session, "label_test")
        assert found is not None
        assert found.label == "label_test"


class TestFigureOfMeritSchema:
    """Tests for FigureOfMerit schema validation."""

    def test_numeric_fom_creation(self):
        """Test creating a numeric FoM."""
        fom = FigureOfMeritCreate(
            name="performance",
            value_numeric=1000.5,
            unit="ops/sec",
            is_primary=True,
        )
        assert fom.name == "performance"
        assert fom.value_numeric == 1000.5
        assert fom.value_type == FomValueType.NUMERIC

    def test_string_fom_creation(self):
        """Test creating a string FoM."""
        fom = FigureOfMeritCreate(
            name="status",
            value_text="success",
            is_primary=False,
        )
        assert fom.name == "status"
        assert fom.value_text == "success"
        assert fom.value_type == FomValueType.STRING

    def test_fom_requires_value(self):
        """Test that FoM requires either numeric or text value."""
        with pytest.raises(ValueError):
            FigureOfMeritCreate(name="invalid", is_primary=False)

