import React from "react";
import { Routes, Route, Link } from "react-router-dom";
import MetadataManager from "./components/MetadataManager";

const App = () => {
  return (
    <div>
      {/* A simple Navbar */}
      <nav className="navbar navbar-expand-lg navbar-dark bg-dark">
        <div className="container-fluid">
          <Link className="navbar-brand" to="/">
            album-wiz
          </Link>
          <button
            className="navbar-toggler"
            type="button"
            data-bs-toggle="collapse"
            data-bs-target="#navbarSupportedContent"
            aria-controls="navbarSupportedContent"
            aria-expanded="false"
            aria-label="Toggle navigation"
          >
            <span className="navbar-toggler-icon"></span>
          </button>
          <div className="collapse navbar-collapse" id="navbarSupportedContent">
            <ul className="navbar-nav me-auto mb-2 mb-lg-0">
              <li className="nav-item">
                <Link className="nav-link" to="/metadata">
                  Metadata Manager
                </Link>
              </li>
            </ul>
          </div>
        </div>
      </nav>

      {/* Main content area */}
      <div className="container mt-4">
        <Routes>
          <Route path="/" element={<h2 className="text-center">Home</h2>} />
          <Route path="/metadata" element={<MetadataManager />} />
        </Routes>
      </div>
    </div>
  );
};

export default App;
