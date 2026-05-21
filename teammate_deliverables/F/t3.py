import streamlit as st
import pandas as pd
import networkx as nx
import random
import matplotlib.pyplot as plt


#
# Random Data Generator


def generate_test_data(num_nodes=10, num_edges=20):

    nodes = [str(i) for i in range(1, num_nodes + 1)]
    data = []
    for _ in range(num_edges):
        u = random.choice(nodes)
        v = random.choice([n for n in nodes if n != u])  # 避免自环
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

        fig, ax = plt.subplots(figsize=(10, 7))

        if current_time is not None:
            display_df = self.df[self.df['t'] <= current_time]
            edges = list(zip(display_df['u'], display_df['v']))
            active_nodes = set(display_df['u']).union(set(display_df['v']))
        else:
            edges = list(self.G.edges())
            active_nodes = list(self.G.nodes())

        nx.draw_networkx_nodes(self.G, self.pos, nodelist=active_nodes,
                               node_color='lightgreen', node_size=500, ax=ax)
        nx.draw_networkx_labels(self.G, self.pos, font_size=10, ax=ax)

        nx.draw_networkx_edges(self.G, self.pos, edgelist=edges,
                               edge_color='gray', arrows=True, ax=ax)

        title = "Full Static Network" if current_time is None else f"Temporal Snapshot at t={current_time}"
        ax.set_title(title)
        return fig


def main():
    st.title("Temporal Path Explorer - Random Test Mode")
    st.sidebar.header("Test Settings")

    num_nodes = st.sidebar.slider("Number of Nodes", 5, 20, 10)
    num_edges = st.sidebar.slider("Number of Edges", 10, 50, 25)

    if st.sidebar.button("Regenerate Random Data"):
        st.session_state.df = generate_test_data(num_nodes, num_edges)
        st.success("New test data generated!")

    if 'df' not in st.session_state:
        st.session_state.df = generate_test_data(num_nodes, num_edges)

    df = st.session_state.df

    with st.expander("Show Generated (u, v, t) Data"):
        st.write(df)

    visualizer = TemporalVisualizer(df)

    mode = st.radio("Display Mode", ["Full Static Graph", "Single Snapshot"])

    if mode == "Full Static Graph":
        fig = visualizer.render_snapshot_frame()
        st.pyplot(fig)
    else:
        min_t, max_t = int(df['t'].min()), int(df['t'].max())
        selected_t = st.slider("Select Time (t)", min_t, max_t, int((min_t + max_t) / 2))

        fig = visualizer.render_snapshot_frame(current_time=selected_t)
        st.pyplot(fig)


if __name__ == "__main__":
    main()

    #Functions will be applied:

    #BFS_Single 使用了 prior_queue 并通过 if time_stamp >= time: 来判断时序约束
    #Arrive_time_and_Latency