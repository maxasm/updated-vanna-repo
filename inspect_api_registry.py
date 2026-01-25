from api import registry

def inspect_registry():
    print("Inspecting Tool Registry...")
    tools = registry._tools
    print(f"Registered tools: {len(tools)}")
    for name, tool_wrapper in tools.items():
        print(f" - {name}")
        # print(dir(tool_wrapper))
        
    if "visualize_data" in tools:
        print("SUCCESS: visualize_data tool found.")
    else:
        print("FAILURE: visualize_data tool NOT found.")

if __name__ == "__main__":
    inspect_registry()
