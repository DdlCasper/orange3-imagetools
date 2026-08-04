# orange3-imagetools
## INTRODUCTION
This is a collection of tools for processing and analyzing spectroscopic images based on scikit-image and scipy.\ 
The package includes widgets for analyzing pre-labeled binary images to extract quantitative features such as area or centroids.
The preprocess_snom folder contains preprocessors that extend the functionalities of the image preprocessing widget from Quasar’s snom module (for more information: https://github.com/Quasars/orange-snom).

## Morphological features widget
<img width="891" height="664" alt="Screenshot 2026-08-04 164256" src="https://github.com/user-attachments/assets/1eed2a40-b413-4972-a32a-dbf50de4d0e7" />

As shown in the image above, the morphological features widget has two layouts. 
On the left, you can choose the variable representing your labelled images. You can optionally insert an intensity image to calculate features such as intensity_max or intensity_std. Such features will not be calculated if an intensity image is not provided.
The caching option serves to speed up calculation when you want to recalculate a property a second time after deselecting it.
The spacing option is very important as it allows you to calculate the properties of the region according to your unit of measurement and spatial resolution. To be more precise, if spacing is (1.0,1.0) as it is by default, it means that your image is isotropic and features such as perimeter will have pixels as their unit of measurement.
For example, if your pixel resolution is 5nm for both x and y, area will be calculated as: N.pixels*(5nm*5nm). So your area will have nm^2 as a measurement unit.





