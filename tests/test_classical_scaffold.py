import json,subprocess,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Scaffold(unittest.TestCase):
 def test_single_canonical_ml_roadmap(self):
  self.assertTrue((ROOT/'ML_PROJECT_ROADMAP.md').is_file())
  self.assertFalse((ROOT/'PROJECT_ROADMAP.md').exists())
 def test_schema_contract(self):
  s=json.loads((ROOT/'reports/experiment_ledger.schema.json').read_text())
  self.assertEqual(s['schema_vocabulary'],'bundled-classical-v2')
  self.assertIn('dataset',s['required']);self.assertIn('threshold',s['required'])
  self.assertFalse(s['additionalProperties'])
  self.assertIn('does not claim a complete JSON Schema Draft',s['contract_note'])
  p=json.loads((ROOT/'core/orchestration_lock.schema.json').read_text())
  self.assertFalse(p['additionalProperties'])
  self.assertEqual(p['properties']['managed_files']['minItems'],13)
 def test_no_data_or_model(self):
  tracked=subprocess.run(['git','-C',str(ROOT),'ls-files','-z'],check=True,capture_output=True).stdout.decode('utf-8').split('\0')
  tracked=[path for path in tracked if path]
  forbidden=[path for path in tracked if path.startswith(('data/','outputs/','artifacts/','models/')) or path.endswith(('.csv','.parquet','.pkl','.joblib'))]
  self.assertEqual(forbidden,[],f'tracked data/model/artifact files are forbidden: {forbidden}')
if __name__=='__main__':unittest.main()
