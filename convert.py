#take a list of images and convert to individual numpy arrays
import numpy as np
from PIL import Image
import cv2
def convert_to_numpy():
    with open('../list_of_images.txt') as f:
        line = f.readlines()
        #line.strip('\n')
        for i in line:
            i=i.strip('\n')
            print(i)
            image = Image.open(i)
            # convert image to numpy array
            data = np.asarray(image)
            
            data = cv2.resize(data, (64, 64))

            #img = np.load(data)
            i=i.strip('.jpg')
            np.save(i, data)

convert_to_numpy()
x.res