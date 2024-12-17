"""
Module to extract a square vinyl record from an image.
"""

import os
from io import BytesIO
import logging
from typing import Optional, Tuple, List
import urllib.request
import numpy as np
import cv2
from PIL import Image
from rembg import remove

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
numba_logger = logging.getLogger("r")
numba_logger.setLevel(logging.WARNING)

# Define the debugging images directory with absolute path
DEBUGGING_DIR = os.path.abspath("debugging_imgs")

# Create the directory if it doesn't exist
try:
    os.makedirs(DEBUGGING_DIR, exist_ok=True)
    logger.debug("Debugging directory created or already exists at: %s", DEBUGGING_DIR)
except OSError as e:
    logger.error("Failed to create debugging directory at %s: %s", DEBUGGING_DIR, e)

# If it does exist, clear out any existing images
for file in os.listdir(DEBUGGING_DIR):
    file_path = os.path.join(DEBUGGING_DIR, file)
    try:
        if os.path.isfile(file_path):
            os.unlink(file_path)
    except OSError as e:
        logger.error("Failed to delete file %s: %s", file_path, e)

# Define the model URL and path
MODEL_URL = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx"
MODEL_DIR = os.path.expanduser("~/.u2net")  # Default directory used by rembg
MODEL_PATH = os.path.join(MODEL_DIR, "u2net.onnx")


def download_model(url: str, path: str):
    """
    Download the u2net.onnx model if it does not exist.

    Parameters:
    - url (str): The URL to download the model from.
    - path (str): The local file path to save the model.
    """
    if not os.path.exists(path):
        logger.info(f"Downloading u2net model from {url} to {path}")
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with urllib.request.urlopen(url) as response, open(path, "wb") as out_file:
                data = response.read()
                out_file.write(data)
            logger.info("u2net model downloaded successfully.")
        except Exception as e:
            logger.error(f"Failed to download u2net model: {e}")
            raise
    else:
        logger.debug("u2net model already exists. Skipping download.")


# Download the model on script startup
download_model(MODEL_URL, MODEL_PATH)


def save_image(image: np.ndarray, filename: str):
    """
    Save an image to the debugging directory.

    Parameters:
    - image (np.ndarray): The image array to save.
    - filename (str): The filename for the saved image.
    """
    logger.debug("Attempting to save image: %s", filename)

    try:
        # Convert image to RGB if it's grayscale
        if len(image.shape) == 2:
            image_to_save = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        else:
            image_to_save = image

        img = Image.fromarray(image_to_save)
        save_path = os.path.join(DEBUGGING_DIR, filename)
        img.save(save_path)
        logger.debug("Saved image: %s", save_path)
    except (OSError, IOError, ValueError) as e:
        logger.error("Failed to save image %s: %s", filename, e)


def remove_background(img: np.ndarray) -> Optional[np.ndarray]:
    """
    Remove the background from an image using the rembg library.

    Parameters:
    - img (np.ndarray): The input image array.

    Returns:
    - Optional[np.ndarray]: The background-removed image array or None if removal fails.
    """
    try:
        output = remove(img, only_mask=True, alpha_matting_foreground_threshold=280)
        logger.debug("Background removed successfully.")
        # Ensure output is a single-channel image
        if len(output.shape) != 2:
            output = cv2.cvtColor(output, cv2.COLOR_RGBA2GRAY)
            logger.debug(
                "Converted background removed image to single-channel grayscale."
            )
        save_image(output, "3-background_removed.png")
        return output
    except RuntimeError as e:
        logger.error("Failed to remove background: %s", e)
        return None


def sharpen_image(img: np.ndarray) -> np.ndarray:
    """
    Sharpen the image using a predefined kernel.

    Parameters:
    - img (np.ndarray): The input image array.

    Returns:
    - np.ndarray: The sharpened image array.
    """
    logger.debug("Entering sharpen_image")
    kernel = np.array([[0, -2, 0], [-2, 10, -2], [0, -2, 0]])
    sharpened_image = cv2.filter2D(img, -1, kernel)
    logger.debug("Image sharpened successfully.")
    save_image(sharpened_image, "2-sharpened_image.png")
    logger.debug("Exiting sharpen_image")
    return sharpened_image


def calculate_line_length(line: Tuple[int, int, int, int]) -> float:
    """
    Calculate the length of a line segment.

    Parameters:
    - line (Tuple[int, int, int, int]): Coordinates of the line (x1, y1, x2, y2).

    Returns:
    - float: Length of the line.
    """
    x1, y1, x2, y2 = line
    length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    return length


def get_direction_vector(line: Tuple[int, int, int, int]) -> Tuple[float, float]:
    """
    Calculate the direction vector of a line.

    Parameters:
    - line (Tuple[int, int, int, int]): Coordinates of the line (x1, y1, x2, y2).

    Returns:
    - Tuple[float, float]: Normalized direction vector (dx, dy).
    """
    x1, y1, x2, y2 = line
    dx = x2 - x1
    dy = y2 - y1
    norm = np.sqrt(dx**2 + dy**2)
    if norm == 0:
        logger.warning("Zero-length line encountered.")
        return (0.0, 0.0)
    vec = (dx / norm, dy / norm)
    return vec


def calculate_parallel_similarity(
    line_1: Tuple[int, int, int, int], line_2: Tuple[int, int, int, int]
) -> float:
    """
    Calculate the similarity of the direction vectors of two lines to determine parallelism.

    Parameters:
    - line_1 (Tuple[int, int, int, int]): Coordinates of the first line.
    - line_2 (Tuple[int, int, int, int]): Coordinates of the second line.

    Returns:
    - float: Similarity score between 0 and 1.
    """
    vec_1 = get_direction_vector(line_1)
    vec_2 = get_direction_vector(line_2)
    dot_product = np.dot(vec_1, vec_2)
    similarity = abs(dot_product)
    return similarity


def lines_proximity(
    line_1: Tuple[int, int, int, int],
    line_2: Tuple[int, int, int, int],
    threshold: float,
) -> bool:
    """
    Check if two lines are in close proximity based on a threshold.

    Parameters:
    - line_1 (Tuple[int, int, int, int]): Coordinates of the first line.
    - line_2 (Tuple[int, int, int, int]): Coordinates of the second line.
    - threshold (float): Distance threshold.

    Returns:
    - bool: True if lines are close, False otherwise.
    """
    # Validate that each line has exactly four coordinates
    if len(line_1) != 4:
        logger.error("Invalid line_1 format: %s. Expected 4 values.", line_1)
        return False
    if len(line_2) != 4:
        logger.error("Invalid line_2 format: %s. Expected 4 values.", line_2)
        return False

    x1, y1, x2, y2 = line_1
    x3, y3, x4, y4 = line_2
    for coord_1 in [np.array((x1, y1)), np.array((x2, y2))]:
        for coord_2 in [np.array((x3, y3)), np.array((x4, y4))]:
            dist = np.linalg.norm(coord_1 - coord_2)
            if dist < threshold:
                return True
    return False


def find_lines_intersection(
    line_1: Tuple[int, int, int, int], line_2: Tuple[int, int, int, int]
) -> Optional[Tuple[float, float]]:
    """
    Find the intersection point of two lines.

    Parameters:
    - line_1 (Tuple[int, int, int, int]): Coordinates of the first line.
    - line_2 (Tuple[int, int, int, int]): Coordinates of the second line.

    Returns:
    - Optional[Tuple[float, float]]: Intersection point or None if lines are parallel.
    """
    x1, y1, x2, y2 = line_1
    x3, y3, x4, y4 = line_2

    vertical_1 = False

    if x1 != x2:
        slope_1 = (y2 - y1) / (x2 - x1)
    else:
        vertical_1 = True

    vertical_2 = False

    if x3 != x4:
        slope_2 = (y4 - y3) / (x4 - x3)
    else:
        vertical_2 = True

    if vertical_1 and vertical_2:
        return None, None

    elif vertical_1:
        x_intersect = x1
        y_intersect = slope_2 * x_intersect + (y3 - slope_2 * x3)

    elif vertical_2:
        x_intersect = x3
        y_intersect = slope_1 * x_intersect + (y1 - slope_1 * x1)

    else:
        intercept_1 = y1 - slope_1 * x1
        intercept_2 = y3 - slope_2 * x3
        if slope_1 != slope_2:
            x_intersect = (intercept_2 - intercept_1) / (slope_1 - slope_2)
        else:
            return None, None
        y_intersect = x_intersect * slope_1 + intercept_1

    return (x_intersect, y_intersect)

    # denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    # if denom == 0:
    #     logger.warning("Lines are parallel; no intersection.")
    #     return None

    # x_intersect = (
    #     (x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)
    # ) / denom
    # y_intersect = (
    #     (x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)
    # ) / denom
    # logger.debug("Intersection point: (%s, %s)", x_intersect, y_intersect)
    # return (x_intersect, y_intersect)


def detect_lines(img: np.ndarray) -> List[List[int]]:
    """
    Detect lines in an image using the Hough Line Transform.

    Parameters:
    - img (np.ndarray): The input image array.

    Returns:
    - list: A list of detected lines, each represented as [x1, y1, x2, y2].
    """
    logger.debug("Entering detect_lines")
    edges = cv2.Canny(img, 40, 150, apertureSize=3)
    save_image(edges, "3-canny_edges.png")

    kernel = np.ones((5, 5), np.uint8)
    edges_dilated = cv2.dilate(edges, kernel, iterations=2)
    save_image(edges_dilated, "4-dilated_edges.png")

    lines = cv2.HoughLinesP(
        edges_dilated, 1, np.pi / 180, 100, minLineLength=100, maxLineGap=100
    )

    if lines is None:
        logger.warning("No lines detected.")
        return []

    flattened_lines = []
    for line in lines:
        if len(line.flatten()) == 4:
            flattened_lines.append(list(line.flatten()))
        else:
            logger.error("Detected line does not have 4 coordinates: %s", line)

    logger.debug("Detected %d valid lines.", len(flattened_lines))

    # Optional: Draw detected lines on the image for debugging
    line_img = img.copy()
    if len(line_img.shape) == 2:  # If grayscale, convert to BGR
        line_img = cv2.cvtColor(line_img, cv2.COLOR_GRAY2BGR)

    for line in flattened_lines:
        x1, y1, x2, y2 = line
        # Draw lines in pink with increased thickness
        cv2.line(line_img, (x1, y1), (x2, y2), (255, 105, 180), 15)  # Pink color in BGR

    save_image(line_img, "5-detected_lines.png")

    logger.debug("Exiting detect_lines")
    return flattened_lines


def filter_unique_lines(lines: list, threshold: float) -> list:
    """
    Filter out lines that are too close to each other.

    Parameters:
    - lines (list): List of detected lines.
    - threshold (float): Distance threshold for proximity.

    Returns:
    - list: Filtered list of unique lines.
    """
    logger.debug("Entering filter_unique_lines")
    unique_lines = []
    for curr_line in lines:
        if not unique_lines:
            unique_lines.append(curr_line)
            continue

        similar = False
        for pivot_line in unique_lines:
            close_coords = lines_proximity(curr_line, pivot_line, threshold)
            similar_angles = calculate_parallel_similarity(curr_line, pivot_line) > 0.92

            if close_coords and similar_angles:
                similar = True
                break

        if similar:
            pivot_length = calculate_line_length(pivot_line)
            curr_length = calculate_line_length(curr_line)
            if curr_length > pivot_length:
                unique_lines.remove(pivot_line)
                unique_lines.append(curr_line)
            continue
        else:
            unique_lines.append(curr_line)

    logger.debug("Filtered down to %d unique lines.", len(unique_lines))

    logger.debug("Exiting filter_unique_lines")
    return unique_lines


def find_most_parallel_pairs(lines: list, threshold: float) -> list:
    """
    Find the two most parallel pairs of lines.

    Parameters:
    - lines (list): List of unique lines.
    - threshold (float): Distance threshold for proximity.

    Returns:
    - list: List containing two pairs of parallel lines.
    """
    logger.debug("Entering find_most_parallel_pairs")
    line_pairs = []
    similarities = []

    for idx, line in enumerate(lines):
        if len(line) != 4:
            logger.error("Line at index %d is malformed: %s", idx, line)
            continue  # Skip malformed lines

        best_pair = None
        best_similarity = 0
        for next_idx, next_line in enumerate(lines):
            if np.array_equal(next_line, line):
                continue
            if len(next_line) != 4:
                logger.error(
                    "Next line at index %d is malformed: %s", next_idx, next_line
                )
                continue  # Skip malformed lines
            if lines_proximity(next_line, line, threshold):
                continue
            similarity = calculate_parallel_similarity(line, next_line)
            if similarity > best_similarity:
                best_pair = (line, next_line)
                best_similarity = similarity

        if best_pair is None:
            continue

        new_pair = True
        for pair in line_pairs:
            best_1, best_2 = best_pair
            curr_1, curr_2 = pair
            if (best_1 == curr_1 and best_2 == curr_2) or (
                best_1 == curr_2 and best_2 == curr_1
            ):
                new_pair = False
                break

        if new_pair:
            line_pairs.append(best_pair)
            similarities.append(float(best_similarity))

    if not similarities:
        logger.warning("No parallel pairs found.")
        return []

    sorted_indices = np.argsort(similarities)[::-1]
    sorted_pairs = [line_pairs[i] for i in sorted_indices]
    best_pairs = [sorted_pairs[0]] if sorted_pairs else []

    i = 1
    while len(best_pairs) < 2 and i < len(sorted_pairs):
        current_pair = sorted_pairs[i]
        if calculate_parallel_similarity(best_pairs[0][0], current_pair[0]) < 0.9:
            best_pairs.append(current_pair)
        i += 1

    if len(best_pairs) < 2 and len(sorted_pairs) > 1:
        best_pairs.append(sorted_pairs[1])

    logger.debug("Found %d parallel pairs.", len(best_pairs))
    logger.debug("Exiting find_most_parallel_pairs")
    return best_pairs


def find_best_corners(
    pairs: list, img: np.ndarray
) -> Optional[List[Tuple[float, float]]]:
    """
    Find the best set of corners from parallel line pairs.

    Parameters:
    - pairs (list): List of parallel line pairs.
    - img (np.ndarray): The image array for visualization.

    Returns:
    - Optional[list]: List of corner points or None if detection fails.
    """
    logger.debug("Entering find_best_corners")
    all_corners = []
    ratio_distances = []
    sets_of_corners = []

    # Iterate over all unique combinations of two pairs
    for i, first_pair in enumerate(pairs):
        for second_pair in pairs[i + 1 :]:
            # Ensure that the pairs are not the same and not parallel
            if (
                first_pair[0] == second_pair[0] and first_pair[1] == second_pair[1]
            ) or (first_pair[1] == second_pair[0] and first_pair[0] == second_pair[1]):
                continue
            if calculate_parallel_similarity(first_pair[0], second_pair[0]) > 0.9:
                continue

            # Find corners from the two pairs
            corners = find_corners_from_lines([first_pair, second_pair], img)
            if corners is None:
                continue

            reformatted_corners = reformat_corners(corners)
            if reformatted_corners is None:
                continue

            sets_of_corners.append(reformatted_corners)
            (x1, y1), (x2, y2), (x3, y3), (x4, y4) = reformatted_corners

            # Calculate width and height to assess ratio
            width_top = calculate_line_length((x1, y1, x2, y2))
            width_bottom = calculate_line_length((x3, y3, x4, y4))
            width = (width_top + width_bottom) / 2

            height_left = calculate_line_length((x1, y1, x4, y4))
            height_right = calculate_line_length((x2, y2, x3, y3))
            height = (height_left + height_right) / 2

            ratio = width / height
            distance_from_1 = abs(ratio - 1)

            all_corners.append([first_pair, second_pair])
            ratio_distances.append(distance_from_1)

    if not ratio_distances:
        logger.error("No valid corner sets found.")
        return None

    # Find the set of corners with the smallest distance from a square ratio
    best_idx = np.argmin(ratio_distances)
    best_corners = sets_of_corners[best_idx]
    logger.debug("Best corners selected: %s", best_corners)
    logger.debug("Exiting find_best_corners")
    return best_corners


def find_corners_from_lines(
    line_pairs: list, img: np.ndarray
) -> Optional[List[Tuple[float, float]]]:
    """
    Find the corners of the square from parallel line pairs.

    Parameters:
    - line_pairs (list): List containing two pairs of parallel lines.
    - img (np.ndarray): The three-channel image array for visualization.

    Returns:
    - list: List of corner points as (x, y) tuples, or None if intersections are invalid.
    """
    logger.debug("Entering find_corners_from_lines")
    corners = []
    if len(line_pairs) < 2:
        logger.warning("Not enough line pairs to determine corners.")
        return None

    pair_1, pair_2 = line_pairs
    for line_1 in pair_1:
        for line_2 in pair_2:
            intersection = find_lines_intersection(line_1, line_2)
            if intersection is None:
                logger.warning(
                    "Intersection failed for lines: %s and %s", line_1, line_2
                )
                continue

            try:
                corners.append((int(intersection[0]), int(intersection[1])))
            except (ValueError, TypeError) as e:
                logger.error("Failed to process intersection: %s", e)
                continue

            # Draw lines and intersections for debugging
            x1, y1, x2, y2 = line_1
            x3, y3, x4, y4 = line_2

            cv2.line(img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 4)
            cv2.line(img, (int(x3), int(y3)), (int(x4), int(y4)), (0, 255, 0), 4)

            # Draw intersection point
            cv2.circle(
                img,
                (int(intersection[0]), int(intersection[1])),
                50,  # Radius
                (255, 0, 0),
                -1,
            )

    save_image(img, "6-corners_detected.png")

    if len(corners) != 4:
        logger.error("Failed to detect exactly 4 corners; detected %d.", len(corners))
        return None

    logger.debug("Detected %d corners.", len(corners))
    logger.debug("Exiting find_corners_from_lines")
    return corners


def detect_corners(img: np.ndarray) -> Optional[List[Tuple[float, float]]]:
    """
    Detect the corners of a square vinyl record in an image.

    Parameters:
    - img (np.ndarray): The background-removed image array.

    Returns:
    - Optional[list]: List of corner points or None if detection fails.
    """
    logger.debug("Entering detect_corners")
    height, width = img.shape[:2]

    # Convert single-channel mask to three-channel BGR image
    if len(img.shape) == 2:
        img_bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        img_bgr = img_bgr.copy()  # Make a writable copy
        logger.debug("Converted single-channel mask to three-channel BGR image.")
    else:
        img_bgr = img.copy()  # Ensure the image is writable
        logger.debug("Image already has multiple channels. Made a writable copy.")

    lines = detect_lines(img)
    proximity_threshold = height * 0.4 if height < width else width * 0.4
    unique_lines = filter_unique_lines(lines, proximity_threshold)

    if len(unique_lines) < 4:
        logger.error("Not enough lines detected to find corners.")
        return None

    best_pairs = find_most_parallel_pairs(unique_lines, proximity_threshold)

    if not best_pairs:
        logger.error("Not enough parallel pairs detected to find corners.")
        return None

    corners = find_best_corners(best_pairs, img_bgr)

    # Ensure corners is valid
    if corners is None:
        logger.error("Corner detection failed.")
        return None
    if corners.size == 0:
        logger.error("Corners array is empty.")
        return None

    # Validate corner positions
    for corner in corners:
        if not (0 <= corner[0] <= width and 0 <= corner[1] <= height):
            logger.warning("Corner out of bounds: %s", corner)
            return None
        else:
            logger.error("Corner detection failed.")

    logger.info("Corners detected successfully.")

    logger.debug("Exiting detect_corners")
    return corners


def reformat_corners(corners: list) -> Optional[np.ndarray]:
    """
    Reformat detected corners to a consistent order: top-left, top-right, bottom-right, bottom-left.

    Parameters:
    - corners (list): List of corner points as (x, y) tuples.

    Returns:
    - Optional[np.ndarray]: Numpy array of reformatted corners or None if formatting fails.
    """
    logger.debug("Entering reformat_corners")
    if len(corners) < 4:
        logger.error("Insufficient corners to reformat.")
        return None

    corners_array = np.float32(corners[:4])
    center = np.mean(corners_array, axis=0)
    x_center, y_center = center

    top_left = top_right = bottom_right = bottom_left = None

    for corner in corners_array:
        x, y = corner
        if x < x_center and y < y_center:
            top_left = corner
        elif x > x_center and y < y_center:
            top_right = corner
        elif x > x_center and y > y_center:
            bottom_right = corner
        elif x < x_center and y > y_center:
            bottom_left = corner

    # Explicitly check each corner for None
    if (
        top_left is None
        or top_right is None
        or bottom_right is None
        or bottom_left is None
    ):
        logger.error("Failed to reformat corners correctly.")
        return None

    corner_inputs = np.float32([top_left, top_right, bottom_right, bottom_left])
    logger.debug("Corners reformatted successfully.")
    logger.debug("Exiting reformat_corners")
    return corner_inputs


def perspective_transform(corners: np.ndarray, img: np.ndarray) -> Optional[np.ndarray]:
    """
    Apply a perspective transform to obtain a top-down view of the vinyl record.

    Parameters:
    - corners (np.ndarray): Numpy array of reformatted corners.
    - img (np.ndarray): The original image array.

    Returns:
    - Optional[np.ndarray]: The warped (transformed) image array or None if transformation fails.
    """
    logger.debug("Entering perspective_transform")
    try:
        if corners.shape != (4, 2):
            logger.error("Expected corners shape (4,2), got %s", corners.shape)
            return None

        length = 500  # Desired output size
        output_coords = np.float32([[0, 0], [length, 0], [length, length], [0, length]])
        transform_matrix = cv2.getPerspectiveTransform(corners, output_coords)
        warped_img = cv2.warpPerspective(
            img, transform_matrix, (length, length), flags=cv2.INTER_LINEAR
        )

        if warped_img is None or warped_img.size == 0:
            logger.error("Warped image is empty.")
            return None

        save_image(warped_img, "7-warped_image.png")

        logger.debug("Perspective transform applied successfully.")
        logger.debug("Exiting perspective_transform")
        return warped_img
    except (ValueError, TypeError) as e:
        logger.exception("Failed to apply perspective transform: %s", e)
        return None


def crop_to_square(image: Image.Image) -> Optional[Image.Image]:
    """
    Extract a square vinyl record from an image.

    Parameters:
    - image (Image.Image): The input PIL Image.

    Returns:
    - Optional[Image.Image]: The cropped square image or None if extraction fails.
    """
    logger.debug("Entering crop_to_square")
    try:
        img_arr = np.array(image)
        logger.debug("Converted PIL image to numpy array.")
        save_image(img_arr, "1-original_image.png")

        sharpened_img = sharpen_image(img_arr)
        logger.debug("Image sharpened.")

        bg_removed_img = 255 * np.uint8(remove_background(sharpened_img) > 150)
        kernel = np.ones((5, 5), np.uint8)
        bg_removed_img_dilated = cv2.dilate(bg_removed_img, kernel)
        if bg_removed_img_dilated is None:
            logger.error("Background removal failed.")
            return None
        logger.debug("Background removed from image.")

        corners = detect_corners(bg_removed_img_dilated)
        if corners is None or corners.size == 0:
            logger.error("Corner detection failed.")
            return None
        logger.debug("Corners detected: %s", corners)

        reformatted_corners = reformat_corners(corners)
        if reformatted_corners is None:
            logger.error("Reformatting corners failed.")
            return None
        logger.debug("Corners reformatted: %s", reformatted_corners)

        warped_img = perspective_transform(reformatted_corners, img_arr)
        if warped_img is None:
            logger.error("Perspective transformation failed.")
            return None
        logger.debug("Perspective transformation applied.")

        warped_pil = Image.fromarray(warped_img)
        logger.info("Vinyl record extracted successfully.")
        logger.debug("Exiting crop_to_square")
        return warped_pil
    except (ValueError, TypeError, RuntimeError) as e:
        logger.exception("Failed to crop to square: %s", e)
        return None


async def bg_removal(image: Image.Image) -> Optional[Image.Image]:
    """
    Remove the background from an image using the rembg library.

    Parameters:
    - image (Image.Image): The input PIL Image.

    Returns:
    - Optional[Image.Image]: The background-removed image or None if removal fails.
    """
    logger.debug("Entering bg_removal")
    try:
        img_arr = np.array(image)
        logger.debug("Converted PIL image to numpy array.")
        save_image(img_arr, "1-original_image.png")

        sharpened_img = sharpen_image(img_arr)
        logger.debug("Image sharpened.")

        bg_removed_img = 255 * np.uint8(remove_background(sharpened_img) > 150)
        kernel = np.ones((5, 5), np.uint8)
        bg_removed_img_dilated = cv2.dilate(bg_removed_img, kernel)
        if bg_removed_img_dilated is None:
            logger.error("Background removal failed.")
            return None
        logger.debug("Background removed from image.")
        save_image(bg_removed_img_dilated, "2-1-background_removed.png")

        bg_removed_img_dilated_pil = Image.fromarray(bg_removed_img_dilated)
        logger.info("Background removed successfully.")
        logger.debug("Exiting bg_removal")

        with BytesIO() as output:
            bg_removed_img_dilated_pil.save(output, format="PNG")
            bg_removed_img_bytes = output.getvalue()
        logger.debug("Album cover converted to bytes successfully.")
        logger.debug("Exiting bg_removal")
        return bg_removed_img_bytes
    except (ValueError, TypeError, RuntimeError) as e:
        logger.exception("Failed to remove background: %s", e)
        return None


async def extract_album_cover(image: Image.Image) -> Optional[bytes]:
    """
    Extract the album cover from an image.

    Parameters:
    - image (Image.Image): The input PIL Image.

    Returns:
    - Optional[bytes]: The extracted album cover in bytes or None if extraction fails.
    """
    logger.debug("Entering extract_album_cover")

    cropped_image = crop_to_square(image)
    if cropped_image is None:
        logger.error("Album cover extraction returned None.")
        return None
    with BytesIO() as output:
        cropped_image.save(output, format="PNG")
        album_cover_bytes = output.getvalue()
    logger.debug("Album cover converted to bytes successfully.")
    logger.debug("Exiting extract_album_cover")
    return album_cover_bytes
