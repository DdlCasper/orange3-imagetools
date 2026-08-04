
import numpy as np
from AnyQt.QtWidgets import QListWidget, QListWidgetItem, QComboBox, QLabel
from AnyQt.QtCore import Qt

from Orange.widgets import gui
from Orange.widgets.settings import Setting
from Orange.widgets.widget import OWWidget, Input, Output
from Orange.data import Table, Domain, ContinuousVariable
from Orange.widgets.utils.itemmodels import VariableListModel
from skimage.measure import regionprops_table

class OWRegionPropsExtractor(OWWidget):
    name = "Morphological features"
    description = "Extract quantitative morphological features from a labelled image using skimage.measure.regionprops."
    priority = 100

    class Inputs:
        labeled_image = Input("Labeled Image", Table)
        intensity_image = Input("Intensity Image", Table)

    class Outputs:
        properties = Output("Properties", Table)

    # Default parameters. If pylance signals issues with the arguments of Setting(), they are just false alarms
    use_intensity = Setting(False)
    selected_intensity_attr = Setting("")
    selected_label_attr = Setting("")
    enable_caching = Setting(True)
    enable_offset = Setting(False)
    spacing_x = Setting(1.0)
    spacing_y = Setting(1.0)
    
    # Default properties
    selected_properties = Setting(['label', 'area', 'centroid'])

    # Image properties from skimage regionprops (If you want to add more feature, check the list here: https://scikit-image.org/docs/0.25.x/api/skimage.measure.html#skimage.measure.regionprops)
    AVAILABLE_PROPS = [
        'label', 'area', 'bbox', 'bbox_area', 'centroid', 'convex_area',
        'eccentricity', 'equivalent_diameter', 'euler_number', 'extent', 
        'filled_area', 'inertia_tensor', 'inertia_tensor_eigvals', 
        'intensity_max', 'intensity_mean', 'intensity_min', 'local_centroid', 
        'major_axis_length', 'minor_axis_length', 'moments', 'moments_central', 
        'moments_hu', 'moments_normalized', 'orientation', 'perimeter', 'solidity'
    ]

    def __init__(self):
        super().__init__()
        
        self.labeled_data = None
        self.intensity_data = None
        
        # ItemModels specifically built to handle Orange Variable icons
        self.label_model = VariableListModel()
        self.intensity_model = VariableListModel()
        
        self._build_gui()

    def _build_gui(self):
        # LEFT PANEL (Control Area)
        box_inputs = gui.widgetBox(self.controlArea, "Input Settings")

        # Label Combobox (Powered by VariableListModel)
        box_inputs.layout().addWidget(QLabel("Label Attribute:"))
        self.combo_label = QComboBox()
        self.combo_label.setModel(self.label_model) #To show which type of variable the label is
        self.combo_label.currentIndexChanged.connect(self._on_label_changed)
        box_inputs.layout().addWidget(self.combo_label)
        #This is the check box to choose weather to use intensity or not. This is important because some properties require intensity.
        self.cb_intensity = gui.checkBox(
            box_inputs, self, "use_intensity", "Use Intensity Image", 
            callback=self._update_ui
        )
        
        # Intensity Combobox
        box_inputs.layout().addWidget(QLabel("Intensity Attribute:"))
        self.combo_intensity = QComboBox()
        self.combo_intensity.setModel(self.intensity_model) #To show which type of variable the intensity is
        self.combo_intensity.currentIndexChanged.connect(self._on_intensity_changed)
        box_inputs.layout().addWidget(self.combo_intensity)
        
        gui.separator(box_inputs)
        
        box_params = gui.widgetBox(self.controlArea, "Function settings")
        gui.checkBox(box_params, self, "enable_caching", "Enable Caching", callback=self.commit)
        gui.separator(box_params)
        gui.doubleSpin(box_params, self, "spacing_x", 0.001, 9999.0, 0.1, label="Spacing X:", callback=self.commit)
        gui.doubleSpin(box_params, self, "spacing_y", 0.001, 9999.0, 0.1, label="Spacing Y:", callback=self.commit)
        gui.rubber(self.controlArea)
        # ==========================================
        # RIGHT PANEL (Main Area) - Checkbox Tabelle
        # ==========================================
        box_props = gui.widgetBox(self.mainArea, "Properties to Extract")

        #It scans all the properties in the list defined in line 38 to see which ones are selected and which ones are not
        self.props_list = QListWidget()
        for prop in self.AVAILABLE_PROPS:
            item = QListWidgetItem(prop)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            
            if prop in self.selected_properties:#If the property got selected, it sets the property to "checked", otherwise it's unchecked
                item.setCheckState(Qt.Checked) 
            else:
                item.setCheckState(Qt.Unchecked) 

            self.props_list.addItem(item)
      
        self.props_list.itemChanged.connect(self._on_props_changed)
        box_props.layout().addWidget(self.props_list)
        
        self._update_ui()

    def _update_ui(self):
        self.combo_intensity.setEnabled(self.use_intensity)
        self.commit()

    def _on_label_changed(self):
        # Update setting based on combobox interaction
        idx = self.combo_label.currentIndex()
        if idx >= 0:
            self.selected_label_attr = self.label_model[idx].name
        else:
            self.selected_label_attr = ""
        self.commit()

    def _on_intensity_changed(self):
        # Update setting based on combobox interaction
        idx = self.combo_intensity.currentIndex()
        if idx >= 0:
            self.selected_intensity_attr = self.intensity_model[idx].name
        else:
            self.selected_intensity_attr = ""
        self.commit()

    def _on_props_changed(self, item):
        prop = item.text()
        if item.checkState() == Qt.Checked:
            if prop not in self.selected_properties:
                self.selected_properties.append(prop)
        else:
            if prop in self.selected_properties:
                self.selected_properties.remove(prop)
        self.commit()

    # ==========================================
    #  INPUT HANDLER
    # ==========================================
    @Inputs.labeled_image
    def set_labeled_image(self, data):
        self.labeled_data = data
        valid_vars = []
        
        if self.labeled_data is not None:
            for var in self.labeled_data.domain.variables + self.labeled_data.domain.metas:
                if var.name not in ["map_x", "map_y"]:
                    valid_vars.append(var)
                    
        # Setting the model resets the combobox safely and prevents data overlap
        self.label_model[:] = valid_vars
        
        if valid_vars:
            names = [var.name for var in valid_vars]
            if self.selected_label_attr in names:
                self.combo_label.setCurrentIndex(names.index(self.selected_label_attr))
            else:
                self.combo_label.setCurrentIndex(0)
                self.selected_label_attr = valid_vars[0].name
        else:
            self.selected_label_attr = ""

        self.commit()

    @Inputs.intensity_image
    def set_intensity_image(self, data):
        self.intensity_data = data
        valid_vars = []
        
        if self.intensity_data is not None:
            for var in self.intensity_data.domain.variables + self.intensity_data.domain.metas:
                if var.is_continuous and var.name not in ["map_x", "map_y"]:
                    valid_vars.append(var)
                    
        self.intensity_model[:] = valid_vars
        
        if valid_vars:
            names = [var.name for var in valid_vars]
            if self.selected_intensity_attr in names:
                self.combo_intensity.setCurrentIndex(names.index(self.selected_intensity_attr))
            else:
                self.combo_intensity.setCurrentIndex(0)
                self.selected_intensity_attr = valid_vars[0].name
        else:
            self.selected_intensity_attr = ""
            
        self.commit()

    #UTILITY FUNCTIONS 

    def _table_to_2d_array(self, table, target_var_name, fill_value=0, is_integer=False):
        """We need to convert the table in a 2D numpy array"""
        if not target_var_name:
            return None
            
        try:
            x_var = table.domain["map_x"]
            y_var = table.domain["map_y"]
        except KeyError:
            self.error("Meta variables named map_x and map_y not found. If present, rename them as such")
            return None

        # Looks for target variable
        target_var = None
        for var in table.domain.variables + table.domain.metas:
            if var.name == target_var_name:
                target_var = var
                break
                
        if target_var is None:
            self.error(f"Target Variable '{target_var_name}' not found.")
            return None

        x_data = table.get_column_view(x_var)[0].astype(int)
        y_data = table.get_column_view(y_var)[0].astype(int)
        val_data = table.get_column_view(target_var)[0]
        
        max_x, max_y = np.max(x_data), np.max(y_data)
        
        dtype = int if is_integer else float
        img = np.full((max_y + 1, max_x + 1), fill_value, dtype=dtype)
        img[y_data, x_data] = val_data
        
        return img

    #MAIN FUNCTION 

    def commit(self):
        self.clear_messages()
        
        if self.labeled_data is None:
            self.Outputs.properties.send(None)
            return

        # Build labled image
        lbl_img = self._table_to_2d_array(self.labeled_data, self.selected_label_attr, fill_value=0, is_integer=True)
        if lbl_img is None:
            self.Outputs.properties.send(None)
            return

        # Builds intensity image if available
        intensity_img = None
        if self.use_intensity and self.intensity_data is not None and self.selected_intensity_attr:
            intensity_img = self._table_to_2d_array(self.intensity_data, self.selected_intensity_attr, fill_value=0.0)

        # Filters properties in case intensity image was not provided to avoid crash
        props_to_calc = []
        for p in self.selected_properties:
            if "intensity" in p and intensity_img is None:
                continue
            props_to_calc.append(p)
            
        if not props_to_calc: #If there are no properties selected, return None
            self.Outputs.properties.send(None)
            return

        # Prepeares arguments for sci-kit image
        kwargs = {'cache': self.enable_caching}
        
        # Scikit-image interprets spacing as(row_spacing, col_spacing) = (y, x)
        kwargs['spacing'] = (self.spacing_y, self.spacing_x)

        # Applies regionprops_table
        try:
            res_dict = regionprops_table(
                lbl_img, 
                intensity_image=intensity_img, 
                properties=props_to_calc, 
                **kwargs
            )
        except Exception as e:
            self.error(f"Error during execution of region_props: {str(e)}")
            self.Outputs.properties.send(None)
            return

        domain_vars = []
        columns = []
        
        for key, val in res_dict.items():
            # regionprops_table flattens features that are arrays (es. centroid-0, centroid-1)
            domain_vars.append(ContinuousVariable(key))
            columns.append(val)

        if not domain_vars: 
            self.Outputs.properties.send(None)
            return

        # Create Table
        X_data = np.column_stack(columns)
        domain = Domain(domain_vars)
        out_table = Table(domain, X_data)
        
        # Output
        self.Outputs.properties.send(out_table)