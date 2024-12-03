from PIL import Image
import numpy as np
from functools import lru_cache

# @lru_cache(maxsize=128)
def vectorize(image: Image): 
    pixels = np.array(image)
    vector = pixels[:3, :, 1].flatten()
    return vector