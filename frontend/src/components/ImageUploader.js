import React, { useState, useEffect } from "react";
import axios from "../axiosConfig"; // Import the configured axios instance

const ImageUploader = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(null);
  const [uploadError, setUploadError] = useState(null);
  const [responseData, setResponseData] = useState(null); // New state for response data
  const [showTracks, setShowTracks] = useState(false); // State for toggling tracks

  // Helper function to format duration
  const formatDuration = (seconds) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    // return `${minutes}m ${remainingSeconds}s`;
    return `${minutes} minutes`;
  };

  // Format values for better display
  const monthNames = {
    "01": "January",
    "02": "February",
    "03": "March",
    "04": "April",
    "05": "May",
    "06": "June",
    "07": "July",
    "08": "August",
    "09": "September",
    10: "October",
    11: "November",
    12: "December",
  };

  const matchAttributes = {
    artist_name: "Artist",
    album_name: "Release",
    genres: "Genres",
    release_date: "Released",
    total_tracks: "# Tracks",
    duration: "Duration",
    tracks: "Tracks",
  };

  const doNotShow = ["artist_url", "album_url", "artist_image", "album_image", "total_duration"];

  const formatValue = (key, value) => {
    if (key === "genres" && Array.isArray(value)) {
      return value.join(", ");
    }
    if (key === "release_date" && typeof value === "string") {
      // Transform 'YYYY-MM' to 'Month YYYY'
      const [year, month] = value.split("-");
      return `${monthNames[month]} ${year}`;
    }
    if (key === "total_duration") {
      return formatDuration(value);
    }
    if (Array.isArray(value)) {
      return `[ ${value
        .map((v) => (typeof v === "object" ? JSON.stringify(v) : v))
        .join(", ")} ]`;
    }
    if (typeof value === "object" && value !== null) {
      return JSON.stringify(value);
    }
    return value;
  };

  // Handle file selection
  const handleFileChange = (e) => {
    const file = e.target.files[0];
    setSelectedFile(file);
    setUploadSuccess(null);
    setUploadError(null);

    if (file) {
      const objectUrl = URL.createObjectURL(file);
      setPreviewUrl(objectUrl);
    } else {
      setPreviewUrl(null);
    }
  };

  // Handle image upload using axios
  // Also handle if the upload is not successful to prompt the user to try again

  const handleUpload = async () => {
    if (!selectedFile) {
      alert("Please select an image to upload.");
      return;
    }

    const formData = new FormData();
    formData.append("image", selectedFile);

    setUploading(true);
    setUploadSuccess(null);
    setUploadError(null);

    try {
      const response = await axios.post("/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      if (response.status === 200 && response.data) {
        setUploadSuccess("Image matched successfully!");
        setResponseData(response.data);
        setSelectedFile(null);
        setPreviewUrl(null);
      } else {
        throw new Error("Upload failed.");
      }
    } catch (error) {
      console.error("Upload error:", error);
      setUploadError(true); // Set the uploadError state to trigger retry dialog
    } finally {
      setUploading(false);
    }
  };

  // Cleanup the object URL to avoid memory leaks
  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  // Common button styles
  const buttonStyle = {
    fontSize: "1.2rem",
    padding: "10px 20px",
    gap: "10px",
    textDecoration: "none",
  };

  return (
    <div className="text-center">
      {/* Hide the header after upload */}
      {!uploadSuccess && <h2>Upload Image</h2>}

      <div className="mb-3">
        {!uploadSuccess && !selectedFile && (
          <input
            type="file"
            accept="image/*"
            capture="environment"
            onChange={handleFileChange}
            className="form-control"
          />
        )}
      </div>

      {previewUrl && (
        <div className="mb-3">
          <img
            src={previewUrl}
            alt="Selected preview"
            style={{ maxWidth: "25%", height: "auto", borderRadius: "8px" }}
          />
        </div>
      )}

      {selectedFile && !uploadError && (
        <button
          className="btn btn-primary"
          onClick={handleUpload}
          disabled={uploading || !selectedFile}
          style={buttonStyle}
        >
          {uploading ? "Uploading..." : "Confirm"}
        </button>
      )}

      {/* Feedback Messages */}
      {uploadSuccess && (
        <div className="alert alert-success mt-3" role="alert">
          {uploadSuccess}
        </div>
      )}
      {uploadError && (
        <div className="alert alert-danger mt-3" role="alert">
          Fail to upload image. Please REFRESH to try again.
          {uploadError}
        </div>
      )}

      {uploadSuccess && responseData && (
        <div className="mt-3">
          {/* Title Below Spotify Button */}
          {responseData.name && (
            <h4
              style={{
                margin: "10px 0",
                color: "#333",
                fontFamily: "Arial, sans-serif",
                textAlign: "center",
                fontSize: "1.5rem",
              }}
            >
              {responseData.name}
            </h4>
          )}

          {/* Uploaded Image */}
          {responseData.album_image && (
            <div className="d-flex justify-content-center mt-2">
              <img
                src={responseData.album_image}
                alt="Album image"
                style={{ maxWidth: "12.5%", borderRadius: "8px" }}
              />
            </div>
          )}
        </div>
      )}

      {responseData && responseData.album_name && responseData.artist_name && (
        <div className="mt-3">
          <h4
            style={{
              margin: "10px 0",
              color: "#333",
              fontFamily: "Arial, sans-serif",
              textAlign: "center",
              fontSize: "1.5rem",
            }}
          >
            {responseData.artist_name} - {responseData.album_name}
          </h4>
        </div>
      )}


      {/* Print the Server Response */}
      {responseData && (
        <div
          className="mt-4"
          style={{
            backgroundColor: "#f9f9f9",
            border: "1px solid #ddd",
            borderRadius: "8px",
            padding: "15px",
            textAlign: "left",
            fontFamily: "monospace",
          }}
        >
          <div>
            {Object.entries(responseData)
              .filter(([key]) => !doNotShow.includes(key) && key !== "tracks")
              .map(([key, value]) => (
                <div key={key} style={{ marginBottom: "10px" }}>
                  <span
                    style={{
                      color: "red",
                      fontWeight: "bold",
                    }}
                  >
                    {/* Use the keyDisplayMap to display a friendly name, fallback to the original key if not found */}
                    {matchAttributes[key] || key}:
                  </span>{" "}
                  <span style={{ color: "#444" }}>
                    {formatValue(key, value)}
                  </span>
                </div>
              ))}
            {/* Total Duration */}
            {responseData.total_duration && (
              <div style={{ marginBottom: "10px" }}>
                <span style={{ color: "red", fontWeight: "bold" }}>{matchAttributes["duration"]}:</span>{" "}
                <span style={{ color: "#444" }}>
                  {formatDuration(responseData.total_duration)}
                </span>
              </div>
            )}
            {/* Show/Hide Tracks Button */}
            {responseData.tracks && (
              <button
                className="btn btn-secondary mt-2"
                onClick={() => setShowTracks((prev) => !prev)}
                style={{
                  fontSize: "1rem",
                  padding: "5px 10px",
                }}
              >
                {showTracks ? "Hide Tracks" : "Show Tracks"}
              </button>
            )}
            {showTracks && responseData.tracks && (
              <ul
                style={{
                  marginTop: "10px",
                  paddingLeft: "40px",
                  listStyleType: "decimal-leading-zero",
                }}
              >
                {responseData.tracks.map((track, index) => {
                  const minutes = Math.floor(track.duration / 60);
                  const seconds = track.duration % 60;

                  // Dynamically determine the duration color
                  const durationStyle = {
                    color:
                      minutes > 5 ? "red" : minutes < 3 ? "blue" : "inherit",
                  };

                  return (
                    <li key={index} style={{ marginBottom: "10px" }}>
                      <b>{track.name}</b> <br />
                      <span style={durationStyle}>
                        {minutes}m {seconds}s
                      </span>
                      <br />
                      {(track.explicit === true || track.explicit === null) && (
                        <span style={{ color: "red" }}>
                          Explicit
                          {track.explicit === true ? "" : ": Unknown"} <br />
                        </span>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      )}

      {/* Spotify Button */}
      {responseData && responseData.album_url && (
        <div className="mt-4 d-flex justify-content-center align-items-center">
          <a
            href={responseData.album_url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-outline-secondary d-flex align-items-center"
            style={buttonStyle}
          >
            <img
              src="https://upload.wikimedia.org/wikipedia/commons/1/19/Spotify_logo_without_text.svg"
              alt="Spotify"
              style={{ width: "24px", height: "24px", marginRight: "10px" }}
            />
            Open in Spotify
          </a>
        </div>
      )}
    </div>
  );
};

export default ImageUploader;
