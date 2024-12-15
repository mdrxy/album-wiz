import React from "react";
import { Link } from "react-router-dom";
import { Container, Button } from "react-bootstrap";

const ServerError = () => {
  return (
    <Container className="text-center mt-5">
      <h1>500</h1>
      <p>Something went wrong on our end. Please try again later.</p>
      <Button as={Link} to="/" variant="primary">
        Go Back Home
      </Button>
    </Container>
  );
};

export default ServerError;