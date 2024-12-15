import React, { useState, useEffect } from "react";
import axios from "../axiosConfig"; // Import the configured axios instance
import { Table, Spinner, Alert, Container, Row, Col } from "react-bootstrap";

const Library = () => {
  const [artists, setArtists] = useState([]);
  const [albums, setAlbums] = useState([]);
  const [loadingArtists, setLoadingArtists] = useState(true);
  const [loadingAlbums, setLoadingAlbums] = useState(true);
  const [errorArtists, setErrorArtists] = useState(null);
  const [errorAlbums, setErrorAlbums] = useState(null);

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

  // Helper function to get albums by artist
  const getAlbumsByArtist = (artistId) => {
    return albums.filter((album) => album.artist_id === artistId);
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
                  <th>#</th>
                  <th>Name</th>
                  <th>Genre</th>
                </tr>
              </thead>
              <tbody>
                {artists.map((artist, index) => (
                  <tr key={artist.id}>
                    <td>{index + 1}</td>
                    <td>{artist.name}</td>
                    <td>{artist.genre}</td>
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
            <Table striped bordered hover responsive>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Title</th>
                  <th>Artist</th>
                  <th>Release Year</th>
                </tr>
              </thead>
              <tbody>
                {albums.map((album, index) => {
                  const artist = artists.find(
                    (artist) => artist.id === album.artist_id
                  );
                  return (
                    <tr key={album.id}>
                      <td>{index + 1}</td>
                      <td>{album.title}</td>
                      <td>{artist ? artist.name : "Unknown Artist"}</td>
                      <td>{album.release_year}</td>
                    </tr>
                  );
                })}
              </tbody>
            </Table>
          )}
        </Col>
      </Row>
    </Container>
  );
};

export default Library;