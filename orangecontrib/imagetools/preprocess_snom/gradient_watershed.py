from AnyQt.QtWidgets import QFormLayout

from orangecontrib.spectroscopy.widgets.preprocessors.utils import BaseEditorOrange
from orangecontrib.spectroscopy.widgets.gui import lineEditFloatRange, lineEditIntRange


from Orange.data import Domain, Table, DiscreteVariable
from orangecontrib.snom.widgets.preprocessors.registry import preprocess_image_editors
from orangecontrib.snom.preprocess.utils import (
    PreprocessImageOpts2DOnlyWhole,
    _prepare_table_for_image,
    _image_from_table,
    get_mask_from_image_opts,
)

import numpy as np
from scipy.ndimage import distance_transform_edt
from skimage.measure import label
from skimage.feature import peak_local_max
from skimage.segmentation import watershed
from scipy.ndimage import gaussian_gradient_magnitude

class SpectralWatershedProcessor(PreprocessImageOpts2DOnlyWhole):
    def __init__(self, min_distance=10, grad_sigma=1.0):
        self.min_distance = int(min_distance)
        self.grad_sigma = float(grad_sigma)

    def __call__(self, data, image_opts, run_all=False):
        if run_all or len(data.domain.attributes) == 0:
            attrs_to_run = [v.name for v in data.domain.attributes]
            newdata = data.copy()
        else:
            attrs_to_run = [image_opts["attr_value"]]
            newdata = _prepare_table_for_image(data, image_opts)

        mask = get_mask_from_image_opts(data, image_opts)
        image_opts = image_opts.copy()

        
        temp_init = _prepare_table_for_image(data, image_opts)
        base_image, indices = _image_from_table(temp_init, image_opts)
        h, w = base_image.shape
        
        # Calculate the Spectral Gradient Map
        spectral_gradient = np.zeros((h, w))
        
        for attr in data.domain.attributes:
            # Extract 1D array for this specific wavelength and reshape to 2D
            band_vals = data[:, attr].X.flatten()
            band_image = np.full((h, w), np.nan)
            band_image[indices] = band_vals
            
            # Handle NaNs for gradient calculation
            band_image = np.nan_to_num(band_image, nan=0.0)
            
            # Calculate structural edges for this band and add to the global map
            grad = gaussian_gradient_magnitude(band_image, sigma=self.grad_sigma)
            spectral_gradient += grad
            
        # Normalize the gradient map to a 0.0 - 1.0 range
        if np.max(spectral_gradient) > 0:
            spectral_gradient /= np.max(spectral_gradient)

        # 4. Apply the watershed using the spectral gradient
        new_vals = np.full_like(newdata.X, np.nan)
        object_vals = None

        for i, attr in enumerate(attrs_to_run):
            image_opts["attr_value"] = attr
            temp = _prepare_table_for_image(newdata, image_opts)
            image, current_indices = _image_from_table(temp, image_opts)
            
            transformed = self.apply_spectral_watershed(image, spectral_gradient, mask)
            new_vals[:, i] = transformed[current_indices].reshape(-1)
            
            if object_vals is None:
                object_vals = transformed[current_indices].reshape(-1)

        with newdata.unlocked(newdata.X):
            newdata.X = new_vals

        
        if object_vals is not None:
            unique_vals = np.unique(object_vals[~np.isnan(object_vals)])
            str_values = [str(int(v)) for v in unique_vals]
            
            object_attr = DiscreteVariable("object", values=str_values)
            #
            existing_names = [v.name for v in newdata.domain.variables + newdata.domain.metas]
            base_name = "object"
            new_name = base_name
            counter = 1
            
            while new_name in existing_names:
                new_name = f"{base_name}_{counter}"
                counter += 1
            
            object_attr = DiscreteVariable(new_name, values=str_values)
            #
            mapped_vals = np.full_like(object_vals, np.nan)
            for idx, val in enumerate(unique_vals):
                mapped_vals[object_vals == val] = idx
            
            new_domain = Domain(
                list(newdata.domain.attributes),
                newdata.domain.class_vars,
                list(newdata.domain.metas) + [object_attr]
            )
            
            new_X = newdata.X 
            
            
            if newdata.metas is not None and newdata.metas.shape[1] > 0:
                new_metas = np.hstack([newdata.metas, mapped_vals.reshape(-1, 1)])
            else:
                new_metas = mapped_vals.reshape(-1, 1)
                
            
            newdata = Table.from_numpy(new_domain, X=new_X, Y=newdata.Y, metas=new_metas)
            '''
            new_domain = Domain(
                list(newdata.domain.attributes) + [object_attr],
                newdata.domain.class_vars,
                newdata.domain.metas,
            )
            
            new_X = np.hstack([newdata.X, mapped_vals.reshape(-1, 1)])
            newdata = Table.from_numpy(new_domain, X=new_X, Y=newdata.Y, metas=newdata.metas)
            '''
        return newdata

    def apply_spectral_watershed(self, image, spectral_gradient, mask=None):
        valid_mask = ~np.isnan(image)
        if not np.any(valid_mask):
            return image

        temp_image = np.nan_to_num(image, nan=0.0)
        mask_bool = temp_image > 0

        if not np.any(mask_bool):
            return image

        # Spatial distance is used solely to find the markers
        distance = distance_transform_edt(mask_bool)
        coords = peak_local_max(distance, min_distance=self.min_distance, labels=mask_bool)
        
        if len(coords) == 0:
            labeled_image = label(mask_bool)
        else:
            mask_markers = np.zeros(distance.shape, dtype=bool)
            mask_markers[tuple(coords.T)] = True
            markers = label(mask_markers)
            
            # Watershed flooded using Spectral Gradient
            labeled_image = watershed(spectral_gradient, markers, mask=mask_bool, watershed_line = True)

        result_image = np.copy(image)
        result_image[valid_mask] = labeled_image[valid_mask]
        
        return result_image


class SpectralWatershedEditor(BaseEditorOrange):
    name = "Spectral gradient Watershed Labeling"
    qualname = "orangecontrib.snom.spectral_watershed"

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.min_distance = 10
        self.grad_sigma = 1.0

        form = QFormLayout()
        
        self.distance_edit = lineEditIntRange(self, self, "min_distance", callback=self.edited.emit)
        self.sigma_edit = lineEditFloatRange(self, self, "grad_sigma", callback=self.edited.emit)

        form.addRow("Spatial Min Distance (Markers)", self.distance_edit)
        form.addRow("Spectral Gradient Sigma", self.sigma_edit)
        
        self.controlArea.setLayout(form)

    def setParameters(self, params):
        self.min_distance = int(params.get("min_distance", 10))
        self.grad_sigma = float(params.get("grad_sigma", 1.0))

    @classmethod
    def createinstance(cls, params):
        params = dict(params)
        min_distance = int(params.get("min_distance", 10))
        grad_sigma = float(params.get("grad_sigma", 1.0))
        return SpectralWatershedProcessor(min_distance=min_distance, grad_sigma=grad_sigma)


preprocess_image_editors.register(SpectralWatershedEditor, 640)