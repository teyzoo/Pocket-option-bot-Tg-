"""Initial database schema."""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),
        sa.Column(
            "telegram_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "username",
            sa.String(255),
            nullable=True,
        ),
        sa.Column(
            "first_name",
            sa.String(255),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "blacklist_reason",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "is_auto_signals_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_users_telegram_id",
        "users",
        ["telegram_id"],
        unique=True,
    )

    op.create_index(
        "ix_users_status",
        "users",
        ["status"],
    )

    op.create_table(
        "join_requests",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),
        sa.Column(
            "telegram_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "processed_by",
            sa.BigInteger(),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_join_requests_telegram_id",
        "join_requests",
        ["telegram_id"],
    )

    op.create_index(
        "ix_join_requests_status",
        "join_requests",
        ["status"],
    )

    op.create_table(
        "signals",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),
        sa.Column(
            "pair",
            sa.String(30),
            nullable=False,
        ),
        sa.Column(
            "direction",
            sa.String(10),
            nullable=False,
        ),
        sa.Column(
            "expiry_minutes",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "quality",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "entry_price",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "close_price",
            sa.Float(),
            nullable=True,
        ),
        sa.Column(
            "result",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "source",
            sa.String(30),
            nullable=False,
            server_default="manual",
        ),
        sa.Column(
            "reasons",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_signals_pair",
        "signals",
        ["pair"],
    )

    op.create_index(
        "ix_signals_result",
        "signals",
        ["result"],
    )

    op.create_table(
        "signal_recipients",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),
        sa.Column(
            "signal_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "telegram_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "message_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_signal_recipients_signal_id",
        "signal_recipients",
        ["signal_id"],
    )

    op.create_index(
        "ix_signal_recipients_telegram_id",
        "signal_recipients",
        ["telegram_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_signal_recipients_telegram_id",
        table_name="signal_recipients",
    )

    op.drop_index(
        "ix_signal_recipients_signal_id",
        table_name="signal_recipients",
    )

    op.drop_table(
        "signal_recipients"
    )

    op.drop_index(
        "ix_signals_result",
        table_name="signals",
    )

    op.drop_index(
        "ix_signals_pair",
        table_name="signals",
    )

    op.drop_table(
        "signals"
    )

    op.drop_index(
        "ix_join_requests_status",
        table_name="join_requests",
    )

    op.drop_index(
        "ix_join_requests_telegram_id",
        table_name="join_requests",
    )

    op.drop_table(
        "join_requests"
    )

    op.drop_index(
        "ix_users_status",
        table_name="users",
    )

    op.drop_index(
        "ix_users_telegram_id",
        table_name="users",
    )

    op.drop_table(
        "users"
    )
