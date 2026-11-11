"""A small, understandable Streamlit interface; algorithms live only in alg.py."""
from pathlib import Path
import hashlib
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from alg import Task, run_genetic_algorithm, exact_greedy
from data_io import read_input, infer_columns, make_tasks, tasks_to_dataframe

st.set_page_config(page_title="ALG | Task Scheduling", page_icon="📅", layout="wide")
st.markdown("""<style>
.block-container { max-width:1150px; padding-top:1.6rem; }
/* High-contrast result cards, readable in Streamlit dark and light themes. */
[data-testid="stMetric"] {
    background-color: #1e293b !important;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 14px 16px;
}
[data-testid="stMetric"] [data-testid="stMetricLabel"],
[data-testid="stMetric"] [data-testid="stMetricLabel"] * {
    color: #cbd5e1 !important;
}
[data-testid="stMetric"] [data-testid="stMetricValue"],
[data-testid="stMetric"] [data-testid="stMetricValue"] * {
    color: #ffffff !important;
}
div[data-testid="stAlert"] { border-radius:10px; }
</style>""", unsafe_allow_html=True)
st.title("Task Scheduling · GA + Greedy")
st.caption("Algorithms Course Project | Choose jobs with non-overlapping start and finish times")
st.html("""
<style>
/* The GitHub link sits directly below the title, not in Streamlit's hidden toolbar. */
.alg-github-row {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
    margin: 5px 0 19px 0;
}
.alg-github-link {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    padding: 11px 17px;
    border: 1px solid #718096;
    border-radius: 11px;
    background: #263445;
    color: #ffffff !important;
    text-decoration: none !important;
    font: 650 15px/1.2 system-ui, sans-serif;
    box-shadow: 0 3px 10px rgba(0, 0, 0, .18);
    transition: background-color .15s ease, border-color .15s ease;
}
.alg-github-link:hover, .alg-github-link:focus-visible {
    background: #36485f;
    border-color: #ff637a;
    color: #ffffff !important;
    text-decoration: none !important;
}
.alg-github-link svg { width: 25px; height: 25px; fill: currentColor; flex-shrink: 0; }
.alg-github-note { color: #9ca3af; font: 12px/1.35 system-ui, sans-serif; }
</style>
<div class="alg-github-row">
  <a class="alg-github-link" href="https://github.com/khaledAlzeer/task-scheduling-ga-greedy"
     target="_blank" rel="noopener noreferrer" aria-label="Open project repository on GitHub">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z"/>
    </svg>
    <span>GitHub</span>
  </a>
  <span class="alg-github-note">Source code · View project on GitHub</span>
</div>
""")
st.info("**What it solves:** maximize the number of non-overlapping jobs on ONE resource. "
        "Genetic Algorithm searches feasible schedules; exact Greedy provides the optimal reference count.")

source = st.radio("How would you like to enter tasks?", ["Load a dataset file", "Enter tasks manually", "Use included 111-task example"], horizontal=True)
raw = None
note = ""
if source == "Load a dataset file":
    uploaded = st.file_uploader("Upload CSV, TSV, TXT, XLSX or original PTSP .dat", type=["csv", "tsv", "txt", "xlsx", "dat"])
    st.caption("Headers like `job`, `start`, `end` are recognized automatically. If column names are unusual, choose them below. Invalid values are reported, never silently changed.")
    if uploaded:
        try:
            raw, note = read_input(uploaded.name, uploaded.getvalue())
        except Exception as exc:
            st.error(f"Could not load file: {exc}")
elif source == "Use included 111-task example":
    path = Path(__file__).parent / "data" / "Khaled_Activity_Selection_Dataset_111.csv"
    raw, note = read_input(path.name, path.read_bytes())
else:
    st.caption("Add or delete rows as needed; times are numbers, not clock strings.")
    if "manual_tasks" not in st.session_state:
        st.session_state.manual_tasks = pd.DataFrame([
            {"task_id":"A","start_time":1.0,"finish_time":3.0},
            {"task_id":"B","start_time":2.0,"finish_time":5.0},
            {"task_id":"C","start_time":3.0,"finish_time":4.0},
            {"task_id":"D","start_time":4.0,"finish_time":7.0},
            {"task_id":"E","start_time":5.0,"finish_time":6.0},
            {"task_id":"F","start_time":6.0,"finish_time":8.0},
        ])
    raw = st.data_editor(st.session_state.manual_tasks, num_rows="dynamic", hide_index=True, use_container_width=True,
                         column_config={"task_id": st.column_config.TextColumn("Task ID", required=True),
                                        "start_time": st.column_config.NumberColumn("Start", required=True),
                                        "finish_time": st.column_config.NumberColumn("Finish", required=True)},
                         key="task_editor")
    note = "Manual data entry"

if raw is not None:
    st.success(f"Input opened: {len(raw)} rows · {note}")
    with st.expander("Check imported data and assign columns", expanded=source == "Load a dataset file"):
        st.dataframe(raw.head(15), hide_index=True, use_container_width=True)
        guess = infer_columns(raw)
        cols = [None] + list(raw.columns)
        labels = {None: "(Not provided — generate task IDs)"}
        c1,c2,c3 = st.columns(3)
        def choose(label, key, area):
            val = guess.get(key)
            return area.selectbox(label, cols, index=cols.index(val) if val in cols else 0,
                                  format_func=lambda x: labels.get(x, str(x)), key=f"map_{key}_{source}")
        id_col = choose("Task ID column (optional)", "task_id", c1)
        start_col = choose("Start time column", "start_time", c2)
        finish_col = choose("Finish time column", "finish_time", c3)
    with st.expander("Genetic Algorithm settings"):
        a,b,c = st.columns(3)
        pop = a.number_input("Population size", 2, 1000, 30)
        generations = b.number_input("Max generations", 0, 10000, 100)
        seed = c.number_input("Random seed", 0, 10_000_000, 42)
        a,b,c = st.columns(3)
        crossover = a.slider("Crossover probability", 0.0, 1.0, .80, .05)
        mutation = b.slider("Mutation per bit", 0.0, 1.0, .05, .01)
        tournament = c.number_input("Tournament size", 1, int(pop), min(3, int(pop)))
    # Do not display stale GA outputs when the user edits/reuploads a dataset.
    current_signature = hashlib.sha256((raw.to_csv(index=False) + str((id_col,start_col,finish_col,pop,generations,seed,crossover,mutation,tournament))).encode('utf-8')).hexdigest()
    if st.button("Find an optimal-compatible schedule", type="primary", use_container_width=True):
        try:
            tasks = make_tasks(raw, {"task_id":id_col, "start_time":start_col, "finish_time":finish_col})
            r = run_genetic_algorithm(tasks, population_size=int(pop), max_generations=int(generations),
                                      crossover_rate=crossover, mutation_rate=mutation,
                                      tournament_size=int(tournament), seed=int(seed))
        except Exception as exc:
            st.error(f"Please correct input or algorithm parameters: {exc}")
        else:
            st.session_state["last_run"] = (r, tasks, source, current_signature)
    if "last_run" in st.session_state:
        r,tasks,prior_source,previous_signature = st.session_state["last_run"]
        if prior_source != source or previous_signature != current_signature:
            st.warning("Your data, column mapping or settings have changed. Run the algorithm again to refresh the results.")
        else:
            st.subheader("Optimization result")
            a,b,c,d = st.columns(4)
            a.metric("GA selected jobs",r.fitness)
            b.metric("Exact Greedy optimum",r.exact_greedy_count)
            c.metric("Optimality gap",r.gap)
            d.metric("Time (seconds)",f"{r.elapsed_seconds:.4f}")
            st.caption(f"Generations: {r.generations} · Fitness evaluations: {r.evaluations} · Seed: {r.seed} · Stop: {r.stop_reason}")
            if r.gap == 0:
                st.success("The GA found a feasible schedule with the maximum possible task count.")
            else:
                st.warning("GA produced a valid schedule, but it did NOT reach the known optimum. This is normal for a heuristic search.")
            left,right = st.columns([1,1])
            with left:
                st.markdown("**Selected jobs (compatible schedule)**")
                selected_df = tasks_to_dataframe(r.selected)
                st.dataframe(selected_df, hide_index=True, use_container_width=True)
                st.download_button("Download selected jobs CSV", selected_df.to_csv(index=False).encode("utf-8"), "selected_jobs.csv", "text/csv")
            with right:
                st.markdown("**Not selected**")
                st.dataframe(tasks_to_dataframe(r.rejected), hide_index=True, use_container_width=True)
            st.markdown("**Convergence: best-so-far selected-job count**")
            fig,ax = plt.subplots(figsize=(9,3))
            ax.plot(list(range(len(r.history))),r.history,marker="o",markersize=3,linewidth=2,label="GA best so far")
            ax.axhline(r.exact_greedy_count,color="tab:orange",linestyle="--",label="Exact Greedy optimum")
            ax.set_xlabel("Generation (0 is initial population)")
            ax.set_ylabel("Number of selected jobs")
            ax.set_ylim(bottom=0)
            ax.legend()
            ax.grid(alpha=.25)
            fig.tight_layout()
            st.pyplot(fig)
            plt.close(fig)
            st.markdown("**Schedule visualization (selected jobs only)**")
            if r.selected:
                fig2,ax2=plt.subplots(figsize=(9,max(2.4,min(8,len(r.selected)*.34))))
                for y,task in enumerate(r.selected):
                    ax2.barh(y,task.finish-task.start,left=task.start,height=.7,color="#087fa1")
                ax2.set_yticks(range(len(r.selected)))
                ax2.set_yticklabels([t.task_id for t in r.selected])
                ax2.invert_yaxis()
                ax2.set_xlabel("Time (dataset units)")
                ax2.set_title("Selected compatible intervals")
                ax2.grid(axis="x",alpha=.25)
                fig2.tight_layout()
                st.pyplot(fig2)
                plt.close(fig2)
            st.caption("Greedy is proven optimal for the standard unweighted Activity Selection model. GA is the required evolutionary-method demonstration, not a claim of better optimality.")
else:
    st.caption("Select or enter data above. You can try the included example without uploading anything.")
