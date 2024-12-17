import React, { useState, useEffect } from "react";
import axios from "../axiosConfig"; // Import the configured axios instance
import {
  Table,
  Spinner,
  Alert,
  Container,
  Row,
  Col,
  Button,
  Image,
  Dropdown,
  ButtonGroup,
} from "react-bootstrap";

// Define cache keys and expiration (e.g., 24 hours)
const CACHE_KEYS = {
  ARTISTS: "cache_artists",
  ALBUMS: "cache_albums",
};
const CACHE_EXPIRATION = 24 * 60 * 60 * 1000; // 24 hours in milliseconds

// Utility functions for caching
const saveToCache = (key, data) => {
  const cacheEntry = {
    timestamp: Date.now(),
    data,
  };
  localStorage.setItem(key, JSON.stringify(cacheEntry));
};

const loadFromCache = (key) => {
  const cacheEntry = localStorage.getItem(key);
  if (!cacheEntry) return null;

  try {
    const parsedEntry = JSON.parse(cacheEntry);
    const isExpired = Date.now() - parsedEntry.timestamp > CACHE_EXPIRATION;
    if (isExpired) {
      localStorage.removeItem(key);
      return null;
    }
    return parsedEntry.data;
  } catch (error) {
    console.error("Error parsing cache data:", error);
    localStorage.removeItem(key);
    return null;
  }
};

const Library = () => {
  const [artists, setArtists] = useState([]);
  const [albums, setAlbums] = useState([]);
  const [loadingArtists, setLoadingArtists] = useState(true);
  const [loadingAlbums, setLoadingAlbums] = useState(true);
  const [errorArtists, setErrorArtists] = useState(null);
  const [errorAlbums, setErrorAlbums] = useState(null);
  const [deletingAlbums, setDeletingAlbums] = useState(false);
  const [deleteError, setDeleteError] = useState(null);
  const [selectedAlbums, setSelectedAlbums] = useState([]);

  // Fetch Artists with Caching
  useEffect(() => {
    const fetchArtists = async () => {
      setLoadingArtists(true);
      setErrorArtists(null);

      // Attempt to load from cache
      const cachedArtists = loadFromCache(CACHE_KEYS.ARTISTS);
      if (cachedArtists) {
        setArtists(cachedArtists);
        setLoadingArtists(false);
        return;
      }

      // Fetch from API if cache is not available or expired
      try {
        const response = await axios.get("/db/artists");
        setArtists(response.data);
        saveToCache(CACHE_KEYS.ARTISTS, response.data);
      } catch (error) {
        console.error("Error fetching artists:", error);
        setErrorArtists(
          error.response?.data?.detail || "Failed to fetch artists."
        );
      } finally {
        setLoadingArtists(false);
      }
    };

    fetchArtists();
  }, []);

  // Fetch Albums with Caching
  useEffect(() => {
    const fetchAlbums = async () => {
      setLoadingAlbums(true);
      setErrorAlbums(null);

      // Attempt to load from cache
      const cachedAlbums = loadFromCache(CACHE_KEYS.ALBUMS);
      if (cachedAlbums) {
        setAlbums(cachedAlbums);
        setLoadingAlbums(false);
        return;
      }

      // Fetch from API if cache is not available or expired
      try {
        const response = await axios.get("/db/albums");
        setAlbums(response.data);
        saveToCache(CACHE_KEYS.ALBUMS, response.data);
      } catch (error) {
        console.error("Error fetching albums:", error);
        setErrorAlbums(
          error.response?.data?.detail || "Failed to fetch albums."
        );
      } finally {
        setLoadingAlbums(false);
      }
    };

    fetchAlbums();
  }, []);

  // Delete Selected Albums
  const deleteSelectedAlbums = async () => {
    if (deletingAlbums || selectedAlbums.length === 0) return;
    setDeletingAlbums(true);
    setDeleteError(null);
    try {
      await Promise.all(
        selectedAlbums.map((albumId) => axios.delete(`/album/${albumId}`))
      );
      const updatedAlbums = albums.filter(
        (album) => !selectedAlbums.includes(album.id)
      );
      setAlbums(updatedAlbums);
      saveToCache(CACHE_KEYS.ALBUMS, updatedAlbums); // Update cache

      setSelectedAlbums([]);

      // Refetch artists to ensure the UI reflects any artist deletions
      const response = await axios.get("/db/artists");
      setArtists(response.data);
      saveToCache(CACHE_KEYS.ARTISTS, response.data); // Update cache
    } catch (error) {
      console.error("Error deleting albums:", error);
      setDeleteError(
        error.response?.data?.detail || "Failed to delete selected albums."
      );
    } finally {
      setDeletingAlbums(false);
    }
  };

  // Handle Individual Album Selection
  const handleSelectAlbum = (albumId) => {
    setSelectedAlbums((prevSelected) =>
      prevSelected.includes(albumId)
        ? prevSelected.filter((id) => id !== albumId)
        : [...prevSelected, albumId]
    );
  };

  // Handle Select All
  const handleSelectAll = () => {
    if (selectedAlbums.length === albums.length) {
      setSelectedAlbums([]);
    } else {
      setSelectedAlbums(albums.map((album) => album.id));
    }
  };

  return (
    <Container className="mt-4" style={{ paddingBottom: "50px" }}>
      <h2 className="text-center mb-4">Library</h2>
      <Row>
        <Col md={6}>
          <h4>Artists</h4>
          {loadingArtists ? (
            <Spinner animation="border" variant="primary" />
          ) : errorArtists ? (
            <Alert variant="danger">{errorArtists}</Alert>
          ) : artists.length === 0 ? (
            <Alert variant="info">No artists found.</Alert>
          ) : (
            <Table striped bordered hover responsive>
              <thead>
                <tr>
                  <th>Name</th>
                </tr>
              </thead>
              <tbody>
                {artists.map((artist) => (
                  <tr key={artist.id}>
                    <td>{artist.name}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Col>
        <Col md={6}>
          <h4>Albums</h4>
          {loadingAlbums ? (
            <Spinner animation="border" variant="primary" />
          ) : errorAlbums ? (
            <Alert variant="danger">{errorAlbums}</Alert>
          ) : albums.length === 0 ? (
            <Alert variant="info">No albums found.</Alert>
          ) : (
            <>
              {deleteError && <Alert variant="danger">{deleteError}</Alert>}
              <div className="d-flex justify-content-between mb-2">
                <div>
                  <Dropdown as={ButtonGroup}>
                    <Button
                      variant="danger"
                      onClick={deleteSelectedAlbums}
                      disabled={selectedAlbums.length === 0 || deletingAlbums}
                    >
                      {deletingAlbums ? "Deleting..." : "Delete Selected"}
                    </Button>
                    {/* Future actions can be added here */}
                  </Dropdown>
                </div>
                <div>
                  <Button
                    variant="outline-secondary"
                    size="sm"
                    onClick={handleSelectAll}
                  >
                    {selectedAlbums.length === albums.length
                      ? "Deselect All"
                      : "Select All"}
                  </Button>
                </div>
              </div>
              <Table striped bordered hover responsive>
                <thead>
                  <tr>
                    <th>
                      <input
                        type="checkbox"
                        checked={selectedAlbums.length === albums.length}
                        onChange={handleSelectAll}
                      />
                    </th>
                    <th>Cover</th>
                    <th>Title</th>
                    <th>Artist</th>
                  </tr>
                </thead>
                <tbody>
                  {albums.map((album) => {
                    const artist = artists.find(
                      (artist) => artist.id === album.artist_id
                    );
                    return (
                      <tr key={album.id}>
                        <td>
                          <input
                            type="checkbox"
                            checked={selectedAlbums.includes(album.id)}
                            onChange={() => handleSelectAlbum(album.id)}
                          />
                        </td>
                        <td>
                          <Image
                            src={
                              album.cover_image
                                ? `/media/${album.cover_image}`
                                : "/media/placeholder.png"
                            } // Placeholder if no cover URL
                            alt={`${album.cover_image}`}
                            thumbnail
                            style={{ maxWidth: "100px" }}
                          />
                        </td>
                        <td>{album.title}</td>
                        <td>{artist ? artist.name : "Unknown Artist"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </Table>
            </>
          )}
        </Col>
      </Row>
    </Container>
  );
};

export default Library;