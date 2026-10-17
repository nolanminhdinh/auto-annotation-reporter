"""Check semantic references and filter paths in the generated Power BI source."""
import json
import re
import unittest
from pathlib import Path
from powerbi.build_project import MEASURES
from src.reporting_pipeline import TABLES

PROJECT=Path(__file__).resolve().parents[1]/'powerbi'/'project'

class PowerBIProjectTests(unittest.TestCase):
    def test_dax_column_references_exist_in_contract(self):
        for name,(expr,_) in MEASURES.items():
            for table,col in re.findall(r'(\w+)\[(\w+)\]',expr):
                self.assertIn(table,TABLES,name);self.assertIn(col,TABLES[table],name)

    def test_relationships_have_one_active_filter_path(self):
        data=json.loads((PROJECT/'AnnotationReporter.SemanticModel'/'model.bim').read_text(encoding='utf-8'))
        graph={t:[] for t in TABLES}
        for r in data['model']['relationships']:
            self.assertIn(r['fromColumn'],TABLES[r['fromTable']]);self.assertIn(r['toColumn'],TABLES[r['toTable']])
            self.assertEqual(r['crossFilteringBehavior'],'oneDirection')
            graph[r['toTable']].append(r['fromTable'])
        for origin in graph:
            visited=set()
            def walk(node):
                for child in graph[node]:
                    self.assertNotIn(child,visited,f'Ambiguous or cyclic path from {origin} to {child}')
                    visited.add(child);walk(child)
            walk(origin)

    def test_visual_field_bindings_exist(self):
        files=list((PROJECT/'AnnotationReporter.Report').rglob('visual.json'))
        self.assertEqual(len(files),43)
        for path in files:
            v=json.loads(path.read_text(encoding='utf-8'))
            for role in v['visual']['query']['queryState'].values():
                for p in role['projections']:
                    kind=next(iter(p['field']));f=p['field'][kind];table=f['Expression']['SourceRef']['Entity']
                    if kind=='Measure':self.assertIn(f['Property'],MEASURES)
                    else:self.assertIn(f['Property'],TABLES[table])

if __name__=='__main__':unittest.main()
