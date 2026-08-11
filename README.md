# orange3-imagetools
## INTRODUCTION
This is a collection of tools for processing and analyzing spectroscopic images based on _scikit-image_ and _scipy_.  
The package includes widgets for analyzing labeled/binary images to extract quantitative features such as area or centroids.  
The **preprocess_snom** folder contains preprocessors that extend the functionalities of the image preprocessing widget from Quasar’s snom package (for more information: https://github.com/Quasars/orange-snom).

## Morphological features widget
<img width="891" height="664" alt="Screenshot 2026-08-04 164256" src="https://github.com/user-attachments/assets/1eed2a40-b413-4972-a32a-dbf50de4d0e7" />

As shown in the image above, the morphological features widget has two layouts:   
 
On the left, you can choose the variable representing your labelled images. You can optionally insert an intensity image to calculate features such as **intensity_max** or **intensity_std**. Such features will not be calculated <ins>if an intensity image is not provided</ins>.  
- The **caching** option serves to speed up calculation when you want to recalculate a property a second time after deselecting it.  
- The **spacing** parameter allows regionprops to compute measurements directly in real-world units rather than pixel indices. By default, _spacing=(1.0, 1.0)_ assumes a standard **unitless** pixel grid. However, if you set spacing=(5, 5) to represent a 5 nm voxel size in both $x$ and $y$ (an isotropic pixel grid), spatial properties adapt accordingly:
Area is calculated as $N_{\text{pixels}} \times (5\text{ nm} \times 5\text{ nm})$, yielding results in $\text{nm}^2$. Perimeter and length measurements will yield results in $\text{nm}$.

The final result is a table where each row rapresents an object in your labelled image and each column is the property.  
**Warning**: Certain multi-dimensional features such as centroid coordinates will be split as separate columns for **each dimension**.



