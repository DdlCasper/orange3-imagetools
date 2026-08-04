from AnyQt.QtWidgets import QFormLayout

from orangecontrib.spectroscopy.widgets.preprocessors.utils import BaseEditorOrange
from orangecontrib.spectroscopy.widgets.gui import lineEditIntRange
from orangewidget.gui import comboBox

from orangecontrib.snom.widgets.preprocessors.registry import preprocess_image_editors
from orangecontrib.snom.preprocess.utils import (
    PreprocessImageOpts2DOnlyWhole
)

import numpy as np
from scipy.ndimage import grey_opening, grey_closing, grey_dilation, grey_erosion, binary_fill_holes


class MorphologyProcessor(PreprocessImageOpts2DOnlyWhole):
    def __init__(self, method="opening", size=3):
        self.method = method
        self.size = int(size)

    def transform_image(self, image, data, mask=None):
        # This is to handle NaN value, especially the borders
        valid_mask = ~np.isnan(image)
        if not np.any(valid_mask):
            return image

        result_image = np.copy(image)
        
        # Nan is replaced by 0 to not compromise the calculations
        temp_image = np.nan_to_num(image, nan=0.0)

        # Creiamo l'elemento strutturante (il "pennello" con cui operiamo, es. 3x3)
        structure = np.ones((self.size, self.size))

        # Filters
        if self.method == "opening":
            # Removes background outliers
            processed = grey_opening(temp_image, structure=structure)
            
        elif self.method == "closing":
            # Fills the holes inside the blobs
            processed = grey_closing(temp_image, structure=structure)
            
        elif self.method == "dilation":
            # Expands blob boundaries
            processed = grey_dilation(temp_image, structure=structure)
            
        elif self.method == "erosion":
            # Shrinks blob boundaries
            processed = grey_erosion(temp_image, structure=structure)
            
        elif self.method == "fill_holes":
            # WORKS ONLY ON BOOLEAN MAPS 
            # Foreground is everything above 0
            binary_img = temp_image > 0
            filled = binary_fill_holes(binary_img, structure=structure)
            
            
            processed = temp_image.copy()
            holes_mask = filled & ~binary_img
            max_val = np.max(temp_image) if np.max(temp_image) > 0 else 1.0
            processed[holes_mask] = max_val
            
        else:
            processed = temp_image

        # We place Nan values back 
        result_image[valid_mask] = processed[valid_mask]
        
        return result_image


class MorphologyEditor(BaseEditorOrange):
    name = "Morphology Cleaner"
    qualname = "orangecontrib.snom.morphology"

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.method = "opening"
        self.size = 3

        form = QFormLayout()
        
        # Menu
        self.cb_method = comboBox(self, self, "method", callback=self.edited.emit)
        self.cb_method.addItems(['opening', 'closing', 'dilation', 'erosion', 'fill_holes'])
        self.cb_method.setCurrentText('opening')

        # Kernel size
        self.size_edit = lineEditIntRange(self, self, "size", callback=self.edited.emit)

        form.addRow("Operation", self.cb_method)
        form.addRow("Element Size (Pixels)", self.size_edit)
        
        self.controlArea.setLayout(form)
        self.update_ui()
        
    def update_ui(self):
        metodo = self.cb_method.currentText()
                
        self.method = metodo
        self.edited.emit()

    def setParameters(self, params):
        self.method = params.get("method", "opening")
        self.size = int(params.get("size", 3))
        self.update_ui()
        
    @classmethod
    def createinstance(cls, params):
        params = dict(params)
        method = str(params.get("method", "opening"))
        size = int(params.get("size", 3))
        
        return MorphologyProcessor(method=method, size=size)


preprocess_image_editors.register(MorphologyEditor, 620)
