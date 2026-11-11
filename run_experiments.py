"""Reproducible Phase-3 benchmark and initial evidence generator.

Phase 3 has 3 increasing sizes, each with three documented overlap profiles,
plus the unchanged 111-job source extract and a 6-job manual example.
The profiles are objective structures, NOT theoretical best/worst running times.
"""
from __future__ import annotations
from pathlib import Path
import csv
import hashlib
import json
import math
import platform
import random
import sys
import time
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from alg import Task, exact_greedy, finish_order, is_feasible, run_genetic_algorithm
from data_io import read_input, infer_columns, make_tasks

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
FIGURES = ROOT / 'figures'
RESULTS = ROOT / 'results'
SOURCE_URL = 'https://andreas-ernst.github.io/Mathprog-ORlib/info/readmePTSP.html'
SOURCE_MEMBER = 'Data_10_51_111_66.dat'
SEED = 42


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_csv(path: Path) -> list[Task]:
    df, _ = read_input(path.name, path.read_bytes())
    return make_tasks(df, infer_columns(df))


def write_jobs(path: Path, jobs: list[Task]) -> None:
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['task_id', 'start_time', 'finish_time'])
        for job in jobs:
            w.writerow([job.task_id, f'{job.start:.8g}', f'{job.finish:.8g}'])


def make_profiles(base: list[Task], n: int) -> dict[str, list[Task]]:
    durations = [j.finish-j.start for j in base[:n]]
    ids = [j.task_id for j in base[:n]]
    profiles = {}
    # Best profile: original durations placed consecutively, zero overlaps.
    jobs, cursor = [], 0.0
    for tid, duration in zip(ids, durations):
        jobs.append(Task(tid, cursor, cursor+duration))
        cursor += duration
    profiles['best'] = jobs
    # Average (representative moderate overlap): seeded step using previous duration.
    rng = random.Random(SEED)
    jobs, cursor = [], 0.0
    for i,(tid,duration) in enumerate(zip(ids,durations)):
        if i:
            step = max(1, math.ceil(durations[i-1]*rng.uniform(.45,.75)))
            cursor += step
        jobs.append(Task(tid,cursor,cursor+duration))
    profiles['average'] = jobs
    # Worst profile: all intervals share time 0 (max feasible count == 1).
    profiles['worst'] = [Task(tid,0.0,duration) for tid,duration in zip(ids,durations)]
    return profiles


def save_convergence(rows: dict[str,list[int]], best: dict[str,int], n: int) -> None:
    fig,ax=plt.subplots(figsize=(9,4.4))
    colors={'best':'#087f9c','average':'#ad4c89','worst':'#b58921'}
    for profile,history in rows.items():
        ax.plot(range(len(history)), history, label=f'{profile.title()} - best {history[-1]}/{best[profile]}',
                linewidth=2, color=colors[profile])
    ax.set_xlabel('Generation (0 = initial population)')
    ax.set_ylabel('Best feasible task count')
    ax.set_title(f'GA convergence | {n} jobs | seed {SEED}')
    ax.grid(alpha=.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURES / f'convergence_{n}.png',dpi=190)
    plt.close(fig)


def save_schedule(jobs: list[Task], title: str, path: Path) -> None:
    fig,ax=plt.subplots(figsize=(9,max(2.5,len(jobs)*.55)))
    for i,task in enumerate(jobs):
        ax.barh(i,task.finish-task.start,left=task.start,height=.64,color='#087f9c')
    ax.set_yticks(range(len(jobs)))
    ax.set_yticklabels([j.task_id for j in jobs])
    ax.invert_yaxis()
    ax.set_xlabel('Time (numeric dataset units)')
    ax.set_title(title)
    ax.grid(axis='x',alpha=.2)
    fig.tight_layout()
    fig.savefig(path,dpi=180)
    plt.close(fig)


def main():
    DATA.mkdir(exist_ok=True)
    RESULTS.mkdir(exist_ok=True)
    FIGURES.mkdir(exist_ok=True)
    base_file = DATA / 'Khaled_Activity_Selection_Dataset_111.csv'
    base=load_csv(base_file)
    assert len(base)==111
    meta={'source':{'repository':'Mathprog-ORlib PTSP','url':SOURCE_URL,
                    'original_archive':'ptask.zip','selected_member':SOURCE_MEMBER,
                    'primary_extraction':'Jobs = 111 section; ID added by row number',
                    'csv_original':base_file.name,'original_sha256':sha256(base_file),
                    'source_type':'synthetic academic benchmark, not observed field data'},
          'scenarios':{}, 'generation_seed':SEED,
          'explanation':'best/average/worst describe interval overlap structure, not theoretical runtime case',
          'generation_rule':{'size':'first n rows in original order; preserve durations and IDs',
                             'best':'s_1=0, s_i=f_(i-1), f_i=s_i+d_i',
                             'average':'s_1=0, s_i=s_(i-1)+max(1,ceil(d_(i-1)*U_i)), U~Uniform(0.45,0.75), seed=42 per size',
                             'worst':'s_i=0, f_i=d_i'},
          'times':'original numeric units, not assumed hours or clock time'}
    rows=[]
    for n in (25,60,111):
        hist,best={},{ }
        for label,jobs in make_profiles(base,n).items():
            path=DATA / f'Khaled_Phase3_{n}_{label}.csv'
            write_jobs(path,jobs)
            optimum=len(exact_greedy(jobs))
            result=run_genetic_algorithm(jobs,seed=SEED)
            assert is_feasible(result.chromosome,jobs)
            assert 0<=result.fitness<=optimum
            assert result.fitness==len(result.selected)
            if label=='best': assert optimum==n
            if label=='worst': assert optimum==1
            hist[label]=result.history
            best[label]=optimum
            meta['scenarios'][path.name]={'size':n,'profile':label,'source_original':base_file.name,
                                         'sha256':sha256(path),'exact_optimum':optimum,'is_derived':True,
                                         'row_count':len(jobs),'columns':['task_id','start_time','finish_time']}
            rows.append({'instance':f'{n}-{label}','size':n,'profile':label,'seed':SEED,
                         'ga_fitness':result.fitness,'exact_optimum':optimum,'gap':result.gap,
                         'generations':result.generations,'evaluations':result.evaluations,
                         'elapsed_seconds':round(result.elapsed_seconds,6),
                         'feasible':is_feasible(result.chromosome,jobs),
                         'stop_reason':result.stop_reason,
                         'selected_ids':';'.join(t.task_id for t in result.selected)})
        save_convergence(hist,best,n)
    original=run_genetic_algorithm(base,seed=SEED)
    exact_sel=[base[i] for i in exact_greedy(base)]
    assert [x.task_id for x in exact_sel]==['T007','T036','T081']
    rows.append({'instance':'111-original-PTSP','size':111,'profile':'original PTSP extract','seed':SEED,
                 'ga_fitness':original.fitness,'exact_optimum':original.exact_greedy_count,'gap':original.gap,
                 'generations':original.generations,'evaluations':original.evaluations,
                 'elapsed_seconds':round(original.elapsed_seconds,6), 'feasible':is_feasible(original.chromosome,base),
                 'stop_reason':original.stop_reason,'selected_ids':';'.join(t.task_id for t in original.selected)})
    # Manual example from Phase 2.
    manual=[Task('A',1,3),Task('B',2,5),Task('C',3,4),Task('D',4,7),Task('E',5,6),Task('F',6,8)]
    write_jobs(DATA/'manual_6_jobs.csv',manual)
    check=run_genetic_algorithm(manual,seed=SEED)
    assert check.exact_greedy_count==4
    save_schedule(check.selected,'Selected jobs: six-job manual example',FIGURES/'selected_schedule_manual.png')
    save_schedule(exact_sel,'Exact Greedy reference: original 111-job benchmark',FIGURES/'selected_original_reference.png')
    fig,ax=plt.subplots(figsize=(8.5,4.0))
    ax.plot(range(len(original.history)),original.history,color='#087f9c',linewidth=2,marker='o',markersize=3)
    ax.axhline(original.exact_greedy_count,ls='--',color='#ad4c89',label='Exact optimum = 3')
    ax.set_title('Original PTSP 111-job extract | GA convergence')
    ax.set_xlabel('Generation (0 = initial population)')
    ax.set_ylabel('Best feasible task count')
    ax.grid(alpha=.2);ax.legend();fig.tight_layout()
    fig.savefig(FIGURES/'convergence_original.png',dpi=190);plt.close(fig)

    meta['scenarios'][base_file.name]={'size':111,'profile':'original','is_derived':False,
                                      'exact_optimum':3,'sha256':sha256(base_file)}
    meta['scenarios']['manual_6_jobs.csv']={'size':6,'profile':'educational_hand_calculated',
                                          'is_derived':False,'exact_optimum':4}
    (DATA/'DATASET_MANIFEST.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    with (RESULTS/'phase3_results.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0].keys()))
        writer.writeheader();writer.writerows(rows)
    fixed_a=run_genetic_algorithm(base,seed=SEED)
    fixed_b=run_genetic_algorithm(base,seed=SEED)
    reproducible=(fixed_a.history==fixed_b.history and fixed_a.chromosome==fixed_b.chromosome)
    assert reproducible
    env={'python_version':sys.version.split()[0],'operating_system':platform.platform(),
         'python_ide':'Terminal/Spyder-compatible Python; UI via Streamlit browser',
         'pandas':pd.__version__,'matplotlib':plt.matplotlib.__version__,
         'ga_seed':SEED,'repeatability_fixed_seed':reproducible,
         'repeatability_note':'Fitness, chromosome, generations and history match exactly; measured seconds may differ',
         'test_count':len(rows),'manual_example_optimum':4,
         'original_reference_optimum':3,'original_reference_ids':['T007','T036','T081']}
    (RESULTS/'environment_and_checks.json').write_text(json.dumps(env,indent=2),encoding='utf-8')
    print('Python',env['python_version'],'Pandas',env['pandas'],'Matplotlib',env['matplotlib'])
    print('Repeatability (seed 42):',reproducible)
    print(f"{'Instance':22} {'N':>5} {'GA':>5} {'Opt':>5} {'Gap':>5} {'Gen':>5} {'Time(s)':>10} {'Valid':>7}")
    for x in rows:
        print(f"{x['instance']:22} {x['size']:5} {x['ga_fitness']:5} {x['exact_optimum']:5} {x['gap']:5} {x['generations']:5} {x['elapsed_seconds']:10.5f} {str(x['feasible']):>7}")
    print('Artifacts: data/*.csv, data/DATASET_MANIFEST.json, figures/*.png, results/*.csv')

if __name__=='__main__':main()
