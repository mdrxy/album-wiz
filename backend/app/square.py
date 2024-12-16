from PIL import Image
import cv2
import numpy as np
import matplotlib.pyplot as plt
from rembg import remove
import glob


def remove_background(img):
    output = remove(img, only_mask=True, alpha_matting_foreground_threshold=280)
    return output


def sharpen_image(img):
    # Create the sharpening kernel 
    kernel = np.array([[0, -2, 0], 
                       [-2, 10, -2], 
                       [0, -2, 0]])
    
    # Sharpen the image 
    sharpened_image = cv2.filter2D(img, -1, kernel) 

    return sharpened_image

def calculate_line_length(line):
    x1, y1, x2, y2 = line
    length = np.sqrt((x2-x1)**2 + (y2-y1)**2)
    return length

def get_direction_vector(line):
    x1, y1, x2, y2 = line
    dx = x2-x1
    dy = y2-y1
    norm = np.sqrt(dx**2 + dy**2)
    vec = (dx / norm, dy / norm)
    return vec

def calculate_parallel_similarity(line_1, line_2):
    vec_1 = get_direction_vector(line_1)
    vec_2 = get_direction_vector(line_2)
    dot_product = np.dot(vec_1, vec_2)
    similarity = abs(dot_product)
    return similarity

def lines_proximity(line_1, line_2, threshold):
    x1, y1, x2, y2 = line_1
    x3, y3, x4, y4 = line_2
    for coord_1 in [np.array((x1, y1)), np.array((x2, y2))]:
        for coord_2 in [np.array((x3, y3)), np.array((x4, y4))]:
            dist = np.sqrt(np.sum(np.square(coord_1 - coord_2)))
            if dist < threshold:
                return True
    return False

def find_lines_intersection(line_1, line_2):
    x1, y1, x2, y2 = line_1
    slope_1 = (y2-y1) / (x2-x1)
    intercept_1 = y1 - slope_1 * x1

    x3, y3, x4, y4 = line_2
    slope_2 = (y4-y3) / (x4-x3)
    intercept_2 = y3 - slope_2 * x3

    x_intersect = (intercept_2 - intercept_1) / (slope_1 - slope_2)
    y_intersect = x_intersect * slope_1 + intercept_1

    return (x_intersect, y_intersect)

def detect_lines(img):
    # Canny edge detection
    edges = cv2.Canny(img, 50, 150, apertureSize=3)

    edges_dilated = cv2.dilate(edges, None)

    # Hough Line Transform
    lines = cv2.HoughLinesP(edges_dilated, 1, np.pi/180, 100, minLineLength=100, maxLineGap=100)

    flattened_lines = [list(line.flatten()) for line in lines]

    # for line in flattened_lines:
    #     x1, y1, x2, y2 = line
    #     s = f'{x1} {y1}  {x2} {y2}'
    #     plt.plot([x1, x2], [y1,y2], color='red')
    #     plt.text(x1, y1, s, color='white', fontsize=10)
    # plt.title('flattened lines')
    # plt.imshow(img)
    # plt.show()

    return flattened_lines

def filter_unique_lines(lines, threshold):

    unique_lines = []
    for curr_line in lines:
        if len(unique_lines) == 0:
            unique_lines.append(curr_line)
            continue
        similar_lines = False
        for pivot_line in unique_lines: # TODO: change pivot_line variable name
            close_coords = lines_proximity(curr_line, pivot_line, threshold)
            similar_angles = calculate_parallel_similarity(curr_line, pivot_line) > 0.92

            if close_coords and similar_angles: similar_lines = True

            if similar_lines: break

        if similar_lines:
            pivot_length = calculate_line_length(pivot_line)
            curr_length = calculate_line_length(curr_line)
            if curr_length > pivot_length:
                unique_lines.remove(pivot_line)
                unique_lines.append(curr_line)
            continue
        
        else:
            unique_lines.append(curr_line)

    # for line in unique_lines:
    #     x1, y1, x2, y2 = line
    #     s = f'{x1} {y1}  {x2} {y2}'
    #     plt.plot([x1, x2], [y1,y2], color='red')
    #     plt.text(x1, y1, s, color='white', fontsize=10)
    # plt.title('unique lines (1st filter)')
    # plt.imshow(img)
    # plt.show()

    return unique_lines


def find_most_parallel_pairs(lines, threshold):
    line_pairs = []
    distances = []
    
    for line in lines:
        best_pair = None
        best_similarity = 0
        for next_line in lines:
            if np.array_equal(next_line, line):
                continue
            if lines_proximity(next_line, line, threshold):
                continue
            similarity = calculate_parallel_similarity(line, next_line)
            if similarity > best_similarity:
                best_pair = (line, next_line)
                best_similarity = similarity

        new_pair = True
        for pair in line_pairs:
            best_1, best_2 = best_pair
            curr_1, curr_2 = pair
            if (best_1 == curr_1 or best_2 == curr_2) or (best_1 == curr_2 and best_2 == curr_1):
                new_pair = False
                break
        if new_pair:
            line_pairs.append(best_pair)
            distances.append(float(best_similarity))
    
    sorted_dist_indexes = np.argsort(distances)[::-1]

    sorted_pairs = [line_pairs[i] for i in sorted_dist_indexes]

    best_pairs = [sorted_pairs[0]]
    
    i = 1
    while len(best_pairs) < 2 and i < len(sorted_pairs):
        curr_pair = sorted_pairs[i]
        if calculate_parallel_similarity(best_pairs[0][0], curr_pair[0]) < 0.9:
            best_pairs.append(curr_pair)
        i += 1
    
    if len(best_pairs) < 2:
        best_pairs.append(sorted_pairs[1])
    
    return best_pairs


def find_corners_from_lines(line_pairs):
    corners = []
    pair_1 = line_pairs[0]
    pair_2 = line_pairs[1]
    for line_1 in pair_1:
        for line_2 in pair_2:
            x_intersect, y_intersect = find_lines_intersection(line_1, line_2)
            corners.append((x_intersect, y_intersect))
            x1, y1, x2, y2 = line_1
            x3, y3, x4, y4 = line_2
            plt.plot([x1, x2], [y1,y2], color='red')
            plt.plot([x3, x4], [y3,y4], color='red')
            plt.plot(x_intersect, y_intersect, 'bo')
    plt.imshow(img)
    plt.show()

    return corners


def detect_corners(img):
    height = img.shape[0]
    width = img.shape[1]

    lines = detect_lines(img)

    proximity_threshold = height * 0.3 if height < width else width * 0.3
    unique_lines = filter_unique_lines(lines, proximity_threshold)

    if len(unique_lines) < 4:
        print("ERROR: NOT ENOUGH LINES FOUND")
        return
    
    best_pairs = find_most_parallel_pairs(unique_lines, proximity_threshold)

    corners = find_corners_from_lines(best_pairs)

    for corner in corners:
        if not (0 <= corner[0] <= width and 0 <= corner[1] <= height):
            return None

    return corners


def reformat_corners(corners):
    x1, y1 = corners[0]
    x2, y2 = corners[1]
    x3, y3 = corners[2]
    x4, y4 = corners[3]

    corners_array = np.float32([[x1, y1], [x2, y2], [x3, y3], [x4, y4]])
    top_left = None
    top_right = None
    bottom_right = None
    bottom_left = None
    center = np.mean(corners_array, axis=0)
    x_center = center[0]
    y_center = center[1]

    for corner in corners_array:
        top = False
        bottom = False
        left = False
        right = False

        if corner[0] > x_center:
            right = True
        else:
            left = True

        if corner[1] < y_center:
            top = True
        else:
            bottom = True
    
        if top and left: top_left = corner
        elif top and right: top_right = corner
        elif bottom and right: bottom_right = corner
        elif bottom and left: bottom_left = corner

    if top_left is None or top_right is None or bottom_right is None or bottom_left is None:
        return None
    
    corner_inputs = np.float32([top_left, top_right, bottom_right, bottom_left])
    
    return corner_inputs


def perspective_transform(corners, img):
    input_coords = reformat_corners(corners)
    if input_coords is None:
        return None

    length = 500
    output_coords = np.float32([[0, 0], [length, 0], [length, length], [0, length]])
    transform_matrix = cv2.getPerspectiveTransform(input_coords, output_coords)
    warped_img = cv2.warpPerspective(img, transform_matrix, (length, length), flags=cv2.INTER_LINEAR)

    warped_pil = Image.fromarray(warped_img)
    # warped_pil.save('backend/app/test_outputs/output.jpg')
    return warped_pil


def crop_to_square(image: Image): 
    pass
    img_arr = np.array(img)
    sharpened_img = sharpen_image(img_arr)
    bg_removed_img = remove_background(sharpened_img)
    corners = detect_corners(bg_removed_img)
    warped_img = perspective_transform(corners, img_arr)
    return warped_img

# path = 'backend/app/test_images/IMG_5415.JPG'

total_imgs = 0
correct_imgs = 0

for filename in glob.glob("backend/app/test_images/*"): 
# for filename in ['backend/app/test_images/IMG_5415.JPG']:
# for filename in ['backend/app/test_images/IMG_5359-0049.jpg']:
# for filename in ['backend/app/test_images/IMG_5348-0001.jpg']:
# for filename in ['backend/app/test_images/IMG_5353-0013.jpg']:
    total_imgs += 1
    print("IMAGE: ", filename)
    img = Image.open(filename)
    # plt.imshow(img)
    # plt.title(f"original image: {filename}")
    # plt.show()
    img_arr = np.array(img)
    sharpened_img = sharpen_image(img_arr)
    # print(type(sharpened_img))
    # plt.imshow(sharpened_img)
    # plt.title("sharpened image")
    # plt.show()
    bg_removed_img = remove_background(sharpened_img)
    # print(type(bg_removed_img))
    # plt.imshow(bg_removed_img)
    # plt.title("background removed image")
    # plt.show()
    corners = detect_corners(bg_removed_img)
    if corners == None:
        print("Corners out of bounds")
    else:
        warped_img = perspective_transform(corners, img_arr)
        if warped_img is None:
            print("Unable to transform image")
        else:
            correct_imgs += 1
            print("Successfully transformed image")
            idx = len('backend/app/test_images/')
            new_filename = filename[idx:]
            warped_img.save(f"backend/app/test_outputs/output_{new_filename}")
            # plt.imshow(warped_img)
            # plt.title("warped image")
            # plt.show()

print('\n')
print('Total number of images: ', total_imgs)
print('Number of correct images: ', correct_imgs)
