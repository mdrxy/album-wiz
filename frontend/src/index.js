import React from "react";
import ReactDOM from "react-dom/client";
// import './index.css'; // Importing global styles
import App from "./App"; // Importing the main App component

// Create a root element for React to render into
const root = ReactDOM.createRoot(document.getElementById("root"));

// Render the main App component
root.render(
  <React.StrictMode>
    {/* StrictMode helps identify potential problems in the application by enabling additional checks during development */}
    <App />
  </React.StrictMode>
);
