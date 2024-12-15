import React from "react";
import { Routes, Route, Link } from "react-router-dom";
import { Navbar, Nav, Container } from 'react-bootstrap';
import MetadataManager from "./components/MetadataManager";
import ImageUploader from "./components/ImageUploader"; 
import Library from "./components/Library";

const App = () => {
  return (
    <div>
      {/* Navbar */}
      <Navbar bg="dark" variant="dark" expand="lg">
        <Container fluid>
          <Navbar.Brand as={Link} to="/">
            album-wiz
          </Navbar.Brand>
          <Navbar.Toggle aria-controls="navbar-nav" />
          <Navbar.Collapse id="navbar-nav">
            <Nav className="me-auto">
              <Nav.Link as={Link} to="/metadata">
                Metadata Manager
              </Nav.Link>
              <Nav.Link as={Link} to="/library">
                Library
              </Nav.Link>
            </Nav>
          </Navbar.Collapse>
        </Container>
      </Navbar>

      {/* Main Content Area */}
      <Container className="mt-4">
        <Routes>
          <Route path="/" element={<ImageUploader />} />
          <Route path="/metadata" element={<MetadataManager />} />
          <Route path="/library" element={<Library />} />
        </Routes>
      </Container>
    </div>
  );
};

export default App;