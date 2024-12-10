from PIL import Image
import numpy as np


def vectorize(image: Image):
    pixels = np.array(image)
    vector = pixels[:3, :, 1].flatten()
    return vector
