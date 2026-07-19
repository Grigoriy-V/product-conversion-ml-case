# Online Shoppers train-only threshold analysis

Five group-safe OOF fits used only 9,864 frozen train rows; no frozen test or final-test artifact was read. Fixed RF and preprocessing were unchanged.

Selected pooled-OOF F2 (beta=2) threshold: `0.127325`. F2=0.583341, precision=0.253803, recall=0.863696, F1=0.392320, balanced accuracy=0.699478, predicted-positive rate=0.526460, confusion=[[4463, 3875], [208, 1318]].

Default 0.5: F2=0.072684, precision=0.583333, recall=0.059633, F1=0.108205, balanced accuracy=0.525919, predicted-positive rate=0.015815, confusion=[[8273, 65], [1435, 91]].

OOF AP=0.375891; ROC-AUC=0.778324. F2 is a portfolio assumption prioritizing missed conversions, not a production cost function. Calibration method: none; raw RF scores are not claimed as calibrated probabilities.
