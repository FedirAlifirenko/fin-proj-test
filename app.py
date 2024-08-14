import logging
from pathlib import Path
from typing import Any

import gradio as gr
import pandas as pd

logger = logging.getLogger(__name__)


def main_flow(df: pd.DataFrame) -> dict[str, Any]:
    sections_data = identify_key_sections(df)
    growth_rates = calculate_growth_rates(sections_data)

    static_keys = [key for key, values in growth_rates.items() if 0.0 in values]
    avg_growth_rates = {
        key: round(sum(values) / len(values), 2)
        for key, values in growth_rates.items()
        if key not in static_keys
    }

    initial_values = {key: values[0] for key, values in sections_data.items()}

    return {
        "static_keys": static_keys,
        "avg_growth_rates": avg_growth_rates,
        "initial_values": initial_values,
    }


def identify_key_sections(df) -> dict[str, list[Any]]:
    sections = {}
    sections["Product Sales"] = df.iloc[2, 1:14].values
    sections["Service Sales"] = df.iloc[3, 1:14].values
    sections["Cost of Goods Sold"] = df.iloc[6, 1:14].values
    sections["Marketing"] = df.iloc[7, 1:14].values
    sections["Staff Salaries"] = df.iloc[8, 1:14].values
    return sections


def calculate_growth_rates(section_data) -> dict[str, list[float]]:
    growth_rates = {}
    for key, values in section_data.items():
        growth_rates[key] = [
            round((values[i] - values[i - 1]) / values[i - 1], 2)
            for i in range(1, len(values))
        ]
    return growth_rates


def secondary_flow(assumptions_data: dict[str, Any], original_df: pd.DataFrame) -> None:

    def build_new_df(
        periods: int, product_sales_rate: int, service_sales_rate: int
    ) -> pd.DataFrame:
        static_keys = assumptions_data["static_keys"]

        avg_growth_rates = assumptions_data["avg_growth_rates"]
        avg_growth_rates["Product Sales"] = product_sales_rate / 100
        avg_growth_rates["Service Sales"] = service_sales_rate / 100

        initial_values = assumptions_data["initial_values"]

        new_table_data = {}
        for key, initial_value in initial_values.items():
            if key in static_keys:
                new_table_data[key] = [initial_value] * (periods + 1)
                continue

            new_table_data[key] = [
                round(initial_value * (1 + avg_growth_rates[key]) ** period, 2)
                for period in range(periods + 1)
            ]

        new_table_df = pd.DataFrame(new_table_data)

        new_table_df = new_table_df.transpose()
        new_table_df.columns = ["Initial"] + [
            f"Month {i}" for i in range(1, periods + 1)
        ]

        new_table_df.loc["Total Sales"] = (
            new_table_df.loc["Product Sales"] + new_table_df.loc["Service Sales"]
        )
        new_table_df.loc["Total Operating Expenses"] = (
            new_table_df.loc["Cost of Goods Sold"]
            + new_table_df.loc["Marketing"]
            + new_table_df.loc["Staff Salaries"]
        )
        new_table_df.loc["Net Income"] = (
            new_table_df.loc["Total Sales"]
            - new_table_df.loc["Total Operating Expenses"]
        )

        new_table_df = new_table_df.reindex(
            [
                "Product Sales",
                "Service Sales",
                "Total Sales",
                "Cost of Goods Sold",
                "Marketing",
                "Staff Salaries",
                "Total Operating Expenses",
                "Net Income",
            ]
        )
        new_table_df.insert(0, "Category", new_table_df.index)
        return new_table_df

    with gr.Blocks() as demo:
        with gr.Tabs():
            with gr.Tab("Original table"):
                gr.DataFrame(original_df, label="Financial Projections (Assignment)")

                gr.Json(assumptions_data, label="Assumptions Data")

            with gr.Tab("New projections"):
                gr.Interface(
                    build_new_df,
                    [
                        gr.Number(3, label="Number of periods (months)"),
                        gr.Slider(0, 100, 4, 1, label="Product Sales Growth Rate (%)"),
                        gr.Slider(0, 100, 5, 1, label="Service Sales Growth Rate (%)"),
                    ],
                    gr.DataFrame(),
                    live=True,
                )

    demo.launch()


def main() -> None:
    fp = Path("projections.xlsx").resolve()
    df = pd.read_excel(fp)
    assumptions_data = main_flow(df)
    logger.info(f"{assumptions_data=}")

    secondary_flow(assumptions_data, df)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
    main()
