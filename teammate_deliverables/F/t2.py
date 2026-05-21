import streamlit as st
import pandas as pd
import networkx as nx
import json
import matplotlib.pyplot as plt



# Data Provider


def load_json_data(uploaded_file):
    """
    提取 u , v , t  参数

    """
    try:
        data = json.load(uploaded_file)
        df = pd.DataFrame(data)
        # 统一列名映射
        if 'u' in df.columns and 'v' in df.columns and 't' in df.columns:
            return df[['u', 'v', 't']]
        else:
            st.error("Error")
            return None
    except Exception as e:
        st.error(f"Error: {e}")
        return None



# Visualizer


class TemporalVisualizer:
    def __init__(self, df):
        self.df = df
        # static layout
        self.G = nx.DiGraph()
        for _, row in df.iterrows():
            self.G.add_edge(row['u'], row['v'])

        self.pos = self.compute_static_layout()

    def compute_static_layout(self):
        """
        compute_static_layout
        """

        return nx.spring_layout(self.G, seed=42)

    def render_snapshot_frame(self, current_time=None):
        """
        render_snapshot_frame
        如果 current_time 为 None，则显示全量静态图
        """
        fig, ax = plt.subplots(figsize=(10, 7))

        # t <= current_time
        if current_time is not None:
            display_df = self.df[self.df['t'] <= current_time]
            edges = list(zip(display_df['u'], display_df['v']))
            active_nodes = set(display_df['u']).union(set(display_df['v']))
        else:
            edges = list(self.G.edges())
            active_nodes = list(self.G.nodes())


        nx.draw_networkx_nodes(self.G, self.pos, nodelist=active_nodes,
                               node_color='skyblue', node_size=500, ax=ax)
        nx.draw_networkx_labels(self.G, self.pos, font_size=10, ax=ax)


        nx.draw_networkx_edges(self.G, self.pos, edgelist=edges,
                               edge_color='gray', arrows=True, ax=ax)


        title = "Full Static Network" if current_time is None else f"Temporal Snapshot at t={current_time}"
        ax.set_title(title)
        return fig



# Interface


def main():
    st.title("Temporal Path Explorer & Visualizer")
    st.sidebar.header("Data Upload")


    uploaded_file = st.sidebar.file_uploader("Upload Temporal JSON", type=['json'])

    if uploaded_file is not None:
        df = load_json_data(uploaded_file)

        if df is not None:
            st.success("Data Loaded Successfully!")


            with st.expander("View Raw Data"):
                st.write(df)

            visualizer = TemporalVisualizer(df)


            mode = st.radio("Display Mode", ["Full Static Graph", "Single Snapshot"])

            if mode == "Full Static Graph":
                fig = visualizer.render_snapshot_frame()
                st.pyplot(fig)
            else:

                min_t, max_t = int(df['t'].min()), int(df['t'].max())
                selected_t = st.slider("Select Time Stamp (t)", min_t, max_t, min_t)

                fig = visualizer.render_snapshot_frame(current_time=selected_t)
                st.pyplot(fig)
    else:
        st.info("Please upload a JSON file to begin. Format: `[{'u': '1', 'v': '2', 't': 5}, ...]`")


if __name__ == "__main__":
    main()