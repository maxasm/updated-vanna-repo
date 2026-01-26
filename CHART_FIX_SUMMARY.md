# Chart Generation Fix Summary

## Problem
When the VisualizeDataTool runs and the response text mentions "Created visualization from 'query_results_xxxx.csv'", the final JSON response had:
- `"chart": null`
- `"chart_generated": false`
- `"chart_source": null`

## Root Causes Identified

1. **Missing "Created visualization" detection**: The code didn't check for "Created visualization" in response_text to trigger chart generation from CSV files.

2. **Incomplete chart extraction logic**: The `_extract_chart_from_component()` method wasn't looking in all possible locations for chart data in Vanna 2.x components.

3. **No fallback chart generation**: When the VisualizeDataTool ran but chart extraction failed, there was no fallback to generate charts from the CSV file.

## Solutions Implemented

### 1. Added "Created visualization" detection and fallback chart generation
In `EnhancedChatHandler.handle_chat_request()`:
```python
# Check if visualization was created but chart wasn't extracted
# This happens when VisualizeDataTool runs but chart extraction fails
if "Created visualization" in response_text and csv_path and chart_json is None:
    logger.info(f"Detected 'Created visualization' in response but no chart extracted. CSV path: {csv_path}")
    try:
        # Try to load the CSV and generate chart
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            if not df.empty:
                logger.info(f"Loaded CSV for chart generation: {csv_path}, shape: {df.shape}")
                chart_dict = self.chart_generator.generate_chart(df=df)
                if chart_dict:
                    chart_json = chart_dict
                    chart_source = "forced_after_visualize_tool"
                    logger.info(f"Generated chart from CSV after visualization tool call")
```

### 2. Enhanced chart extraction logic
Improved `_extract_chart_from_component()` method to:
- Add comprehensive logging for debugging
- Check for `plotly_figure` key in metadata (in addition to `chart`)
- Check more component attributes: `plotly_chart`, `chart`, `figure`, `plotly_figure`, `plotly`
- Handle case where component itself is a dict with chart data
- Check if component has chart data directly

### 3. Added better logging
Added debug and info logs throughout the chart extraction and generation process to help diagnose issues.

## Key Changes Made

1. **Line ~807**: Added the "Created visualization" detection logic
2. **Enhanced `_extract_chart_from_component()`**: Added more comprehensive checks and logging
3. **Chart source tracking**: Properly sets `chart_source` to `"forced_after_visualize_tool"` when chart is generated from CSV after visualization tool call

## Testing

Created `test_chart_fix.py` to verify:
1. Chart extraction from various component structures
2. Detection of "Created visualization" in response text
3. Fallback chart generation from CSV files

All tests pass successfully.

## Expected Behavior After Fix

1. When VisualizeDataTool runs successfully:
   - Chart data is extracted from components if available
   - If extraction fails but "Created visualization" is in response text:
     - CSV file is loaded
     - Chart is generated using `PlotlyChartGenerator`
     - `chart_source` is set to `"forced_after_visualize_tool"`

2. Response JSON will now have:
   - `"chart": {plotly_chart_data}` (not null)
   - `"chart_generated": true`
   - `"chart_source": "vanna_ai_tool"` or `"forced_after_visualize_tool"` or `"auto_generated"`

3. Charts are saved via `ChartManager.save_chart_data()` with proper IDs and URLs.

## Files Modified
- `api.py`: Main implementation fixes
- `test_chart_fix.py`: Test script to verify fixes
- `CHART_FIX_SUMMARY.md`: This documentation