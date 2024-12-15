import torch

def get_device():
    """
    Determines the best available device for PyTorch computations.

    Returns:
        torch.device: The best available device. It returns 'cuda' if a GPU is available,
                      'mps' if an Apple Silicon GPU is available, and 'cpu' otherwise.
    """
    if torch.cuda.is_available():
        return torch.device('cuda')
    elif torch.backends.mps.is_available():
        return torch.device('mps')
    else:
        return torch.device('cpu')

def get_fasterrnn_classes():
    """
    Returns the FasterRNN classes.

    Returns:
        tuple: A tuple containing the FasterRNN classes.
    """
    from torchvision.models.detection import FasterRCNN_ResNet50_FPN_Weights
    weights = FasterRCNN_ResNet50_FPN_Weights.DEFAULT
    return weights.meta['categories']

def make_plot_fasterrnn(pil_input_image, fasterrnn_result, classes = None, save_path = 'output.png'):
    """
    This function takes a PIL image and a FasterRNN result and plots the image with the detected objects.
    
    Note: this function is not working... When I pass in a PIL image some pythonic 
    error occurs. Code is still kept here so that I can copy it later.
    
    Args:
        pil_input_image (PIL.Image): The input image.
        fasterrnn_result (dict): The FasterRNN result dictionary.
        classes (tuple): The classes to use for the plot. If None, the default FasterRNN classes are used.
    
    Returns:
        None
    """
    if classes is None:
        classes = get_fasterrnn_classes()
    
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches

    # Plot the actual PIL image
    fig, ax = plt.subplots(1)
    ax.imshow(pil_input_image)

    # Extract boxes, labels, and scores
    boxes = fasterrnn_result['boxes'].detach().numpy()
    labels = fasterrnn_result['labels'].detach().numpy()
    scores = fasterrnn_result['scores'].detach().numpy()

    # Plot the boxes on the image
    for box, label, score in zip(boxes, labels, scores):
        if score > 0.5:  # Only plot boxes with a score above 0.5
            rect = patches.Rectangle((box[0], box[1]), box[2] - box[0], box[3] - box[1], linewidth=2, edgecolor='r', facecolor='none')
            ax.add_patch(rect)
            ax.text(box[0], box[1] - 10, f'{classes[label]}: {score:.2f}', bbox=dict(facecolor='yellow', alpha=0.5))

    fig.savefig(save_path)

def get_colormap(labels): 
    """
    This function returns a colormap for a given list of labels. Ensures that 
    the colormap is consistent across different runs between each label and
    that the colormap is visually distinguishable.
    
    Args:
        labels (list): The list of labels.
    
    Returns:
        dict: A dictionary mapping each label to a color.
    """
    import matplotlib.pyplot as plt
    import random

    # Set a random seed for reproducibility
    random.seed(42)

    # Generate a random color for each label
    colormap = {label: plt.cm.get_cmap('tab20')(random.random()) for label in labels}

    return colormap

def show(pil_image, bbs, scores, labels, cmap, classes, filter = None, ax = None): 
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    
    if ax is None: 
        fig, ax = plt.subplots(1)
    else: 
        fig = None
    
    # Convert bbs, scores, and labels to numpy arrays if they are tensors
    if torch.is_tensor(bbs):
        bbs = bbs.detach().numpy()
    if torch.is_tensor(scores):
        scores = scores.detach().numpy()
    if torch.is_tensor(labels):
        labels = labels.detach().numpy()
        
    assert len(bbs) == len(scores) == len(labels)
    assert len(bbs) > 0, 'No bounding boxes to plot'
    
    if all(bbs[0][i] <= 1.0 for i in range(4)):
        # that means the bounding boxes are normalized
        w,h = pil_image.size
        bbs = bbs * [w, h, w, h]
    
    if not isinstance(labels[0], int): 
        labels = [int(l) for l in labels]
    # Plot the actual PIL image
    
    ax.imshow(pil_image)
    ax.axis('off')
    
    if filter is not None: 
        assert isinstance(filter, float)
        bbs = bbs[scores > filter]
        labels = labels[scores > filter]
        scores = scores[scores > filter]
    
    for box, label, score in zip(bbs, labels, scores): 
        color = cmap(int(label))
        bb = patches.Rectangle((box[0], box[1]), box[2] - box[0], box[3] - box[1],
                               linewidth=2, edgecolor=color, facecolor='none')
        ax.add_patch(bb)
        ax.text(box[0], box[1] - 5, f'{classes[label]}: {score:.2f}', 
                bbox=dict(facecolor=color, alpha=0.5))
        
    return fig