-- Add an extension for vectorized queries (pgvector)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create the artists table to store artist metadata
CREATE TABLE artists (
    id SERIAL PRIMARY KEY,               -- Unique identifier for the artist
    name VARCHAR(255) UNIQUE NOT NULL,   -- Artist name
    genre VARCHAR(100),                  -- Genre of the artist
    created_at TIMESTAMP DEFAULT NOW(),  -- Record creation timestamp
    updated_at TIMESTAMP DEFAULT NOW()   -- Last updated timestamp
);

-- Create the albums table to store album metadata
CREATE TABLE albums (
    id SERIAL PRIMARY KEY,               -- Unique identifier for the album (record ID)
    title VARCHAR(255) UNIQUE NOT NULL,  -- Album title
    artist_id INT NOT NULL,              -- Foreign key to the artist (from the artists table)
    release_date DATE,                   -- Release date of the album
    genres VARCHAR(255),                 -- Genre of the album
    duration_seconds INT,                -- Total duration of the album in seconds
    cover_image TEXT,                    -- Cover image file path
                                         -- Assuming all containers use /media as the root directory
    total_tracks INT DEFAULT 0,          -- Total number of tracks for the album
    embedding VECTOR(256),               -- Vectorized representation for the album (initially empty)
    created_at TIMESTAMP DEFAULT NOW(),  -- Record creation timestamp
    updated_at TIMESTAMP DEFAULT NOW(),  -- Last updated timestamp
    FOREIGN KEY (artist_id) REFERENCES artists (id) ON DELETE CASCADE
);

-- Create the tracks table to store track details
CREATE TABLE tracks (
    id SERIAL PRIMARY KEY,               -- Unique identifier for the track
    album_id INT NOT NULL,               -- Foreign key to the album
    title VARCHAR(255) NOT NULL,         -- Track title
    duration_seconds INT,                -- Duration of the track in seconds
    explicit BOOLEAN,                    -- Indicates if the track contains explicit content
    created_at TIMESTAMP DEFAULT NOW(),  -- Record creation timestamp
    updated_at TIMESTAMP DEFAULT NOW(),  -- Last updated timestamp
    FOREIGN KEY (album_id) REFERENCES albums (id) ON DELETE CASCADE
);

-- ============================
-- ====== Trigger Setup ======
-- ============================

-- Function to increment total_tracks when a new track is added
CREATE OR REPLACE FUNCTION increment_total_tracks()
RETURNS TRIGGER AS $$
DECLARE
    album_id INT;
BEGIN
    -- Retrieve the album_id from the new track
    album_id := NEW.album_id;

    -- Update the total_tracks count for the album
    UPDATE albums SET total_tracks = total_tracks + 1 WHERE id = album_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to decrement total_tracks when a track is deleted
CREATE OR REPLACE FUNCTION decrement_total_tracks()
RETURNS TRIGGER AS $$
DECLARE
    album_id INT;
BEGIN
    -- Retrieve the album_id from the deleted track
    album_id := OLD.album_id;

    -- Update the total_tracks count for the album, ensuring it doesn't go below zero
    UPDATE albums 
    SET total_tracks = GREATEST(total_tracks - 1, 0) 
    WHERE id = album_id;

    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

-- Trigger to call increment_total_tracks after inserting a new track
CREATE TRIGGER trg_increment_total_tracks
AFTER INSERT ON tracks
FOR EACH ROW
EXECUTE FUNCTION increment_total_tracks();

-- Trigger to call decrement_total_tracks after deleting a track
CREATE TRIGGER trg_decrement_total_tracks
AFTER DELETE ON tracks
FOR EACH ROW
EXECUTE FUNCTION decrement_total_tracks();
