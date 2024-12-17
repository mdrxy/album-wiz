import React from "react";
import { Link } from "react-router-dom";
import { Container, Button } from "react-bootstrap";

const NotFound = () => {
  return (
    <Container className="text-center mt-5">
      <h1>404</h1>
      <p>Oops! The page you are looking for does not exist.</p>
      <Button as={Link} to="/" variant="primary">
        Go Back Home
      </Button>
    </Container>
  );
};

export default NotFound;
