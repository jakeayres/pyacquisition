import dearpygui.dearpygui as dpg
from ..constants import TEXT_COLOR, EMPHASIS_COLOR, SECONDARY_COLOR, WHITE


class FileWindow:
    
    
    def __init__(self):
        
        self.file_uuid = dpg.generate_uuid()
        self.directory_uuid = dpg.generate_uuid()
        
        with dpg.window(
            label="Current File", 
            width=300, 
            height=100,
            pos=[20, 40],
            no_close=True, 
            no_collapse=True, 
            no_background=True, 
            no_resize=True, 
            no_move=True, 
            no_bring_to_front_on_focus=True, 
            no_focus_on_appearing=True
        ):
            with dpg.group(horizontal=True):
                dpg.add_text("File:          ", color=SECONDARY_COLOR)
                dpg.add_text("", tag=self.file_uuid, color=WHITE)
                
            with dpg.group(horizontal=True):
                dpg.add_text("Directory:     ", color=SECONDARY_COLOR)
                dpg.add_text("", tag=self.directory_uuid, color=WHITE)
                
    
    def update_file(self, file_path: str) -> None:
        """
        Update the file path in the GUI.
        
        Args:
            file_path (str): The path of the current datafile.
        """
        dpg.set_value(self.file_uuid, file_path)
        
        
    def update_directory(self, directory_path: str) -> None:
        """
        Update the directory path in the GUI.
        
        Args:
            directory_path (str): The path of the current directory.
        """
        dpg.set_value(self.directory_uuid, directory_path)