from AnyQt.QtWidgets import QFormLayout

from orangecontrib.spectroscopy.widgets.preprocessors.utils import BaseEditorOrange
from orangecontrib.spectroscopy.widgets.gui import lineEditIntRange
from orangewidget.gui import comboBox


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


class InstanceLabelingProcessor(PreprocessImageOpts2DOnlyWhole):
    def __init__(self, method="connected_components", min_distance=10):
        self.method = method
        self.min_distance = int(min_distance)

    def __call__(self, data, image_opts, run_all=False):
        if run_all or len(data.domain.attributes) == 0:
            attrs_to_run = [v.name for v in data.domain.attributes]
            newdata = data.copy()
        else:
            attrs_to_run = [image_opts["attr_value"]]
            newdata = _prepare_table_for_image(data, image_opts)

        mask = get_mask_from_image_opts(data, image_opts)
        image_opts = image_opts.copy()

        new_vals = np.full_like(newdata.X, np.nan)
        object_vals = None

        for i, attr in enumerate(attrs_to_run):
            image_opts["attr_value"] = attr
            temp = _prepare_table_for_image(newdata, image_opts)
            image, indices = _image_from_table(temp, image_opts)
            transformed = self.transform_image(image, newdata, mask=mask)
            new_vals[:, i] = transformed[indices].reshape(-1)
            if object_vals is None:
                object_vals = transformed[indices].reshape(-1)

        with newdata.unlocked(newdata.X):
            newdata.X = new_vals

        if object_vals is not None:
            unique_vals = np.unique(object_vals[~np.isnan(object_vals)])
            str_values = [str(int(v)) for v in unique_vals]

            object_attr = DiscreteVariable("object", values=str_values)
            # This is to make sure that if labelling is applied more than once, it will enumarate them in order
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
            for i, val in enumerate(unique_vals):
                mapped_vals[object_vals == val] = i
                
            # Construct the new domain
            new_domain = Domain(
                list(newdata.domain.attributes),
                newdata.domain.class_vars,
                list(newdata.domain.metas) + [object_attr] # Aggiungiamo ai metas
                )
                        
            new_X = newdata.X 
                        
                        
            if newdata.metas is not None and newdata.metas.shape[1] > 0:
                new_metas = np.hstack([newdata.metas, mapped_vals.reshape(-1, 1)])
            else:
                new_metas = mapped_vals.reshape(-1, 1)
                            
                        
            newdata = Table.from_numpy(new_domain, X=new_X, Y=newdata.Y, metas=new_metas)

        return newdata


    def transform_image(self, image, data, mask=None):
        valid_mask = ~np.isnan(image)
        if not np.any(valid_mask):
            return image
        
        temp_image = np.nan_to_num(image, nan=0.0)
        mask_bool = temp_image > 0

        if not np.any(mask_bool):
            return image
        #Method
        if self.method == "connected_components":
            # It simply lables the connected components. More suited for cases where objects are already well separated
            labeled_image = label(mask_bool)
            
        elif self.method == "watershed":
            # More suited where objects are attached but beware: It might separate incorrectly for certain shapes such as hourglasses
            # Calculates the SHORTEST distance between an element in the foreground (1) and the background (0)
            distance = distance_transform_edt(mask_bool)
            # Finds local maxima in the image
            # min_distance is necessary to avoid calculating different local maxima for the same cell
            coords = peak_local_max(distance, min_distance=self.min_distance, labels=mask_bool)
            
            if len(coords) == 0:
                labeled_image = label(mask_bool) # Fallsback on simple labelling if the algorithm fails
            else:
                # Markers are necessary for watershed. In this case we use the local maxima that we found before
                mask_markers = np.zeros(distance.shape, dtype=bool)
                mask_markers[tuple(coords.T)] = True
                markers = label(mask_markers)
                
                # -distance is necessary because it starts filling from the pixels which are the nearest to background.
                labeled_image = watershed(-distance, markers, mask=mask_bool, watershed_line=True)
        else:
            labeled_image = temp_image

        # Final image
        result_image = np.copy(image)
        result_image[valid_mask] = labeled_image[valid_mask]
        
        return result_image


class InstanceLabelingEditor(BaseEditorOrange):
    name = "Instance Labeling"
    qualname = "orangecontrib.snom.instance_labeling"

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.method = "connected_components"
        self.min_distance = 10

        form = QFormLayout()
        
        # Menu 
        self.cb_method = comboBox(self, self, "method", callback=self.update_ui)
        self.cb_method.addItems(['connected_components', 'watershed'])
        self.cb_method.setCurrentText('connected_components')

        # Watershed parameters
        self.distance_edit = lineEditIntRange(self, self, "min_distance", callback=self.edited.emit)

        form.addRow("Method", self.cb_method)
        form.addRow("Min Distance (Watershed)", self.distance_edit)
        
        self.controlArea.setLayout(form)
        self.update_ui()

    def update_ui(self):
        metodo = self.cb_method.currentText()
        
        self.distance_edit.setEnabled(metodo == "watershed")
        
        self.method = metodo
        self.edited.emit()

    def setParameters(self, params):
        self.method = params.get("method", "connected_components")
        self.min_distance = int(params.get("min_distance", 10))
        self.update_ui()

    @classmethod
    def createinstance(cls, params):
        params = dict(params)
        method = str(params.get("method", "connected_components"))
        min_distance = int(params.get("min_distance", 10))
        
        return InstanceLabelingProcessor(method=method, min_distance=min_distance)

preprocess_image_editors.register(InstanceLabelingEditor, 630)
