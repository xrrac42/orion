-- Migration: 2025-08-29
-- Objetivo: adicionar colunas para armazenar o JSON original do parser e associar file_uploads

BEGIN;

-- 1) Adiciona coluna para guardar o JSON bruto da análise (última página / resumo)
ALTER TABLE public.monthly_analyses
  ADD COLUMN IF NOT EXISTS raw_analysis jsonb NULL;

-- 2) Adiciona coluna opcional para referenciar o upload que gerou a análise
-- Nota: a coluna `file_uploads.id` é do tipo uuid no schema atual, então criamos
-- file_upload_id como uuid para garantir compatibilidade com a FK.
ALTER TABLE public.monthly_analyses
  ADD COLUMN IF NOT EXISTS file_upload_id uuid NULL;

-- 3) Se existir a tabela file_uploads, cria FK (seguro: só cria se a tabela existir)
DO $$
BEGIN
  -- Só tenta criar a FK se a tabela file_uploads existir
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'file_uploads') THEN
    -- Verifica tipos das colunas antes de criar a FK (evita bigint vs uuid incompatível)
    DECLARE
      v_type_file_uploads_id text;
      v_type_monthly_file_upload_id text;
    BEGIN
      SELECT data_type INTO v_type_file_uploads_id
      FROM information_schema.columns
      WHERE table_schema = 'public' AND table_name = 'file_uploads' AND column_name = 'id'
      LIMIT 1;

      SELECT data_type INTO v_type_monthly_file_upload_id
      FROM information_schema.columns
      WHERE table_schema = 'public' AND table_name = 'monthly_analyses' AND column_name = 'file_upload_id'
      LIMIT 1;

      IF v_type_file_uploads_id IS NOT NULL AND v_type_monthly_file_upload_id IS NOT NULL AND v_type_file_uploads_id = v_type_monthly_file_upload_id THEN
        IF NOT EXISTS (
          SELECT 1 FROM information_schema.table_constraints
          WHERE constraint_name = 'monthly_analyses_file_upload_id_fkey' AND table_schema = 'public'
        ) THEN
          EXECUTE 'ALTER TABLE public.monthly_analyses ADD CONSTRAINT monthly_analyses_file_upload_id_fkey FOREIGN KEY (file_upload_id) REFERENCES public.file_uploads(id) ON DELETE SET NULL';
        END IF;
      ELSE
        -- Tipos diferentes ou não encontrados; pula criação da FK para evitar erro
        RAISE NOTICE 'Skipping creation of FK monthly_analyses_file_upload_id_fkey: file_uploads.id type = %, monthly_analyses.file_upload_id type = %', v_type_file_uploads_id, v_type_monthly_file_upload_id;
      END IF;
    END;
  END IF;
END$$;

COMMIT;
