from orangewidget import gui
from orangewidget.settings import Setting
from Orange.data import Table
from Orange.widgets import gui
from Orange.widgets.settings import Setting
from Orange.widgets.widget import OWWidget, Input, Output

class OWRowSelector(OWWidget):
    name = "Row Selector"
    description = "Selects rows based on indexes (es. 1, 3, 5-10)."
    priority = 50
    want_main_area = False
    class Inputs:
        data = Input("Data", Table)

    class Outputs:
        selected_data = Output("Selected Data", Table)

    # Default setting
    indices_str = Setting("")
    invert_selection = Setting(False)  # Invert mode so that the indices selected are excluded instead

    def __init__(self):
        super().__init__()
        self.data = None

        box = gui.widgetBox(self.controlArea, "Selection Settings")
        
        gui.widgetLabel(box, "Insert indices (es. 1, 3, 5-10):")
        
        
        self.line_edit = gui.lineEdit(
            box, self, "indices_str",
            callback=self.commit
        )
        
        
        self.cb_invert = gui.checkBox(
            box, self, "invert_selection", 
            "Exclude selected indices",
            callback=self.commit  
        )
        
        gui.button(box, self, "Apply", callback=self.commit)
        gui.rubber(self.controlArea)

    @Inputs.data
    def set_data(self, data):
        self.data = data
        self.commit()

    def commit(self):
        if self.data is None:
            self.Outputs.selected_data.send(None)
            return

        
        parsed_indices = self.parse_indices(self.indices_str, len(self.data))

        if not parsed_indices:
            # If the there are no selected indeces and inverted mode is active, then it gives back all data
            # Otherwise it gives none back
            if self.invert_selection:
                self.Outputs.selected_data.send(self.data)
            else:
                self.Outputs.selected_data.send(None)
            return

        #Main function
        if self.invert_selection:
            # It calculates all indices and keeps the selected ones
            all_indices = set(range(len(self.data)))
            keep_indices = sorted(list(all_indices - set(parsed_indices)))
            
            if not keep_indices:
                self.Outputs.selected_data.send(None)
            else:
                selected = self.data[keep_indices]
                self.Outputs.selected_data.send(selected)
        else:
            selected = self.data[parsed_indices]
            self.Outputs.selected_data.send(selected)

    def parse_indices(self, text, max_len): #This function transforms the text in a logic that the software can understand.
        """Converts '1, 3, 5-7' in a list of python indeces"""
        if not text.strip():
            return []
        indices = set()
        parts = text.split(',') #It splits each part of the string using "," as a separator
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
                
            if '-' in part: #If part of the string has "-"...
                try:
                    start_str, end_str = part.split('-', 1) #...it takes the numbers between "-"...
                    start = int(start_str)
                    end = int(end_str)
                    indices.update(range(max(0, start - 1), min(max_len, end))) #...and uses them to generate an interval which are added in the indeces list
                except ValueError:
                    pass
            else:
                try: #The parts between "-" are trasnformed into integers and added to the list directly
                    val = int(part)
                    if 1 <= val <= max_len:
                        indices.add(val - 1)
                except ValueError:
                    pass
                    
        return sorted(list(indices))
