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
} from "react-bootstrap";

const Library = () => {
  const [artists, setArtists] = useState([]);
  const [albums, setAlbums] = useState([]);
  const [loadingArtists, setLoadingArtists] = useState(true);
  const [loadingAlbums, setLoadingAlbums] = useState(true);
  const [errorArtists, setErrorArtists] = useState(null);
  const [errorAlbums, setErrorAlbums] = useState(null);
  const [deletingAlbum, setDeletingAlbum] = useState(false);
  const [deleteError, setDeleteError] = useState(null);

  // Fetch Artists
  useEffect(() => {
    const fetchArtists = async () => {
      try {
        const response = await axios.get("/db/artists");
        setArtists(response.data);
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

  // Fetch Albums
  useEffect(() => {
    const fetchAlbums = async () => {
      try {
        const response = await axios.get("/db/albums");
        setAlbums(response.data);
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

  // Delete Album
  const deleteAlbum = async (albumId) => {
    if (deletingAlbum) return; // Prevent multiple simultaneous deletions
    setDeletingAlbum(true);
    setDeleteError(null);
    try {
      await axios.delete(`/album/${albumId}`);
      setAlbums((prevAlbums) =>
        prevAlbums.filter((album) => album.id !== albumId)
      );

      // Refetch artists to ensure the UI reflects any artist deletions
      const response = await axios.get("/db/artists");
      setArtists(response.data);
    } catch (error) {
      console.error("Error deleting album:", error);
      setDeleteError(error.response?.data?.detail || "Failed to delete album.");
    } finally {
      setDeletingAlbum(false);
    }
  };

  return (
    <Container className="mt-4">
      <h2 className="text-center mb-4">Your Library</h2>
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
              <Table striped bordered hover responsive>
                <thead>
                  <tr>
                    <th>Cover</th>
                    <th>Title</th>
                    <th>Artist</th>
                    <th>Actions</th>
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
                        <Image
                        src={`/media/${album.cover_image}` || "/media/placeholder.png"} // Placeholder if no cover URL
                        alt={`${album.cover_image}`}
                        thumbnail
                        style={{ maxWidth: "100px" }}
                        />
                      </td>
                      <td>{album.title}</td>
                      <td>{artist ? artist.name : "Unknown Artist"}</td>
                      <td>
                        <Button
                        variant="danger"
                        size="sm"
                        onClick={() => deleteAlbum(album.id)}
                        disabled={deletingAlbum}
                        >
                        {deletingAlbum ? "Deleting..." : "Delete"}
                        </Button>
                      </td>
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