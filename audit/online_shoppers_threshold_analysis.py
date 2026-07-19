"""Train-only OOF operating-point analysis for the fixed Online Shoppers RF."""
from __future__ import annotations
import argparse, json, time
from pathlib import Path
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, balanced_accuracy_score, confusion_matrix, f1_score, fbeta_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import Pipeline
try:
    from audit.online_shoppers_audit import sha256_file
    from audit.online_shoppers_baseline import load_train_only, make_preprocessor, validate_folds
    from audit.online_shoppers_model_comparison import RF_CONFIG
except ModuleNotFoundError:
    from online_shoppers_audit import sha256_file
    from online_shoppers_baseline import load_train_only, make_preprocessor, validate_folds
    from online_shoppers_model_comparison import RF_CONFIG
SOURCE_SHA256="b3055ee355f59134d851d32641183cb4a8b45def7124d2f50442a042f358e0d9"
MEMBERSHIP_SHA256="8dd85409ff57638ed5a8197cb2d0fe5d1d13ff90c59b6dbd83e08c475e2deee1"
DEFAULT_THRESHOLD=0.5; BETA=2.0; RECALL_TARGETS=(0.50,0.60,0.70)
def make_model(): return Pipeline([("preprocess",make_preprocessor()),("model",RandomForestClassifier(**RF_CONFIG))])
def metrics(y,s,t):
 p=s>=t; m=confusion_matrix(y,p,labels=[False,True])
 return {"threshold":float(t),"f2":float(fbeta_score(y,p,beta=BETA,zero_division=0)),"precision":float(precision_score(y,p,zero_division=0)),"recall":float(recall_score(y,p,zero_division=0)),"f1":float(f1_score(y,p,zero_division=0)),"balanced_accuracy":float(balanced_accuracy_score(y,p)),"confusion_matrix_labels_false_true":m.astype(int).tolist(),"predicted_positive":int(p.sum()),"predicted_positive_rate":float(p.mean())}
def threshold_table(y,s):
 """O(n log n) unique-score table via descending sort and cumulative counts."""
 y=np.asarray(y,dtype=bool);s=np.asarray(s,dtype=float)
 if len(y)==0 or len(y)!=len(s) or not np.isfinite(s).all(): raise ValueError("invalid threshold inputs")
 order=np.argsort(-s,kind="mergesort"); score=s[order]; label=y[order]
 end=np.r_[score[:-1]!=score[1:],True]; idx=np.flatnonzero(end)
 tp=np.cumsum(label)[idx].astype(int); predicted=idx+1; positives=int(y.sum()); negatives=len(y)-positives
 fp=predicted-tp; fn=positives-tp; tn=negatives-fp
 precision=np.divide(tp,predicted,out=np.zeros(len(idx),float),where=predicted>0)
 recall=np.divide(tp,positives,out=np.zeros(len(idx),float),where=positives>0)
 f1=np.divide(2*precision*recall,precision+recall,out=np.zeros(len(idx),float),where=(precision+recall)>0)
 f2=np.divide(5*precision*recall,4*precision+recall,out=np.zeros(len(idx),float),where=(4*precision+recall)>0)
 tpr=recall; tnr=np.divide(tn,negatives,out=np.zeros(len(idx),float),where=negatives>0)
 ba=(tpr+tnr)/2 if positives and negatives else np.where(positives,tpr,tnr)
 return [{"threshold":float(score[i]),"f2":float(f2[j]),"precision":float(precision[j]),"recall":float(recall[j]),"f1":float(f1[j]),"balanced_accuracy":float(ba[j]),"confusion_matrix_labels_false_true":[[int(tn[j]),int(fp[j])],[int(fn[j]),int(tp[j])]],"predicted_positive":int(predicted[j]),"predicted_positive_rate":float(predicted[j]/len(y))} for j,i in enumerate(idx)]
def choose(y,s):
 items=[(item["threshold"],item) for item in threshold_table(y,s)]+[(DEFAULT_THRESHOLD,metrics(y,s,DEFAULT_THRESHOLD))]
 return max(items,key=lambda x:(x[1]["f2"],x[1]["recall"],x[1]["precision"],x[0]))
def points(y,s):
 result={}
 table=threshold_table(y,s)
 for target in RECALL_TARGETS:
  eligible=[item for item in table if item["recall"]>=target]
  result[f"recall_at_least_{target:.2f}"]=max(eligible,key=lambda x:(x["precision"],x["threshold"])) if eligible else None
 return result
def run(source,membership):
 if sha256_file(source)!=SOURCE_SHA256 or sha256_file(membership)!=MEMBERSHIP_SHA256: raise ValueError("accepted source or membership hash mismatch")
 X,y,folds,boundary=load_train_only(source,membership); checks=validate_folds(y,folds); oof=np.full(len(y),np.nan)
 for fold in range(5):
  valid=np.fromiter((folds[i]==fold for i in range(len(y))),dtype=bool,count=len(y))
  if not valid.any() or np.isfinite(oof[valid]).any(): raise ValueError("invalid OOF fold assignment")
  oof[valid]=make_model().fit(X.loc[~valid],y[~valid]).predict_proba(X.loc[valid])[:,1]
 if not np.isfinite(oof).all(): raise ValueError("missing/nonfinite OOF scores")
 threshold,selected=choose(y,oof)
 return {"protocol":{"source_sha256":SOURCE_SHA256,"membership_sha256":MEMBERSHIP_SHA256,"train_rows":len(y),"n_folds":5,"fold_checks":checks,"test_access":"No frozen test row, label, score, metric, or final-test artifact is read, materialized, predicted, or scored.","excluded_features":["Revenue","PageValues"]},"model":{"class":"sklearn.ensemble.RandomForestClassifier","params":RF_CONFIG},"calibration":{"method":"none","performed":False,"statement":"Raw RF scores support ranking and the train-OOF decision threshold only; they are not asserted calibrated probabilities."},"selection_rule":{"objective":"maximize pooled train-only OOF F2","beta":BETA,"tie_breakers":["higher recall","higher precision","higher threshold"],"portfolio_assumption":"F2 prioritizes missed conversions for illustration, not a production cost function."},"oof_ranking_metrics":{"average_precision":float(average_precision_score(y,oof)),"roc_auc":float(roc_auc_score(y,oof))},"selected_operating_point":selected,"default_threshold_0_5":metrics(y,oof,DEFAULT_THRESHOLD),"recall_constrained_operating_points":points(y,oof)}
def main():
 p=argparse.ArgumentParser();p.add_argument("--source",type=Path,required=True);p.add_argument("--membership",type=Path,required=True);p.add_argument("--output",type=Path,required=True);p.add_argument("--report",type=Path,required=True);a=p.parse_args();start=time.perf_counter();r=run(a.source,a.membership);r["total_runtime_seconds"]=time.perf_counter()-start;a.output.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n",encoding="utf-8");s=r["selected_operating_point"];d=r["default_threshold_0_5"];a.report.write_text(f"# Online Shoppers train-only threshold analysis\n\nFive group-safe OOF fits used only 9,864 frozen train rows; no frozen test or final-test artifact was read. Fixed RF and preprocessing were unchanged.\n\nSelected pooled-OOF F2 (beta=2) threshold: `{s['threshold']:.6f}`. F2={s['f2']:.6f}, precision={s['precision']:.6f}, recall={s['recall']:.6f}, F1={s['f1']:.6f}, balanced accuracy={s['balanced_accuracy']:.6f}, predicted-positive rate={s['predicted_positive_rate']:.6f}, confusion={s['confusion_matrix_labels_false_true']}.\n\nDefault 0.5: F2={d['f2']:.6f}, precision={d['precision']:.6f}, recall={d['recall']:.6f}, F1={d['f1']:.6f}, balanced accuracy={d['balanced_accuracy']:.6f}, predicted-positive rate={d['predicted_positive_rate']:.6f}, confusion={d['confusion_matrix_labels_false_true']}.\n\nOOF AP={r['oof_ranking_metrics']['average_precision']:.6f}; ROC-AUC={r['oof_ranking_metrics']['roc_auc']:.6f}. F2 is a portfolio assumption prioritizing missed conversions, not a production cost function. Calibration method: none; raw RF scores are not claimed as calibrated probabilities.\n",encoding="utf-8");print(json.dumps(r,sort_keys=True))
if __name__=="__main__": main()
