import streamlit as st
import pandas as pd
import networkx as nx
import random
import matplotlib.pyplot as plt


def generate_test_data(num_nodes=500, num_edges=1000):
    nodes = [str(i) for i in range(1, num_nodes + 1)]
    data = []
    for _ in range(num_edges):
        u = random.choice(nodes)
        v = random.choice([n for n in nodes if n != u])
        t = random.randint(1, 100)
        data.append({'u': u, 'v': v, 't': t})
    return pd.DataFrame(data)


class TemporalVisualizer:
    def __init__(self, df):
        self.df = df
        self.G = nx.DiGraph()
        for _, row in df.iterrows():
            self.G.add_edge(row['u'], row['v'])

        self.pos = self.compute_static_layout()

    def compute_static_layout(self):

        return nx.spring_layout(self.G, seed=42)

    def render_snapshot_frame(self, current_time=None):

        fig, ax = plt.subplots(figsize=(12, 8))

        if current_time is not None:
            display_df = self.df[self.df['t'] <= current_time]
            edges = list(zip(display_df['u'], display_df['v']))
            active_nodes = set(display_df['u']).union(set(display_df['v']))
        else:
            edges = list(self.G.edges())
            active_nodes = list(self.G.nodes())


        nx.draw_networkx_nodes(self.G, self.pos, nodelist=active_nodes,
                               node_color='lightgreen', node_size=50, ax=ax)

        if len(active_nodes) < 50:
            nx.draw_networkx_labels(self.G, self.pos, font_size=8, ax=ax)

        nx.draw_networkx_edges(self.G, self.pos, edgelist=edges,
                               edge_color='gray', arrows=True, alpha=0.5, ax=ax)

        title = f"Network Scale: {len(active_nodes)} Nodes" if current_time is None else f"Snapshot at t={current_time}"
        ax.set_title(title)
        return fig


def main():
    st.title("Temporal Path Explorer - High Scale Mode")
    st.sidebar.header("Test Settings")


    num_nodes = st.sidebar.slider("Number of Nodes", 5, 500, 500)

    num_edges = st.sidebar.slider("Number of Edges", 10, 2000, 1000)

    if st.sidebar.button("Regenerate Random Data"):
        st.session_state.df = generate_test_data(num_nodes, num_edges)
        st.success(f"Generated {num_nodes} nodes and {num_edges} edges.")

    if 'df' not in st.session_state:
        st.session_state.df = generate_test_data(num_nodes, num_edges)

    df = st.session_state.df

    with st.expander("Show Generated Data"):
        st.write(df)

    visualizer = TemporalVisualizer(df)
    mode = st.radio("Display Mode", ["Full Static Graph", "Single Snapshot"])

    if mode == "Full Static Graph":
        fig = visualizer.render_snapshot_frame()
        st.pyplot(fig)
    else:
        min_t, max_t = int(df['t'].min()), int(df['t'].max())
        selected_t = st.slider("Select Time (t)", min_t, max_t, min_t)
        fig = visualizer.render_snapshot_frame(current_time=selected_t)
        st.pyplot(fig)


if __name__ == "__main__":
    main()