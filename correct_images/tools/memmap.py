import cv2
from ..loaders import default
import uuid
import numpy as np
import joblib
from tqdm import tqdm
from correct_images.tools.joblib_tqdm import tqdm_joblib


def create_memmap(image_list, loader=default.loader):

    tmp = loader(image_list[0])
    dimensions = tmp.shape

    filename_map = "memmap_" + str(uuid.uuid4()) + ".map"
    list_shape = [len(image_list)] + list(dimensions)
    size = 1
    for i in list_shape:
        size *= i
    image_memmap = np.memmap(filename=filename_map, mode="w+", shape=tuple(list_shape), dtype=np.uint16)
    joblib.Parallel(n_jobs=-1, verbose=0)(
        joblib.delayed(memmap_loader)(image_list, image_memmap, idx, loader, dimensions[1], dimensions[0])
        for idx in range(len(image_list))
    )
    return filename_map, image_memmap


def memmap_loader(image_list, memmap_handle, idx, loader=default.loader, new_width=None, new_height=None):
    np_im = loader(image_list[idx]).astype(np.uint16)
    
    dimensions = np_im.shape

    if new_height is not None and new_width is not None:
        same_dimensions = (new_width == dimensions[1]) and (new_height == dimensions[0])
        if not same_dimensions:
            im2 = cv2.resize(np_im, (new_width, new_height), cv2.INTER_CUBIC)
            memmap_handle[idx, ...] = im2
        else:
            memmap_handle[idx, ...] = np_im    
    else:
        memmap_handle[idx, ...] = np_im