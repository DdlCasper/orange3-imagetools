from AnyQt.QtWidgets import QFormLayout

from orangecontrib.spectroscopy.widgets.preprocessors.utils import BaseEditorOrange
from orangecontrib.spectroscopy.widgets.gui import lineEditFloatRange
from orangewidget.gui import comboBox

from orangecontrib.snom.widgets.preprocessors.registry import preprocess_image_editors
from orangecontrib.snom.preprocess.utils import (
    PreprocessImageOpts2DOnlyWhole
)

from scipy.ndimage import gaussian_filter, median_filter, uniform_filter
from skimage.restoration import denoise_bilateral

class SpatialFilterProcessor(PreprocessImageOpts2DOnlyWhole):
    def __init__(self, method="gaussian", mode="reflect", sigma=1.0, size=3, sigma_intensity=0.1):
        self.method = method
        self.sigma = float(sigma)
        self.size = int(size)
        self.sigma_intensity = float(sigma_intensity)
        self.mode = mode

    def transform_image(self, image, data, mask=None):

        if self.method == "gaussian":
            return gaussian_filter(image, sigma=self.sigma, mode=self.mode)
        
        elif self.method == "median":
            return median_filter(image, size=self.size, mode=self.mode)

        elif self.method == "uniform":
            return uniform_filter(image, size = self.size, mode=self.mode)
            
        elif self.method == "bilateral":
            return denoise_bilateral(
                image, 
                sigma_spatial=self.sigma, 
                sigma_color=self.sigma_intensity, 
                mode=self.mode
            )
        return image
    
class SpatialFilterEditor(BaseEditorOrange):
    name = "Spatial Filter"
    qualname = "orangecontrib.snom.spatial_filter"

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.method = "gaussian"
        self.mode = "reflect"
        self.sigma = 1.0
        self.size = 3 
        self.sigma_intensity = 0.0

        form = QFormLayout()
        
        # Method
        self.cb_method = comboBox(self, self, "method", callback=self.update_ui)
        self.cb_method.addItems(['gaussian', 'median', 'uniform', 'bilateral'])
        self.cb_method.setCurrentText('gaussian')

        # Mode
        self.cb_mode = comboBox(self, self, "mode", callback=self.update_ui)
        self.cb_mode.addItems(['reflect', 'constant', 'nearest', 'mirror', 'wrap'])
        self.cb_mode.setCurrentText('reflect')

        # Parameters
        self.sigma_edit = lineEditFloatRange(self, self, "sigma", callback=self.edited.emit)
        self.size_edit = lineEditFloatRange(self, self, "size", callback=self.edited.emit)
        self.sigma_intensity_edit = lineEditFloatRange(self, self, "sigma_intensity", callback=self.edited.emit)

        # Layout
        form.addRow("Method", self.cb_method)
        form.addRow("Mode", self.cb_mode)
        form.addRow("Spatial similarity", self.sigma_edit)
        form.addRow("Intensity similarity", self.sigma_intensity_edit)
        form.addRow("Kernel Size", self.size_edit)
        
        self.controlArea.setLayout(form)
        self.update_ui()

    def update_ui(self):
        metodo = self.cb_method.currentText() #calls the text chosen in line 162
        
        # Abilita/Disabilita in base al filtro scelto
        self.sigma_edit.setEnabled(metodo in ["gaussian", "bilateral"])
        self.size_edit.setEnabled(metodo in ["median", "uniform"])
        self.sigma_intensity_edit.setEnabled(metodo == "bilateral")
        
        self.cb_mode.setEnabled(metodo in ["gaussian","median", "uniform"])
        self.mode = self.cb_mode.currentText() #calls the text chosen in line 167
        self.method = metodo
        self.edited.emit()

    def setParameters(self, params):
        self.method = params.get("method", "gaussian")
        self.mode = params.get("mode", "reflect")
        self.sigma = float(params.get("sigma", 1.0))
        self.size = int(params.get("size", 3))
        self.sigma_intensity = float(params.get("sigma_intensity", 0.0))
        self.update_ui()

    @classmethod
    def createinstance(cls, params):
        params = dict(params)
        method = str(params.get("method", "gaussian"))
        mode = str(params.get("mode", "reflect"))
        sigma = float(params.get("sigma", 1.0))
        size = int(params.get("size", 3))
        sigma_intensity = float(params.get("sigma_intensity", 0.0))
        
        return SpatialFilterProcessor(
            method=method, 
            sigma=sigma, 
            size=size, 
            mode=mode, 
            sigma_intensity=sigma_intensity
        )

    def set_preview_data(self, data):
        pass


preprocess_image_editors.register(SpatialFilterEditor, 600)