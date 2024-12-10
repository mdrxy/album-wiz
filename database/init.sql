-- \c vinyl_db;

-- Create the artists table to store artist metadata
CREATE TABLE artists (
    id SERIAL PRIMARY KEY,               -- Unique identifier for the artist
    name VARCHAR(255) NOT NULL,          -- Artist name
    genre VARCHAR(100),                  -- Genre of the artist
    popularity_score INT,                -- Popularity score (e.g., from Spotify/Last.fm)
    created_at TIMESTAMP DEFAULT NOW(),  -- Record creation timestamp
    updated_at TIMESTAMP DEFAULT NOW()   -- Last updated timestamp
);

-- Create the albums table to store album metadata
CREATE TABLE albums (
    id SERIAL PRIMARY KEY,               -- Unique identifier for the album
    title VARCHAR(255) NOT NULL,         -- Album title
    artist_id INT NOT NULL,              -- Foreign key to the artist (from the artists table)
    release_date DATE,                   -- Release date of the album (ISO-8601 format?)
    genre VARCHAR(100),                  -- Genre of the album
    cover_image_url TEXT,                -- URL for the album cover image
    popularity_score INT,                -- Popularity score (e.g., from Spotify/Last.fm)
    created_at TIMESTAMP DEFAULT NOW(),  -- Record creation timestamp
    updated_at TIMESTAMP DEFAULT NOW(),  -- Last updated timestamp
    FOREIGN KEY (artist_id) REFERENCES artists (id) ON DELETE CASCADE
);

-- -- Create the tracks table to store track details
-- CREATE TABLE tracks (
--     id SERIAL PRIMARY KEY,               -- Unique identifier for the track
--     album_id INT NOT NULL,               -- Foreign key to the album
--     title VARCHAR(255) NOT NULL,         -- Track title
--     duration_seconds INT,                -- Duration of the track in seconds
--     explicit BOOLEAN DEFAULT FALSE,      -- Indicates if the track contains explicit content
--     created_at TIMESTAMP DEFAULT NOW(),  -- Record creation timestamp
--     updated_at TIMESTAMP DEFAULT NOW(),  -- Last updated timestamp
--     FOREIGN KEY (album_id) REFERENCES albums (id) ON DELETE CASCADE
-- );

-- Create the queries table to cache query results
CREATE TABLE queries (
    id SERIAL PRIMARY KEY,               -- Unique identifier for the query
    query_text TEXT NOT NULL,            -- Text of the search query
    result JSONB NOT NULL,               -- JSON object containing the query result
    created_at TIMESTAMP DEFAULT NOW(),  -- Record creation timestamp
    updated_at TIMESTAMP DEFAULT NOW()   -- Last updated timestamp
);

-- Create an index on the queries table for efficient search
CREATE INDEX idx_query_text ON queries (query_text);

-- Add an extension for vectorized queries (pgvector)
CREATE EXTENSION IF NOT EXISTS vector;

-- Add a column for latent vector embeddings in the albums table for vector search
ALTER TABLE albums ADD COLUMN embedding VECTOR(256); -- TODO: May need to update dimension size?

-- Insert example data (optional for development)
INSERT INTO artists (name, genre, popularity_score) VALUES
('Radiohead', 'Alternative Rock', 90),
('Kendrick Lamar', 'Hip-Hop', 95),
('Taylor Swift', 'Pop', 98);

INSERT INTO albums (title, artist_id, release_date, genre, cover_image_url, popularity_score) VALUES
('OK Computer', 1, '1997-05-21', 'Alternative Rock', 'https://example.com/ok_computer.jpg', 95),
('DAMN.', 2, '2017-04-14', 'Hip-Hop', 'https://example.com/damn.jpg', 94),
('1989', 3, '2014-10-27', 'Pop', 'https://example.com/1989.jpg', 97);

-- INSERT INTO tracks (album_id, title, duration_seconds, explicit) VALUES
-- (1, 'Paranoid Android', 388, FALSE),
-- (2, 'HUMBLE.', 177, TRUE),
-- (3, 'Shake It Off', 242, FALSE);