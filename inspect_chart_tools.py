from vanna.tools import VisualizeDataTool, PlotlyChartGenerator
import inspect

def inspect_tools():
    print("Inspecting PlotlyChartGenerator...")
    for name, method in inspect.getmembers(PlotlyChartGenerator):
        if not name.startswith('_'):
            print(f"  {name}")
            
    print("\nInspecting VisualizeDataTool...")
    for name, method in inspect.getmembers(VisualizeDataTool):
        if not name.startswith('_'):
            print(f"  {name}")
            
    print("\nInit signatures:")
    print(f"PlotlyChartGenerator: {inspect.signature(PlotlyChartGenerator.__init__)}")
    print(f"PlotlyChartGenerator.generate_chart: {inspect.signature(PlotlyChartGenerator.generate_chart)}")
    print(f"VisualizeDataTool: {inspect.signature(VisualizeDataTool.__init__)}")

if __name__ == "__main__":
    inspect_tools()
