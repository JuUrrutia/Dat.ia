from typing import Dict, Any, List

class EChartsFormatter:
    """
    Builds backend ECharts option dictionaries for query response DTOs.
    """

    @classmethod
    def build_chart_option(
        cls,
        chart_type: str,
        x_labels: List[str],
        y_values: List[float],
        series_name: str = "Valor"
    ) -> Dict[str, Any]:
        if chart_type == "none" or not y_values:
            return {"series": []}

        if chart_type in ("pie", "donut"):
            return {
                "tooltip": {"trigger": "item"},
                "series": [{
                    "name": series_name,
                    "type": "pie",
                    "radius": ["40%", "70%"] if chart_type == "donut" else "65%",
                    "data": [{"name": x_labels[i], "value": y_values[i]} for i in range(min(len(x_labels), len(y_values)))]
                }]
            }

        return {
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": x_labels},
            "yAxis": {"type": "value"},
            "series": [{
                "name": series_name,
                "type": "bar" if chart_type == "bar" else "line",
                "data": y_values
            }]
        }
