"""Add RolePermissions

Revision ID: 5e7042396d4b
Revises: 25a556898423
Create Date: 2024-04-04 15:15:21.384488

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from datetime import datetime

from ORM.auto_grader_orms import Permission, Role, RolePermission
from ORM.role_constants import Roles, permission_names


# revision identifiers, used by Alembic.
revision: str = '5e7042396d4b'
down_revision: Union[str, None] = '25a556898423'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('role_permission', 'name')

    bind = op.get_bind()
    session = Session(bind=bind)

    role_permissions = []

    admin_role_id = session.query(Role).filter_by(name=Roles.ADMIN.value).scalar().id

    permissions = session.query(Permission).filter(Permission.name.in_(
        permission_names[Roles.ADMIN.value]
    )).all()

    for permission in permissions:
        role_permissions.append(RolePermission(
            role_id=admin_role_id,
            permission_id=permission.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ))

    session.add_all(role_permissions)
    session.commit()


def downgrade() -> None:
    op.add_column('role_permission', sa.Column('name', sa.String(length=50), nullable=False))
    bind = op.get_bind()
    session = Session(bind=bind)
    session.query(RolePermission).delete()
    session.commit()

