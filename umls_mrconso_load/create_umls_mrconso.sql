-- PostgreSQL 14 DDL for UMLS MRCONSO (2025AB)
-- Source for field order and element definitions: UMLS Reference Manual + Columns/Data Elements.

--ran via psql
CREATE SCHEMA IF NOT EXISTS umls;

CREATE TABLE IF NOT EXISTS umls.mrconso (
    cui      CHAR(8)        NOT NULL,
    lat      CHAR(3)        NOT NULL,
    ts       CHAR(1)        NOT NULL,
    lui      VARCHAR(10)    NOT NULL,
    stt      VARCHAR(3)     NOT NULL,
    sui      VARCHAR(10)    NOT NULL,
    ispref   CHAR(1)        NOT NULL,
    aui      VARCHAR(9)     NOT NULL,
    saui     VARCHAR(100),
    scui     VARCHAR(100),
    sdui     VARCHAR(100),
    sab      VARCHAR(40)    NOT NULL,
    tty      VARCHAR(20)    NOT NULL,
    code     VARCHAR(100)   NOT NULL,
    str      VARCHAR(3000)  NOT NULL,
    srl      INTEGER        NOT NULL,
    suppress CHAR(1)        NOT NULL,
    cvf      VARCHAR(50)
);

-- Common access patterns for MRCONSO lookups.
-- ran manually via dbeaver 02/27/2026
CREATE INDEX IF NOT EXISTS idx_mrconso_cui ON umls.mrconso (cui);
CREATE INDEX IF NOT EXISTS idx_mrconso_aui ON umls.mrconso (aui);
CREATE INDEX IF NOT EXISTS idx_mrconso_lui ON umls.mrconso (lui);
CREATE INDEX IF NOT EXISTS idx_mrconso_sui ON umls.mrconso (sui);
CREATE INDEX IF NOT EXISTS idx_mrconso_sab_tty_code ON umls.mrconso (sab, tty, code);
CREATE INDEX IF NOT EXISTS idx_mrconso_str ON umls.mrconso (str);