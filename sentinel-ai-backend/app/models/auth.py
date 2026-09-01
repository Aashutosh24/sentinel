"""
Platform authentication. Not derived from any dataset — invented for
Step 7 (JWT + RBAC foundation). Uses a UUID PK (UUIDPKMixin) since there
is no natural business key, per the approved architecture's default.
"""
from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base
from app.models.enums import UserRole
from app.models.mixins import TimestampMixin, UUIDPKMixin


class User(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=False, length=30),
        nullable=False,
        default=UserRole.EMPLOYEE,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Optional link to a real Employee row (from dataset1) so an "employee"-role
    # login can be traced back to their HR record. Nullable: admin/compliance/
    # security/auditor accounts are not necessarily also ingested Employees.
    employee_id: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("employees.employee_id", ondelete="SET NULL"), nullable=True, index=True
    )
