import React, { useState, useRef, useEffect } from "react";
import axios from "../axiosConfig";
import {
  Form,
  Button,
  Table,
  Spinner,
  Alert,
  Container,
  Row,
  Col,
  Badge,
  ProgressBar,
} from "react-bootstrap";
import "bootstrap-icons/font/bootstrap-icons.css";

// A mapping from internal field keys to more user-friendly display names.
const fieldDisplayNames = {
  "artist.name": "Artist Name",
  "artist.namevariations": "Artist Name Variations",
  "album.name": "Album Name",
  "artist.genres": "Artist Genres",
  "artist.image": "Artist Image",
  "artist.profile": "Artist Profile/Description",
  "album.genres": "Album Genres",
  "album.image": "Album Image",
  "album.total_tracks": "Total Tracks",
  "album.tracks": "Tracks",
  "album.release_date": "Release Date",
  "artist.popularity": "Artist Popularity",
  "artist.url": "Artist URL",
  "album.url": "Album URL",
  artist: "Artist",
  album: "Album",
};

const MetadataManager = () => {
  // useState hooks manage local component state.
  // These store the form inputs and the results from the API.
  const [artist, setArtist] = useState("");
  const [album, setAlbum] = useState("");
  const [metadata, setMetadata] = useState(null);
  const [differences, setDifferences] = useState(null);
  const [selectedResolution, setSelectedResolution] = useState({});
  const [selectedSources, setSelectedSources] = useState([]);
  const [availableSources, setAvailableSources] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [singleSourceConfirmed, setSingleSourceConfirmed] = useState(false);
  const [fetchedSourcesCount, setFetchedSourcesCount] = useState(null);
  const [fetchedSourcesList, setFetchedSourcesList] = useState([]);
  const [customImagePreviews, setCustomImagePreviews] = useState({});

  // New state to track custom input values for each field
  const [customValues, setCustomValues] = useState({});

  // useRef provides a mutable reference that persists across renders.
  // Here, it's used to refer to the error element, so we can scroll to it
  // when an error occurs.
  const errorRef = useRef(null);

  // This function checks if a given URL looks like an image URL
  // TODO: improve this to handle more cases
  const isImageUrl = (url) => {
    if (typeof url !== "string") return false;
    return (
      url.toLowerCase().includes("image") ||
      /\.(jpeg|jpg|png|gif|webp)$/i.test(url)
    );
  };

  // useEffect hooks allow you to run side-effects when state or props change.
  // This one runs whenever 'error' changes. If there's an error, scroll to it.
  useEffect(() => {
    if (error && errorRef.current) {
      errorRef.current.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    }
  }, [error]);

  // This effect runs once on mount because it has an empty dependency array [].
  // It fetches a list of available sources when the component loads.
  useEffect(() => {
    const fetchSources = async () => {
      try {
        const response = await axios.get("/meta-sources");
        if (response.data && response.data.sources) {
          setAvailableSources(response.data.sources);
        } else {
          setAvailableSources([]);
        }
      } catch (err) {
        console.error("Failed to fetch sources:", err);
        setAvailableSources([]);
      }
    };
    fetchSources();
  }, []);

  // This function is called to fetch metadata from the backend for a given artist and album.
  // It also handles comparing multiple metadata sources if more than one is selected.
  const fetchMetadata = async () => {
    const query = `${artist} - ${album}`.trim();

    // Validate the input fields
    if (!artist.trim() || !album.trim()) {
      setError("Please enter both artist and album.");
      return;
    }

    if (selectedSources.length === 0) {
      setError("Please select at least one database.");
      setMetadata(null);
      setDifferences(null);
      return;
    }

    try {
      setLoading(true);
      setError("");

      // Prepare query parameters to send to the API.
      const params = {
        compare: true,
        source: selectedSources.join(","),
      };

      // Make the API request to fetch metadata.
      const response = await axios.get(`/metadata/${query}`, {
        params,
        timeout: 10000, // timeout after 10 seconds
      });

      console.log("API Response:", response.data);

      const {
        differences,
        identical,
        sources,
        metadata: fetchedMetadata,
      } = response.data;

      // Store info about how many sources we fetched and which ones.
      setFetchedSourcesCount(selectedSources.length);
      setFetchedSourcesList([...selectedSources]);

      // If there's only one source selected, we can directly show that source's metadata.
      if (selectedSources.length === 1) {
        const selectedSource = selectedSources[0];

        if (!fetchedMetadata || !fetchedMetadata[selectedSource]) {
          setLoading(false);
          setError("No metadata found for the selected source.");
          // Clear previous output
          setMetadata(null);
          setDifferences(null);
          return;
        }

        const singleSourceMeta = fetchedMetadata[selectedSource];

        // Check if the album is present and not empty
        if (!singleSourceMeta.album || !singleSourceMeta.album.name) {
          setLoading(false);
          setError(
            "No album found. Please verify the search terms or try a different source."
          );
          // Clear previous output
          setMetadata(null);
          setDifferences(null);
          return;
        }

        // If album is found, proceed
        setMetadata({ identical: singleSourceMeta });
        setDifferences({});
        setLoading(false);
        return;
      }

      // If multiple sources are selected, first check if there's any metadata found at all.
      if (
        (!differences || Object.keys(differences).length === 0) &&
        (!identical || Object.keys(identical).length === 0)
      ) {
        setLoading(false);
        setError("No metadata found for the selected sources.");
        return;
      }

      // If there are fields where only one non-null value is found among all sources,
      // we can auto-resolve those fields (no need for user input) but still show them.
      const autoResolved = {};
      if (differences) {
        Object.keys(differences).forEach((field) => {
          const nonNullValues = Object.entries(differences[field]).filter(
            ([, value]) => value !== null
          );

          // If exactly one non-null value exists, select it automatically.
          if (nonNullValues.length === 1) {
            autoResolved[field] = nonNullValues[0][1];
          }
        });
      }

      // Update the selectedResolution state with any auto-resolved fields.
      setSelectedResolution((prev) => ({ ...prev, ...autoResolved }));

      // Store the identical and sources data in state so we can display them.
      setMetadata({ identical: identical || {}, sources });
      setDifferences(differences || {});
      setLoading(false);
    } catch (err) {
      setLoading(false);
      // If the server provides a detailed error, display it; otherwise show a generic message.
      setError(err.response?.data?.detail || "Failed to fetch metadata.");
    }
  };

  // This allows the user to press Enter in the input fields to trigger a search.
  const handleKeyDown = (event) => {
    if (event.key === "Enter") {
      fetchMetadata();
    }
  };

  // When a user selects a resolution (a choice for a field's value), we store it.
  const handleResolve = (field, rawValue) => {
    // "__NONEUSER__" means the user selected "None".
    // "__CUSTOM__" means the user selected the custom option but hasn't finalized input yet.
    setSelectedResolution((prev) => ({ ...prev, [field]: rawValue }));
    // If switching away from custom, clear preview state for that field.
    if (rawValue !== "__CUSTOM__") {
      setCustomImagePreviews((prev) => ({ ...prev, [field]: false }));
    }
  };

  // Upload the final resolved metadata. This function interprets the user choices.
  const uploadResolution = async () => {
    const finalResolution = {};
    for (const [field, val] of Object.entries(selectedResolution)) {
      if (val === "__NONEUSER__") {
        finalResolution[field] = null;
      } else if (val === "__NONEFOUND__") {
        // "__NONEFOUND__" is a non-selectable placeholder, but just in case,
        // we treat it as null.
        finalResolution[field] = null;
      } else if (val === "__CUSTOM__") {
        // If user selected custom, use the customValues[field] directly.
        finalResolution[field] = customValues[field] || null;
      } else {
        // Try to parse JSON if it's a stringified object or a string.
        try {
          finalResolution[field] = JSON.parse(val);
        } catch {
          // If not valid JSON, just use the raw value or null if empty.
          finalResolution[field] = val ? val : null;
        }
      }
    }

    // TODO: upload finalResolution to backend
    console.log("Final Resolution to Upload:", finalResolution);
  };

  // If there's only one source, after reviewing, the user can confirm.
  const handleConfirmSingleSource = () => {
    setSingleSourceConfirmed(true);
    uploadResolution();
  };

  // Helper function to nicely format source names for display.
  const formatSourceName = (s) => {
    const lower = s.toLowerCase();
    if (lower === "musicbrainz") {
      // Special case for MusicBrainz
      return "MusicBrainz";
    }
    // Capitalize the first letter and leave the rest as is.
    return s.charAt(0).toUpperCase() + s.slice(1);
  };

  // Format multiple sources in a user-friendly way
  // e.g., "MusicBrainz and Discogs" or "MusicBrainz, Discogs, and Spotify"
  const formatSources = (sources) => {
    const capitalized = sources.map(formatSourceName);
    if (capitalized.length === 1) return capitalized[0];
    if (capitalized.length === 2)
      return `${capitalized[0]} and ${capitalized[1]}`;
    return (
      capitalized.slice(0, -1).join(", ") +
      ", and " +
      capitalized[capitalized.length - 1]
    );
  };

  // If we have multiple sources and identical fields exist, change the heading text to reflect the comparison.
  let headingText = "Metadata";
  if (
    fetchedSourcesCount &&
    fetchedSourcesCount > 1 &&
    metadata &&
    Object.keys(metadata.identical).length > 0
  ) {
    headingText = `Shared fields between ${formatSources(fetchedSourcesList)}`;
  }

  // Display a single metadata field in a user-friendly way.
  const displayField = (label, value) => {
    // Handle images
    if (label.toLowerCase().includes("image") && typeof value === "string") {
      const imageUrl = value;
      return (
        <div className="mb-3" key={label}>
          <h3>{label}</h3>
          {imageUrl ? (
            <img
              src={imageUrl}
              alt={label}
              className="img-fluid mb-2"
              style={{ maxWidth: "200px", borderRadius: "8px" }}
            />
          ) : (
            <em>No image available</em>
          )}
        </div>
      );
    }

    // Handle URLs
    if (label.toLowerCase().includes("url") && typeof value === "string") {
      return (
        <div className="mb-3" key={label}>
          <h3>{label}</h3>
          {value ? (
            <a href={value} target="_blank" rel="noopener noreferrer">
              <i className="bi bi-link-45deg"></i> {value}
            </a>
          ) : (
            <em>None</em>
          )}
        </div>
      );
    }

    // Handle popularity as a simple progress bar (0-100)
    if (
      label.toLowerCase().includes("popularity") &&
      typeof value === "number"
    ) {
      return (
        <div className="mb-3" key={label}>
          <h3>{label}</h3>
          <ProgressBar now={value} label={`${value}%`} />
        </div>
      );
    }

    // Handle profile/description (HTML)
    if (label.includes("Profile/Description") && typeof value === "string") {
      return (
        <div className="mb-3" key={label}>
          <h3>{label}</h3>
          <div
            className="p-3 mb-3 border bg-light"
            dangerouslySetInnerHTML={{ __html: value }}
          ></div>
        </div>
      );
    }

    // Handle null/undefined
    if (value === null || value === undefined) {
      return (
        <div className="mb-3" key={label}>
          <h3>{label}</h3>
          <p>
            <i>None found</i>
          </p>
        </div>
      );
    }

    // If value is a primitive (string/number) and not handled above, just display it.
    if (typeof value === "string" || typeof value === "number") {
      return (
        <div className="mb-3" key={label}>
          <h3>{label}</h3>
          <p>{value.toString()}</p>
        </div>
      );
    }

    // If it's an object and not null (handled in renderMetadata), we shouldn't reach here
    // because objects are handled recursively. Just in case:
    return (
      <div className="mb-3" key={label}>
        <h3>{label}</h3>
        <pre>{JSON.stringify(value, null, 2)}</pre>
      </div>
    );
  };

  // A helper function to format track duration (in seconds) to mm:ss
  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  // Recursively render metadata. If the data is nested objects,
  // we go deeper to display all fields.
  const renderMetadata = (data, prefix = "") => {
    if (!data || typeof data !== "object") return null;

    return Object.entries(data).map(([key, val]) => {
      const fullKey = prefix ? `${prefix}.${key}` : key;
      const label = fieldDisplayNames[fullKey] || fullKey;

      // Special handling for arrays:
      if (Array.isArray(val)) {
        // If it's the "Tracks" field, display in a table
        if (label.toLowerCase().includes("tracks")) {
          return (
            <div className="mb-3" key={fullKey}>
              <h3>{label}</h3>
              {val.length === 0 ? (
                <p>None</p>
              ) : (
                <Table striped bordered hover responsive>
                  <thead>
                    <tr>
                      <th>Track Name</th>
                      <th>Duration</th>
                      <th>Explicit</th>
                    </tr>
                  </thead>
                  <tbody>
                    {val.map((track, i) => (
                      <tr key={i}>
                        <td>{track.name || "Unknown"}</td>
                        <td>
                          {track.duration
                            ? formatDuration(track.duration)
                            : "N/A"}
                        </td>
                        <td>
                          {track.explicit === true
                            ? "Yes"
                            : track.explicit === false
                            ? "No"
                            : "Unknown"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              )}
            </div>
          );
        }

        // If it's a genres field, display as badges
        if (label.toLowerCase().includes("genres")) {
          return (
            <div className="mb-3" key={fullKey}>
              <h3>{label}</h3>
              {val.length === 0 ? (
                <p>None</p>
              ) : (
                <div>
                  {val.map((genres, i) => (
                    <Badge bg="secondary" className="me-2" key={i}>
                      {genres}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          );
        }

        // Default array handling: just list items
        return (
          <div className="mb-3" key={fullKey}>
            <h3>{label}</h3>
            {val.length === 0 ? (
              <p>None</p>
            ) : val.length === 1 ? (
              <p>{val[0] === null ? "None" : val[0].toString()}</p>
            ) : (
              <ul>
                {val.map((item, i) => (
                  <li key={i}>{item === null ? "None" : item.toString()}</li>
                ))}
              </ul>
            )}
          </div>
        );
      }

      // If it's an object (and not null), recurse deeper unless it's handled specially above.
      if (typeof val === "object" && val !== null && val.image === undefined) {
        return (
          <div key={fullKey} className="mb-3">
            <h3>{label}</h3>
            {renderMetadata(val, fullKey)}
          </div>
        );
      }

      // Otherwise, use displayField for the final display
      return <div key={fullKey}>{displayField(label, val)}</div>;
    });
  };

  return (
    <Container style={{ paddingBottom: "50px" }}>
      <h2 className="mb-4 text-center">Add Record</h2>
      <Form
        onSubmit={(e) => {
          e.preventDefault();
          fetchMetadata();
        }}
      >
        {/* Artist Input Field */}
        <Form.Group className="mb-3" controlId="formArtist">
          <Form.Label className="fw-bold">
            <i className="bi bi-person"></i> Artist
          </Form.Label>
          <Form.Control
            type="text"
            className="form-control mb-2"
            value={artist}
            onChange={(e) => setArtist(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Enter artist name"
            autoFocus // Enable autofocus for the first input
          />
        </Form.Group>

        {/* Album Input Field */}
        <Form.Group className="mb-3" controlId="formAlbum">
          <Form.Label className="fw-bold">
            <i className="bi bi-vinyl"></i> Album
          </Form.Label>
          <Form.Control
            type="text"
            value={album}
            onChange={(e) => setAlbum(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Enter album name"
          />
        </Form.Group>

        {/* Metadata Sources Selection */}
        <Form.Group className="mb-3" controlId="formSources">
          <Form.Label>
            <i className="bi bi-database"></i> Search Databases:
          </Form.Label>
          {availableSources.length > 0 ? (
            <div>
              {availableSources.map((source) => (
                <Form.Check
                  type="checkbox"
                  id={source}
                  label={formatSourceName(source)}
                  key={source}
                  value={source}
                  checked={selectedSources.includes(source)}
                  onChange={(e) => {
                    const value = e.target.value;
                    setSelectedSources((prevSelected) =>
                      prevSelected.includes(value)
                        ? prevSelected.filter((s) => s !== value)
                        : [...prevSelected, value]
                    );
                  }}
                  className="mb-2"
                />
              ))}
            </div>
          ) : (
            <Alert variant="info">
              No sources available. Please try again later.
            </Alert>
          )}
        </Form.Group>

        {/* Fetch Metadata Button */}
        <Button
          variant="primary"
          type="submit"
          disabled={loading || availableSources.length === 0}
          className="mb-3"
        >
          <i className="bi bi-search"></i> Fetch Metadata
        </Button>
      </Form>

      {/* Show a loading message while fetching */}
      {loading && (
        <div className="text-center my-3">
          <Spinner animation="border" variant="primary" />
          <span className="ms-2">Loading...</span>
        </div>
      )}

      {/* Show any error messages */}
      {error && (
        <Alert ref={errorRef} variant="danger">
          <i className="bi bi-exclamation-circle me-2"></i> {error}
        </Alert>
      )}

      {/* Display Metadata */}
      {metadata && (
        <div className="mt-4">
          {/* Identical Metadata Alert - Only show if there are identical fields */}
          {Object.keys(metadata.identical).length > 0 && (
            <Alert variant="success">
              <h2>{headingText}</h2>
              {renderMetadata(metadata.identical)}
            </Alert>
          )}

          {/* If only one source was fetched, user can confirm directly */}
          {fetchedSourcesCount === 1 && (
            <div className="mt-4">
              <Alert variant="info">
                Please review the metadata above. If it looks correct, click the
                button below to confirm and submit.
              </Alert>
              <Button
                variant="success"
                onClick={handleConfirmSingleSource}
                disabled={loading}
              >
                <i className="bi bi-check-circle me-2"></i> Confirm and Submit
              </Button>
            </div>
          )}

          {/* If multiple sources are fetched, show differences for the user to resolve */}
          {fetchedSourcesCount > 1 &&
            differences &&
            Object.keys(differences).length > 0 && (
              <div className="mt-4">
                <h2 className="mb-3">
                  <i className="bi bi-exclamation-triangle me-2 text-warning"></i>{" "}
                  Resolve Differences
                </h2>
                {Object.keys(differences).map((field) => {
                  const label = fieldDisplayNames[field] || field;
                  const allNull = Object.values(differences[field]).every(
                    (val) => val === null
                  );

                  if (allNull) {
                    // If all are null, we have "None" and "Custom" as options.
                    return (
                      <div key={field} className="mb-4">
                        <h4>{label}</h4>
                        <Form.Check
                          type="radio"
                          id={`${field}-none`}
                          name={field}
                          label="None"
                          value="__NONEUSER__"
                          onChange={() => handleResolve(field, "__NONEUSER__")}
                          checked={selectedResolution[field] === "__NONEUSER__"}
                          className="mb-2"
                        />
                        <Form.Check
                          type="radio"
                          id={`${field}-custom`}
                          name={field}
                          label="Custom"
                          value="__CUSTOM__"
                          onChange={() => handleResolve(field, "__CUSTOM__")}
                          checked={selectedResolution[field] === "__CUSTOM__"}
                        />
                        {selectedResolution[field] === "__CUSTOM__" && (
                          <div className="mt-2">
                            <Form.Control
                              type="text"
                              placeholder={`Enter custom ${label.toLowerCase()}`}
                              value={customValues[field] || ""}
                              onChange={(e) =>
                                setCustomValues((prev) => ({
                                  ...prev,
                                  [field]: e.target.value,
                                }))
                              }
                            />
                            {isImageUrl(customValues[field]) && (
                              <div className="mt-2">
                                <Button
                                  variant="outline-primary"
                                  size="sm"
                                  onClick={() =>
                                    setCustomImagePreviews((prev) => ({
                                      ...prev,
                                      [field]: !prev[field],
                                    }))
                                  }
                                  className="me-2"
                                >
                                  {customImagePreviews[field]
                                    ? "Hide Preview"
                                    : "Preview Image"}
                                </Button>
                                {customImagePreviews[field] && (
                                  <img
                                    src={customValues[field]}
                                    alt="Custom Preview"
                                    style={{
                                      maxWidth: "200px",
                                      borderRadius: "8px",
                                    }}
                                    className="img-fluid mt-2"
                                  />
                                )}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  }

                  // If there are some actual values, list each source's value as a choice.
                  return (
                    <div key={field} className="mb-4">
                      <h4>{label}</h4>
                      {Object.entries(differences[field]).map(
                        ([source, value]) => {
                          const displaySource = formatSourceName(source);

                          if (value === null) {
                            // Handle null case as before
                            return (
                              <div className="form-check mb-2" key={source}>
                                <Form.Check
                                  type="radio"
                                  id={`${field}-${source}`}
                                  name={field}
                                  label={`${displaySource}: `}
                                  value="__NONEFOUND__"
                                  disabled={true}
                                  className="me-2"
                                />
                                <em>None found</em>
                              </div>
                            );
                          }

                          // Decide how to display the value
                          let displayValue;
                          if (Array.isArray(value)) {
                            // If it's an array, join by commas or line breaks for a nicer view
                            displayValue =
                              value.length > 0 ? value.join(", ") : "None";
                          } else if (typeof value === "object") {
                            // If it's an object, optionally format as JSON or handle specially
                            displayValue = JSON.stringify(value, null, 2);
                          } else {
                            // For strings/numbers, just display as is
                            displayValue = value;
                          }

                          const radioValue = JSON.stringify(value);

                          return (
                            <div className="form-check mb-2" key={source}>
                              <Form.Check
                                type="radio"
                                id={`${field}-${source}`}
                                name={field}
                                label={
                                  <>
                                    {displaySource}:
                                    {label.toLowerCase().includes("profile") &&
                                    typeof value === "string" ? (
                                      <div
                                        className="border bg-light p-2 d-inline-block ms-2"
                                        dangerouslySetInnerHTML={{
                                          __html: value,
                                        }}
                                      />
                                    ) : label.toLowerCase().includes("image") &&
                                      typeof value === "string" ? (
                                      <img
                                        src={value}
                                        alt={label}
                                        className="img-fluid d-block mt-2"
                                        style={{
                                          maxWidth: "200px",
                                        }}
                                      />
                                    ) : (
                                      <pre className="d-inline-block ms-2 mb-0">
                                        {displayValue}
                                      </pre>
                                    )}
                                  </>
                                }
                                value={radioValue}
                                onChange={() =>
                                  handleResolve(field, radioValue)
                                }
                                checked={
                                  selectedResolution[field] === radioValue
                                }
                              />
                              {/* Edit button */}
                              <Button
                                variant="link"
                                size="sm"
                                onClick={() => {
                                  handleResolve(field, "__CUSTOM__");
                                  setCustomValues((prev) => ({
                                    ...prev,
                                    [field]:
                                      typeof value === "object"
                                        ? JSON.stringify(value)
                                        : value,
                                  }));
                                }}
                                className="ms-2 p-0"
                              >
                                <i className="bi bi-pencil"></i> Edit
                              </Button>
                            </div>
                          );
                        }
                      )}

                      {/* None Option */}
                      <Form.Check
                        type="radio"
                        id={`${field}-none`}
                        name={field}
                        label="None"
                        value="__NONEUSER__"
                        onChange={() => handleResolve(field, "__NONEUSER__")}
                        checked={selectedResolution[field] === "__NONEUSER__"}
                        className="mb-2"
                      />

                      {/* Custom Option */}
                      <Form.Check
                        type="radio"
                        id={`${field}-custom`}
                        name={field}
                        label="Custom"
                        value="__CUSTOM__"
                        onChange={() => handleResolve(field, "__CUSTOM__")}
                        checked={selectedResolution[field] === "__CUSTOM__"}
                        className="mb-2"
                      />

                      {/* Custom Input Field */}
                      {selectedResolution[field] === "__CUSTOM__" && (
                        <div className="mt-2">
                          <Form.Control
                            type="text"
                            placeholder={`Enter custom ${label.toLowerCase()}`}
                            value={customValues[field] || ""}
                            onChange={(e) =>
                              setCustomValues((prev) => ({
                                ...prev,
                                [field]: e.target.value,
                              }))
                            }
                          />
                          {isImageUrl(customValues[field]) && (
                            <div className="mt-2">
                              <Button
                                variant="outline-primary"
                                size="sm"
                                onClick={() =>
                                  setCustomImagePreviews((prev) => ({
                                    ...prev,
                                    [field]: !prev[field],
                                  }))
                                }
                                className="me-2"
                              >
                                {customImagePreviews[field]
                                  ? "Hide Preview"
                                  : "Preview Image"}
                              </Button>
                              {customImagePreviews[field] && (
                                <img
                                  src={customValues[field]}
                                  alt="Custom Preview"
                                  style={{
                                    maxWidth: "200px",
                                    borderRadius: "8px",
                                  }}
                                  className="img-fluid mt-2"
                                />
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}

                {/* Upload Resolution Button */}
                <Button
                  variant="primary"
                  onClick={uploadResolution}
                  disabled={loading}
                >
                  Upload Resolution
                </Button>
              </div>
            )}

          {/* No Differences Found */}
          {metadata && fetchedSourcesCount > 1 && !differences && (
            <Alert variant="info" className="mt-4">
              No differences found between metadata sources.
            </Alert>
          )}
        </div>
      )}
    </Container>
  );
};

export default MetadataManager;
