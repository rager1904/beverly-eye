"""Create the RAG vector table and upgrade legacy float-array embeddings.

Revision ID: 013
Revises: 012
"""
from alembic import op

revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.execute('''CREATE TABLE IF NOT EXISTS document_embeddings (
        id SERIAL PRIMARY KEY, external_id VARCHAR(255), content TEXT NOT NULL,
        title VARCHAR(500), source_type VARCHAR(100), source_url VARCHAR(1024),
        language VARCHAR(10), hospital_id VARCHAR(100), department VARCHAR(200),
        specialty VARCHAR(200), author VARCHAR(255), published_date VARCHAR(50),
        version VARCHAR(50), metadata JSONB, embedding vector(1024) NOT NULL,
        sparse_vector JSONB, created_at VARCHAR(50))''')
    op.execute('''DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = current_schema() AND table_name = 'document_embeddings'
                   AND column_name = 'embedding' AND data_type = 'ARRAY') THEN
            ALTER TABLE document_embeddings ALTER COLUMN embedding
                TYPE vector(1024) USING embedding::vector(1024);
        END IF;
    END $$''')
    op.execute('CREATE INDEX IF NOT EXISTS ix_document_embeddings_hospital_id ON document_embeddings (hospital_id)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_doc_emb_hnsw ON document_embeddings USING hnsw (embedding vector_cosine_ops) WITH (m = 32, ef_construction = 200)')
    op.execute("CREATE INDEX IF NOT EXISTS idx_doc_emb_content_gin ON document_embeddings USING gin(to_tsvector('english', content))")


def downgrade():
    # Retain documents. The old model stored float arrays, so restore that type.
    op.execute('DROP INDEX IF EXISTS idx_doc_emb_hnsw')
    op.execute('ALTER TABLE document_embeddings ALTER COLUMN embedding TYPE double precision[] USING embedding::real[]::double precision[]')
