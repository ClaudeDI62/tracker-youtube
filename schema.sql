-- YouTube Recommendation Tracker — Database Schema
-- Run this in the Supabase SQL Editor (Dashboard > SQL Editor > New query)

-- 1. Channels
CREATE TABLE channels (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        TEXT NOT NULL,
    url         TEXT NOT NULL,
    channel_id  TEXT NOT NULL UNIQUE,
    language    TEXT NOT NULL DEFAULT 'EN',
    market_default TEXT NOT NULL DEFAULT 'USA',
    active      BOOLEAN NOT NULL DEFAULT TRUE
);

-- 2. Videos
CREATE TABLE videos (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    channel_id      BIGINT NOT NULL REFERENCES channels(id),
    video_id        TEXT NOT NULL UNIQUE,
    title           TEXT NOT NULL,
    url             TEXT NOT NULL,
    published_at    TIMESTAMPTZ NOT NULL,
    transcript_source TEXT NOT NULL DEFAULT 'none'
        CHECK (transcript_source IN ('subs', 'whisper', 'none')),
    processed_at    TIMESTAMPTZ,
    status          TEXT NOT NULL DEFAULT 'new'
        CHECK (status IN ('new', 'transcribed', 'extracted', 'done', 'error'))
);

-- 3. Recommendations
CREATE TABLE recommendations (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    video_id        BIGINT NOT NULL REFERENCES videos(id),
    asset_name      TEXT NOT NULL,
    ticker          TEXT,
    isin            TEXT,
    asset_type      TEXT NOT NULL
        CHECK (asset_type IN ('stock', 'etf', 'index', 'commodity')),
    action          TEXT NOT NULL
        CHECK (action IN ('buy', 'sell', 'hold')),
    target_price    NUMERIC,
    horizon_text    TEXT,
    rationale       TEXT,
    quote           TEXT,
    video_timestamp TEXT,
    reco_date       DATE NOT NULL,
    price_at_reco   NUMERIC,
    benchmark_ticker TEXT,
    conditional     BOOLEAN NOT NULL DEFAULT FALSE,
    status          TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'evaluated', 'quarantined'))
);

-- 4. Prices (daily close prices cache)
CREATE TABLE prices (
    ticker  TEXT NOT NULL,
    date    DATE NOT NULL,
    close   NUMERIC NOT NULL,
    PRIMARY KEY (ticker, date)
);

-- 5. Evaluations
CREATE TABLE evaluations (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    recommendation_id   BIGINT NOT NULL REFERENCES recommendations(id),
    horizon_days        INT NOT NULL CHECK (horizon_days IN (7, 30, 90)),
    asset_return_pct    NUMERIC,
    benchmark_return_pct NUMERIC,
    excess_return_pct   NUMERIC,
    hit                 BOOLEAN,
    evaluated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (recommendation_id, horizon_days)
);

-- 6. Ratings (per channel, per horizon)
CREATE TABLE ratings (
    channel_id      BIGINT NOT NULL REFERENCES channels(id),
    horizon_days    INT NOT NULL CHECK (horizon_days IN (7, 30, 90)),
    n_recos         INT NOT NULL DEFAULT 0,
    hit_rate        NUMERIC,
    wilson_lb       NUMERIC,
    avg_excess_return NUMERIC,
    score           NUMERIC,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (channel_id, horizon_days)
);

-- 7. Quarantine (failed extractions)
CREATE TABLE quarantine (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    video_id            BIGINT NOT NULL REFERENCES videos(id),
    raw_extraction_json JSONB,
    reason              TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 8. Job runs (monitoring)
CREATE TABLE job_runs (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status      TEXT NOT NULL CHECK (status IN ('success', 'partial', 'failed')),
    notes       TEXT
);

-- Indexes for common queries
CREATE INDEX idx_videos_channel ON videos(channel_id);
CREATE INDEX idx_videos_status ON videos(status);
CREATE INDEX idx_recommendations_video ON recommendations(video_id);
CREATE INDEX idx_recommendations_status ON recommendations(status);
CREATE INDEX idx_evaluations_reco ON evaluations(recommendation_id);
CREATE INDEX idx_prices_ticker_date ON prices(ticker, date);
