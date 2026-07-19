import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Scaffold(unittest.TestCase):
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
  self.assertFalse(any(p.name.endswith(('.csv','.parquet','.pkl','.joblib')) for p in ROOT.rglob('*') if p.is_file()))
if __name__=='__main__':unittest.main()
