from AnyQt.QtWidgets import QFormLayout

from orangecontrib.spectroscopy.widgets.preprocessors.utils import BaseEditorOrange
from orangecontrib.spectroscopy.widgets.gui import lineEditFloatRange, lineEditIntRange
from orangewidget.gui import comboBox

from orangecontrib.snom.widgets.preprocessors.registry import preprocess_image_editors
from orangecontrib.snom.preprocess.utils import (
    PreprocessImageOpts2DOnlyWhole,
    MaskOptions,
    _prepare_table_for_image,
    _image_from_table,
    get_mask_from_image_opts,
    transform_mask,
)


from skimage.filters import threshold_otsu
from sklearn.cluster import KMeans

class BinarizationProcessor(PreprocessImageOpts2DOnlyWhole):
    def __init__(self, method="otsu", manual_threshold=0.5, k_clusters=2):
        self.method = method
        self.manual_threshold = float(manual_threshold)
        self.k_clusters = int(k_clusters)



    def transform_image(self, image, data, mask=None):

        # Handles Nan values
        valid_mask = ~np.isnan(image) #tilde flips 0 and 1 values, so that nan become the false values. It's because np.isnotnan doesn't exist
        if not np.any(valid_mask): #If no valid values were found give the image back
            return image
        result_image = np.copy(image)
        valid_pixels = image[valid_mask] #Recovers only the elements of the image which are not Nan

        if self.method == "manual":  # It sets the threshold manually
            result_image[valid_mask] = (valid_pixels > self.manual_threshold).astype(float)
            
        elif self.method == "otsu": #It computes the threshold automatically based on pixel intensity
            try:
                thresh = threshold_otsu(valid_pixels)
                result_image[valid_mask] = (valid_pixels > thresh).astype(float) #creates the mask where values of 1 are those above the calculated threshold
            except ValueError: # It fallsback if an image has constant values
                result_image[valid_mask] = 0.0

        elif self.method == "kmeans": #This version of k-means operates only with the intensity image
            pixels_2d = valid_pixels.reshape(-1, 1) #we need to recreate the 2D image
            
            # sklearn says that n_init=auto improves performances. 
            kmeans = KMeans(n_clusters=self.k_clusters, random_state=42, n_init="auto")
            labels = kmeans.fit_predict(pixels_2d)
            # We order k-means labels based on intensity to be sure that the first labels are always the background
            centers = kmeans.cluster_centers_.flatten()
            ordered_labels = np.argsort(centers) #It gives an array of the indices that would sort the original array
            mapped_labels = np.zeros_like(labels) #Creates an array of zeros of the same shape as labels
            for new_idx, old_idx in enumerate(ordered_labels): 
                mapped_labels[labels == old_idx] = new_idx
                
            result_image[valid_mask] = mapped_labels.astype(float)

        return result_image


class BinarizationEditor(BaseEditorOrange):
    name = "Binarization"
    qualname = "orangecontrib.snom.binarization"

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.method = "otsu"
        self.manual_threshold = 0.5
        self.k_clusters = 3

        form = QFormLayout()
        
        # Menu for method selection
        self.cb_method = comboBox(self, self, "method", callback=self.update_ui)
        self.cb_method.addItems(['otsu', 'manual', 'kmeans'])
        self.cb_method.setCurrentText('otsu')

        # Number input
        self.threshold_edit = lineEditFloatRange(self, self, "manual_threshold", callback=self.edited.emit)
        self.clusters_edit = lineEditIntRange(self, self, "k_clusters", callback=self.edited.emit)

        form.addRow("Method", self.cb_method)
        form.addRow("Manual Threshold", self.threshold_edit)
        form.addRow("Number of Clusters (K)", self.clusters_edit)
        
        self.controlArea.setLayout(form)
        self.update_ui()

    def update_ui(self):
        metodo = self.cb_method.currentText()
        
        # It enables certain settings only if certain methods are active
        self.threshold_edit.setEnabled(metodo == "manual")
        self.clusters_edit.setEnabled(metodo == "kmeans")
        
        self.method = metodo
        self.edited.emit()

    def setParameters(self, params):
        self.method = params.get("method", "otsu")
        self.manual_threshold = float(params.get("manual_threshold", 0.5))
        self.k_clusters = int(params.get("k_clusters", 3))
        self.update_ui()

    @classmethod
    def createinstance(cls, params):
        params = dict(params)
        method = str(params.get("method", "otsu"))
        manual_threshold = float(params.get("manual_threshold", 0.5))
        k_clusters = int(params.get("k_clusters", 3))
        
        return BinarizationProcessor(
            method=method, 
            manual_threshold=manual_threshold, 
            k_clusters=k_clusters
        )


preprocess_image_editors.register(BinarizationEditor, 610)