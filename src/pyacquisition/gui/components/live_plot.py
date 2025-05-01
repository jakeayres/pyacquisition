import dearpygui.dearpygui as dpg
from ...core.consumer import Consumer
from ...core.logging import logger
import time
import asyncio



class LivePlotWidget(Consumer):
    
    
    def __init__(self, data: dict[str, list]):
        super().__init__()
        
        self.window_tag = dpg.generate_uuid()
        self.plot_tag = dpg.generate_uuid()
        self.x_axis_tag = dpg.generate_uuid()
        self.y_axis_tag = dpg.generate_uuid()
        self.data = data.copy()
        self.x_key = next(iter(self.data.keys()))
        self.series_tags = {}
        
        with dpg.window(
            label="Live Plot",
            pos=[20, 40],
            width=800,
            height=600,
            tag=self.window_tag,
        ):
            with dpg.menu_bar():
                dpg.add_menu_item(label="Clear", callback=self.clear_data)
                with dpg.menu(label="x-axis"):
                    for key in self.data.keys():
                        dpg.add_menu_item(label=key, callback=lambda s, a, u: self.set_x_key(s, a, u), user_data=key)
                
            
            with dpg.plot(label="Live Data Plot", tag=self.plot_tag, height=-1, width=-1):
                dpg.add_plot_legend()
                dpg.add_plot_axis(dpg.mvXAxis, label=self.x_key, tag=self.x_axis_tag)
                dpg.add_plot_axis(dpg.mvYAxis, label="Value", tag=self.y_axis_tag)

        self.build_series()
        
        
    def clear_data(self):
        """
        Clear the data in the plot.
        """
        for key in self.data.keys():
            self.data[key] = []
        
        
    def set_on_close(self, callback: callable):
        """
        Set the callback for when the window is closed.
        """
        dpg.configure_item(self.window_tag, on_close=callback)
        
        
    def set_x_key(self, sender, app_data, user_data):
        """
        Set the x-axis key for the plot.
        """
        if user_data in self.data:
            self.x_key = user_data
            dpg.configure_item(self.x_axis_tag, label=user_data)
        else:
            logger.error(f"Key {user_data} not found in data.")
        
    
    def build_series(self):
        """
        Build the series for the plot.
        """
        for key in self.data.keys():
            series_tag = dpg.generate_uuid()
            dpg.add_scatter_series(
                x=self.data[self.x_key],
                y=self.data[key],
                label=key,
                tag=series_tag,
                parent=self.y_axis_tag,
            )
            self.series_tags[key] = series_tag

    
    def update_data(self, data: dict):
        """
        Update the plot with new data.
        """
        for key, value in data.items():
            if key in self.data:
                self.data[key].append(value)
                
                
    def update_series(self):
        """
        Update the series in the plot.
        """
        for key in self.data:
            dpg.set_value(self.series_tags[key], [self.data[self.x_key], self.data[key]])
            
            
    def update(self, data: dict):
        """
        Update the plot with new data.
        """
        self.update_data(data)
        self.update_series()
    