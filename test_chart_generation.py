import sys
import os
import pandas as pd
import json
from vanna.integrations.openai import OpenAILlmService
from vanna.integrations.chromadb import ChromaAgentMemory
from vanna import Agent, AgentConfig
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_chart_generation():
    print("Testing Chart Generation...")
    
    # Mock data
    data = {
        'Product': ['A', 'B', 'C', 'D', 'E'],
        'Sales': [100, 150, 80, 200, 120]
    }
    df = pd.DataFrame(data)
    print(f"Dataframe:\n{df}")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found")
        return

    
    from vanna.tools import PlotlyChartGenerator
    
    # 1. Test Chart Generation
    print("\nGenerating Chart using PlotlyChartGenerator...")
    try:
        generator = PlotlyChartGenerator()
        chart_dict = generator.generate_chart(df, title="Sales by Product")
        
        if chart_dict:
            print("Chart generated successfully")
            json_str = json.dumps(chart_dict)
            print(f"JSON length: {len(json_str)}")
            print(f"Keys: {chart_dict.keys()}")
            print("Test PASSED")
        else:
            print("Failed to generate chart")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_chart_generation()
