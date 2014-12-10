"""
Simple demo of the imshow function.
"""
import matplotlib.pyplot as plt
import matplotlib.cbook as cbook

datafile = cbook.get_sample_data('ada.png', asfileobj=False)
image = plt.imread(datafile)

plt.imshow(image)
plt.axis('off') # clear x- and y-axes
