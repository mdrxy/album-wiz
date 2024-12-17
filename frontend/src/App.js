import React, { useState } from "react";
import { Routes, Route, Link } from "react-router-dom";
import { Navbar, Nav, Container } from "react-bootstrap";
import MetadataManager from "./components/MetadataManager";
import ImageUploader from "./components/ImageUploader";
import Library from "./components/Library";
import NotFound from "./components/NotFound";
import ServerError from "./components/ServerError";

const App = () => {
  const [uploaderKey, setUploaderKey] = useState(0);
  const [expanded, setExpanded] = useState(false); // Track navbar expansion state

  const handleAlbumWizClick = () => {
    setUploaderKey((prevKey) => prevKey + 1);
    setExpanded(false);
  };

  const handleNavClick = () => {
    setExpanded(false); // Close navbar on link click
  };

  return (
    <div>
      {/* Navbar */}
      <Navbar
        bg="dark"
        variant="dark"
        expand="lg"
        expanded={expanded} // Control navbar expansion state
        onToggle={(isExpanded) => setExpanded(isExpanded)} // Sync toggle with state
      >
        <Container fluid>
          <Navbar.Brand as={Link} to="/" onClick={handleAlbumWizClick}>
            <strong>album-wiz</strong>
          </Navbar.Brand>
          <Navbar.Toggle aria-controls="navbar-nav" />
          <Navbar.Collapse id="navbar-nav">
            <Nav className="me-auto" onSelect={handleNavClick}>
              <Nav.Link as={Link} to="/" onClick={handleAlbumWizClick}>
                Match Record
              </Nav.Link>
              <Nav.Link as={Link} to="/add" onClick={handleNavClick}>
                Add Records
              </Nav.Link>
              <Nav.Link as={Link} to="/library" onClick={handleNavClick}>
                Library
              </Nav.Link>
            </Nav>
          </Navbar.Collapse>
        </Container>
      </Navbar>

      {/* Main Content Area */}
      <Container className="mt-4">
        <Routes>
          <Route path="/" element={<ImageUploader key={uploaderKey} />} />
          <Route path="/add" element={<MetadataManager />} />
          <Route path="/library" element={<Library />} />
          <Route path="/500" element={<ServerError />} />
          <Route path="*" element={<NotFound />} /> {/* Catch-all route */}
        </Routes>
      </Container>
    </div>
  );
};

export default App;
