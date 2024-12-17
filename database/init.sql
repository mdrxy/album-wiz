-- Switch to the vinyl_db database
\c vinyl_db;

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
