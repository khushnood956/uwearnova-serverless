"""create_products_variants_and_images_tables

Revision ID: d4fc55d592df
Revises: 19b855e08445
Create Date: 2026-11-10 19:56:34.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4fc55d592df'
down_revision: Union[str, Sequence[str], None] = '19b855e08445'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. products table
    op.create_table(
        'products',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('category_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('subtitle', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('brand_label', sa.String(length=128), server_default='UniNova', nullable=False),
        sa.Column('status', sa.String(length=32), server_default='active', nullable=False),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('original_price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('is_new_arrival', sa.Boolean(), server_default=sa.text('0'), nullable=False),
        sa.Column('is_trending', sa.Boolean(), server_default=sa.text('0'), nullable=False),
        sa.Column('is_featured', sa.Boolean(), server_default=sa.text('0'), nullable=False),
        sa.Column('fabric_care', sa.Text(), nullable=True),
        sa.Column('delivery_notes', sa.String(length=500), nullable=True),
        sa.Column('rating', sa.Numeric(precision=3, scale=2), server_default='5.0', nullable=False),
        sa.Column('review_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], name=op.f('fk_products_category_id_categories'), ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_products')),
        sa.UniqueConstraint('slug', name=op.f('uq_products_slug')),
    )
    op.create_index(op.f('ix_products_id'), 'products', ['id'], unique=False)
    op.create_index(op.f('ix_products_category_id'), 'products', ['category_id'], unique=False)
    op.create_index(op.f('ix_products_name'), 'products', ['name'], unique=False)
    op.create_index(op.f('ix_products_slug'), 'products', ['slug'], unique=True)
    op.create_index(op.f('ix_products_status'), 'products', ['status'], unique=False)
    op.create_index(op.f('ix_products_price'), 'products', ['price'], unique=False)
    op.create_index(op.f('ix_products_is_new_arrival'), 'products', ['is_new_arrival'], unique=False)
    op.create_index(op.f('ix_products_is_trending'), 'products', ['is_trending'], unique=False)
    op.create_index(op.f('ix_products_is_featured'), 'products', ['is_featured'], unique=False)

    # 2. product_variants table
    op.create_table(
        'product_variants',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('product_id', sa.BigInteger(), nullable=False),
        sa.Column('sku', sa.String(length=64), nullable=False),
        sa.Column('size', sa.String(length=32), nullable=False),
        sa.Column('color_name', sa.String(length=64), nullable=False),
        sa.Column('color_hex', sa.String(length=16), nullable=True),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('compare_at_price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('inventory_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('in_stock', sa.Boolean(), server_default=sa.text('1'), nullable=False),
        sa.Column('weight_grams', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('1'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_product_variants_product_id_products'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_product_variants')),
        sa.UniqueConstraint('sku', name=op.f('uq_product_variants_sku')),
    )
    op.create_index(op.f('ix_product_variants_id'), 'product_variants', ['id'], unique=False)
    op.create_index(op.f('ix_product_variants_product_id'), 'product_variants', ['product_id'], unique=False)
    op.create_index(op.f('ix_product_variants_sku'), 'product_variants', ['sku'], unique=True)
    op.create_index(op.f('ix_product_variants_size'), 'product_variants', ['size'], unique=False)
    op.create_index(op.f('ix_product_variants_color_name'), 'product_variants', ['color_name'], unique=False)
    op.create_index(op.f('ix_product_variants_in_stock'), 'product_variants', ['in_stock'], unique=False)
    op.create_index(op.f('ix_product_variants_is_active'), 'product_variants', ['is_active'], unique=False)

    # 3. product_images table
    op.create_table(
        'product_images',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('product_id', sa.BigInteger(), nullable=False),
        sa.Column('image_url', sa.String(length=1024), nullable=False),
        sa.Column('alt_text', sa.String(length=255), nullable=True),
        sa.Column('sort_order', sa.Integer(), server_default='0', nullable=False),
        sa.Column('is_primary', sa.Boolean(), server_default=sa.text('0'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_product_images_product_id_products'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_product_images')),
    )
    op.create_index(op.f('ix_product_images_id'), 'product_images', ['id'], unique=False)
    op.create_index(op.f('ix_product_images_product_id'), 'product_images', ['product_id'], unique=False)

    # 4. product_collections join table
    op.create_table(
        'product_collections',
        sa.Column('product_id', sa.BigInteger(), nullable=False),
        sa.Column('collection_id', sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(['collection_id'], ['collections.id'], name=op.f('fk_product_collections_collection_id_collections'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_product_collections_product_id_products'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('product_id', 'collection_id', name=op.f('pk_product_collections')),
    )


def downgrade() -> None:
    op.drop_table('product_collections')
    op.drop_index(op.f('ix_product_images_product_id'), table_name='product_images')
    op.drop_index(op.f('ix_product_images_id'), table_name='product_images')
    op.drop_table('product_images')

    op.drop_index(op.f('ix_product_variants_is_active'), table_name='product_variants')
    op.drop_index(op.f('ix_product_variants_in_stock'), table_name='product_variants')
    op.drop_index(op.f('ix_product_variants_color_name'), table_name='product_variants')
    op.drop_index(op.f('ix_product_variants_size'), table_name='product_variants')
    op.drop_index(op.f('ix_product_variants_sku'), table_name='product_variants')
    op.drop_index(op.f('ix_product_variants_product_id'), table_name='product_variants')
    op.drop_index(op.f('ix_product_variants_id'), table_name='product_variants')
    op.drop_table('product_variants')

    op.drop_index(op.f('ix_products_is_featured'), table_name='products')
    op.drop_index(op.f('ix_products_is_trending'), table_name='products')
    op.drop_index(op.f('ix_products_is_new_arrival'), table_name='products')
    op.drop_index(op.f('ix_products_price'), table_name='products')
    op.drop_index(op.f('ix_products_status'), table_name='products')
    op.drop_index(op.f('ix_products_slug'), table_name='products')
    op.drop_index(op.f('ix_products_name'), table_name='products')
    op.drop_index(op.f('ix_products_category_id'), table_name='products')
    op.drop_index(op.f('ix_products_id'), table_name='products')
    op.drop_table('products')
