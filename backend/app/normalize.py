from PIL import Image
import cv2
import numpy as np
import matplotlib.pyplot as plt
# import matplotlib
# import torch
# from torchvision.models.detection import fasterrcnn_resnet50_fpn 
# from torchvision.models.detection import FasterRCNN_ResNet50_FPN_Weights
from rembg import remove
import glob


def remove_background(img):
    output_path = 'backend/app/test_outputs/output.png'

    input = img
    output = remove(input, only_mask=True, alpha_matting_foreground_threshold=280)
    # output.save(output_path)
    return output

def detect_corners(img):

    # # convert PIL image to numpy array
    img = np.array(img)

    # make image grayscale
    preprocessed_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # turn image to float32 type
    preprocessed_img = np.float32(preprocessed_img)

    corner_probs = cv2.cornerHarris(preprocessed_img, 2, 5, 0.07)

    # print(corner_probs)
    print(img[corner_probs > 0.01 * corner_probs.max()])


    #result is dilated for marking the corners, not important
    corner_probs = cv2.dilate(corner_probs,None)

    # print(corner_probs > 0.01 * corner_probs.max())

    corner_probs = (corner_probs - np.min(corner_probs))/(np.max(corner_probs) - np.min(corner_probs))
    print(np.min(corner_probs))
    print(np.max(corner_probs))

    img[corner_probs > 0.66 * corner_probs.max()]=[0, 0, 255] 

    print(corner_probs)

    print("corner_probs shape:", corner_probs.shape)
    print("img shape:", img.shape)

    cv2.imshow('corner_probs', img)

    if cv2.waitKey(0) & 0xff == 27:
        cv2.destroyAllWindows()


def sharpen_image(img):

    img = np.array(img)
    # Create the sharpening kernel 
    # kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]]) 

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

    img = np.array(img)
    height = img.shape[0]
    width = img.shape[1]

    # Canny edge detection
    edges = cv2.Canny(img, 50, 150, apertureSize=3)

    # Hough Line Transform
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, 70, minLineLength=100, maxLineGap=70)

    flattened_lines = [list(line.flatten()) for line in lines]

    for line in flattened_lines:
        x1, y1, x2, y2 = line
        print(f'{x1}, {y1} - {x2}, {y2}')
        plt.plot([x1, x2], [y1,y2], color='red')
    plt.imshow(img)
    plt.show()

    lines = flattened_lines

    # TODO: filter out unique lines more

    unique_lines = []
    threshold = height * 0.15 if height < width else width * 0.15
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
    


    for line in unique_lines:
        x1, y1, x2, y2 = line
        print(f'{x1}, {y1} - {x2}, {y2}')
        plt.plot([x1, x2], [y1,y2], color='red')
    plt.imshow(img)
    plt.show()


    line_pairs = []
    distances = []

    
    for line in unique_lines:
        best_pair = None
        best_similarity = 0
        # print(curr_vec.shape)
        for next_line in unique_lines:
            if np.array_equal(next_line, line):
                continue
            if lines_proximity(next_line, line, threshold):
                continue
            # print(next_vec.shape)
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
    while len(best_pairs) < 2:
        curr_pair = sorted_pairs[i]
        if calculate_parallel_similarity(best_pairs[0][0], curr_pair[0]) < 0.92:
            best_pairs.append(curr_pair)
        i += 1

    # idx = 0
    # for pair in best_pairs:
    #     print("\nPAIR:")
    #     for line in pair:
    #         x1, y1, x2, y2 = line
    #         print(f'{x1}, {y1} - {x2}, {y2}')
    #         plt.plot([x1, x2], [y1,y2], color='red')
    #     print(distances[sorted_dist_indexes[idx]])
    #     idx += 1
    #     plt.imshow(img)
    #     plt.show()
    
    pair_1 = best_pairs[0]
    pair_2 = best_pairs[1]

    corners = []
    
    for line_1 in pair_1:
        for line_2 in pair_2:
            x1, y1, x2, y2 = line_1
            x3, y3, x4, y4 = line_2
            x_intersect, y_intersect = find_lines_intersection(line_1, line_2)
            corners.append((x_intersect, y_intersect))
            # print(line_1)
            # print(line_2)
            # print(x_intersect, y_intersect)
            plt.plot([x1, x2], [y1,y2], color='red')
            plt.plot([x3, x4], [y3,y4], color='red')
            plt.plot(x_intersect, y_intersect, 'bo')
    plt.imshow(img)
    plt.show()



def crop_to_square(image: Image): 
    pass
    changed_img = image.copy()
    return changed_img

# path = 'backend/app/test_images/IMG_5415.JPG'

# for filename in glob.glob("backend/app/test_images/*"): 
# for filename in ['backend/app/test_images/IMG_5359-0049.jpg']:
for filename in ['backend/app/test_images/IMG_5348-0001.jpg']:
    print(filename)
    img = Image.open(filename)
    plt.imshow(img)
    plt.title("original image")
    plt.show()
    sharpened_img = sharpen_image(img)
    plt.imshow(sharpened_img)
    plt.title("sharpened image")
    plt.show()
    bg_removed_img = remove_background(sharpened_img)
    plt.imshow(bg_removed_img)
    plt.title("background removed image")
    plt.show()
    detect_lines(bg_removed_img)

