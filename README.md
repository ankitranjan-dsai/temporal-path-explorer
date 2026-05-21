# Temporal Path Explorer

A web-based interactive tool for exploring temporal paths in time-evolving networks. Built as a **Group 9** MSc project at the **University of Liverpool** (COMP530 Software Group Project).

## About the Project

Temporal networks extend graph models by associating time with edges, supporting the study of time-dependent connectivity. This tool allows users to upload temporal network data (edges with timestamps) and interactively explore how connectivity from a selected source node evolves over time.

**Key features:**
- **Temporal BFS** — compute earliest-arrival paths between nodes under temporal ordering constraints
- **What-if analysis** — remove or delay edges/vertices and observe the impact on global reachability and latency
- **Bottleneck detection** — identify critical edges or vertices whose removal most affects network connectivity
- **Interactive visualisation** — Plotly-based network graph with a cumulative time slider

The primary dataset used during development is the [Stanford SNAP sx-mathoverflow](https://snap.stanford.edu/data/sx-mathoverflow.html) temporal interaction network (~506k edges, ~24k nodes).

## Team

| Code | Member | Primary Role | Key Module |
|------|--------|-------------|------------|
| A | Yiqing Liu | System Integration | `app.py`, `visualizer_plotly.py` |
| B | Ankit Ranjan | Data Engineering | `data_provider.py` |
| C | Xiaohan Xu | Core Algorithms | `algorithm_C.py` |
| D | Bowen Li | Simulation Dev (What-if) | `algorithm_D.py` |
| E | Zixuan Tang | Optimisation (Bottlenecks) | `algorithm_E.py` |
| F | Ce Wang | Layout Design | `visualizer_F.py` |
| G | Wenbin Zeng | Visual Interaction | *(no code submitted by integration time)* |

## Getting Started

### Prerequisites

- Python 3.10 or later

### Installation

```bash
git clone https://github.com/<your-username>/temporal-path-explorer.git
cd temporal-path-explorer
pip install -r requirements.txt
```

### Running the App

```bash
streamlit run app.py
```

The app opens in your browser. Stop the server with **Ctrl+C**.

### Using the App

1. **Load sample data** to try the built-in 20-node demo, or **upload** a CSV/JSON file
2. Your data needs three columns: source (`SRC`/`source`/`from`), target (`TGT`/`target`/`to`), and time (`Unix`/`time`/`timestamp`)
3. Navigate the four tabs: **Data**, **Explore**, **Analyze** (What-if), **Advanced** (Bottlenecks)

See [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) for detailed usage instructions.

## Project Structure

```
temporal-path-explorer/
├── app.py                     # Streamlit entry point (4 tabs)
├── data_provider.py           # Data loading & cleaning
├── data_adj.py                # DataFrame to adjacency conversion
├── algorithm_C.py             # Earliest-arrival path (temporal BFS)
├── algorithm_D.py             # Sensitivity & what-if analysis
├── algorithm_E.py             # Bottleneck scanning
├── visualizer_plotly.py       # Plotly network visualisation
├── visualizer_F.py            # Matplotlib temporal snapshots (reference)
├── demo_data.csv              # Built-in small sample (~50 edges)
├── requirements.txt           # Python dependencies
├── docs/
│   ├── ACCEPTANCE.md          # Acceptance checklist
│   ├── USER_GUIDE.md          # End-user guide
│   └── INTEGRATION_LOG.md     # Integration history
├── teammate_deliverables/     # Original teammate notebooks and scripts
│   ├── B/                     # Data cleaning notebooks
│   ├── C/                     # Earliest-path notebook
│   ├── D/                     # What-if scripts
│   ├── E/                     # Bottleneck script
│   └── F/                     # Matplotlib visualiser scripts
├── notebooks/
│   ├── data_cleaning.ipynb    # Data cleaning pipeline
│   └── exploratory_analysis.ipynb  # EDA on sx-mathoverflow
├── data/
│   └── mathoverflow_demo_42k.csv   # 42k-edge demo subset
└── reports/                   # Project documentation and reports
    ├── CA1_report.pdf
    ├── CA4_completion_report.pdf
    ├── demo_feedback.pdf
    ├── milestones_and_roles.pdf
    ├── presentation_team9.pptx
    └── ...
```

## Dataset

The full sx-mathoverflow dataset is not included in the repository due to its size. To use it:

1. Download from [Stanford SNAP](https://snap.stanford.edu/data/sx-mathoverflow.html)
2. Place `sx-mathoverflow.txt.gz` in the project root
3. Use the `data_cleaning.ipynb` notebook to process it, or upload the raw file directly through the app

A 42k-edge demo subset is provided in `data/mathoverflow_demo_42k.csv` for testing.

## Dependencies

- streamlit >= 1.34.0
- pandas >= 2.1.0
- networkx >= 3.1
- plotly >= 5.18.0
- matplotlib >= 3.8.0

## License

This project was developed as part of an academic group project and is intended for educational purposes.
