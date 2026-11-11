import unittest
import io
import pandas as pd
from alg import Task, exact_greedy, finish_order, repair, is_feasible, run_genetic_algorithm, validate_tasks
from data_io import read_input, infer_columns, make_tasks

class AlgorithmTests(unittest.TestCase):
    def setUp(self):
        self.jobs = [Task('A',1,3),Task('B',2,5),Task('C',3,4),Task('D',4,7),Task('E',5,6),Task('F',6,8)]

    def test_exact_optimum_small_manual(self):
        self.assertEqual([self.jobs[i].task_id for i in exact_greedy(self.jobs)], ['A','C','E','F'])

    def test_conflict_repair(self):
        order = finish_order(self.jobs)
        repaired = repair([1,1,1,0,1,0],self.jobs,order)
        self.assertEqual(repaired,[1,0,1,0,1,0])
        self.assertTrue(is_feasible(repaired,self.jobs))

    def test_ga_feasible_and_history(self):
        result = run_genetic_algorithm(self.jobs,seed=42)
        self.assertTrue(is_feasible(result.chromosome,self.jobs))
        self.assertEqual(result.fitness,len(result.selected))
        self.assertEqual(result.exact_greedy_count,4)
        self.assertEqual(result.history[-1],result.fitness)
        self.assertLessEqual(result.fitness,4)
        self.assertEqual(len(result.history),result.generations+1)
        self.assertTrue(all(a<=b for a,b in zip(result.history,result.history[1:])))

    def test_seed_reproducibility(self):
        a=run_genetic_algorithm(self.jobs,seed=42)
        b=run_genetic_algorithm(self.jobs,seed=42)
        self.assertEqual((a.chromosome,a.history,a.generations),(b.chromosome,b.history,b.generations))

    def test_empty_input(self):
        self.assertEqual(run_genetic_algorithm([]).fitness,0)

    def test_single_task_and_back_to_back(self):
        self.assertEqual(run_genetic_algorithm([Task('A',0,1)]).fitness,1)
        self.assertEqual(len(exact_greedy([Task('A',0,1),Task('B',1,2)])),2)

    def test_duplicate_and_invalid_times(self):
        with self.assertRaises(ValueError): validate_tasks([Task('A',1,2),Task('A',3,4)])
        with self.assertRaises(ValueError): validate_tasks([Task('A',2,2)])
        with self.assertRaises(ValueError): validate_tasks([Task('A',float('nan'),2)])

    def test_import_header_synonyms(self):
        df,_ = read_input('jobs.csv',b'Job,Begin,End,Priority\nX,1,2,high\nY,2,3,low\n')
        jobs = make_tasks(df,infer_columns(df))
        self.assertEqual([t.task_id for t in jobs],['X','Y'])
        self.assertEqual(len(exact_greedy(jobs)),2)

    def test_import_headerless_pairs(self):
        df,_=read_input('jobs.txt',b'1 3\n3 5\n5 7\n')
        jobs=make_tasks(df,infer_columns(df))
        self.assertEqual(len(jobs),3)

    def test_import_semicolon_and_invalids(self):
        df,_=read_input('j.csv',b'name;start;finish\nX;1;3\nY;4;5\n')
        self.assertEqual(len(make_tasks(df,infer_columns(df))),2)
        df2=pd.DataFrame({'task_id':['A','B'],'start_time':[1,4],'finish_time':[3,'bad']})
        with self.assertRaisesRegex(ValueError,'Data row 2'):
            make_tasks(df2,infer_columns(df2))

    def test_original_ptsp_file(self):
        text='\n'.join(['# Example','Type = 1','Jobs = 2',' 1 3',' 3 5','Qualifications = 5','stuff'])
        df,_=read_input('sample.dat',text.encode())
        self.assertEqual(len(make_tasks(df,infer_columns(df))),2)

    def test_initial_solution_not_injected_from_reference(self):
        jobs=[Task(f'T{i}',i*2,i*2+1) for i in range(20)]
        result=run_genetic_algorithm(jobs,max_generations=0,seed=42)
        self.assertLess(result.fitness,result.exact_greedy_count)
        self.assertEqual(result.generations,0)

if __name__=='__main__':unittest.main()
