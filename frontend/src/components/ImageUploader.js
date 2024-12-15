import React, { useState, useEffect } from "react";
import axios from "../axiosConfig"; // Import the configured axios instance

const ImageUploader = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(null);
  const [uploadError, setUploadError] = useState(null);

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
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      if (response.status === 200) {
        setUploadSuccess("Image uploaded successfully!");
        setSelectedFile(null);
        setPreviewUrl(null);
      } else {
        throw new Error(response.statusText || "Upload failed.");
      }
    } catch (error) {
      console.error("Upload error:", error);
      // Handle different error scenarios
      if (error.response) {
        // Server responded with a status other than 2xx
        setUploadError(`Upload failed: ${error.response.data.message || error.message}`);
      } else if (error.request) {
        // Request was made but no response received
        setUploadError("No response from the server. Please try again later.");
      } else {
        // Something else caused the error
        setUploadError(`Upload failed: ${error.message}`);
      }
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

  return (
    <div className="text-center">
      <h2>Upload an Image</h2>
      <div className="mb-3">
        <input
          type="file"
          accept="image/*"
          capture="environment" // 'environment' for rear camera on mobile devices
          onChange={handleFileChange}
          className="form-control"
        />
      </div>
      {previewUrl && (
        <div className="mb-3">
          <img
            src={previewUrl}
            alt="Selected preview"
            style={{ maxWidth: "100%", height: "auto", borderRadius: "8px" }}
          />
        </div>
      )}
      <button
        className="btn btn-primary"
        onClick={handleUpload}
        disabled={uploading || !selectedFile}
      >
        {uploading ? "Uploading..." : "Upload"}
      </button>

      {/* Feedback Messages */}
      {uploadSuccess && (
        <div className="alert alert-success mt-3" role="alert">
          {uploadSuccess}
        </div>
      )}
      {uploadError && (
        <div className="alert alert-danger mt-3" role="alert">
          {uploadError}
        </div>
      )}
    </div>
  );
};

export default ImageUploader;