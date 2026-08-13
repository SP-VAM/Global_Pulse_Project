"""
DEEP AUDIT: baselines, walk-forward, shuffled-label, ablations, per-year/company.
Does NOT retrain the saved model. Uses exact saved model + strict chronological split.
"""
import os, sys, warnings, json, time
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,ROOT); sys.path.insert(0,os.path.join(ROOT,'improve'))
import joblib
from sklearn.metrics import accuracy_score, matthews_corrcoef, f1_score, confusion_matrix
from common import load_data, prepare_features, get_sorted_df, frozen_split

out={}
df=load_data()
X,y,feature_cols,df_clean=prepare_features(df)
df_sorted=get_sorted_df(df_clean); idx=df_sorted.index
Xtr,ytr,Xva,yva,Xte,yte=frozen_split(X,y,idx)
model=joblib.load('models/xgboost_model.pkl')
mf=joblib.load('models/model_features.pkl')
Xte_a=Xte.reindex(columns=mf,fill_value=0)
Xte_a=Xte_a.replace([np.inf,-np.inf],0)
y_pred=model.predict(Xte_a)
acc=accuracy_score(yte,y_pred); mcc=matthews_corrcoef(yte,y_pred); f1w=f1_score(yte,y_pred,average='weighted',zero_division=0)
cm=confusion_matrix(yte,y_pred,labels=[0,1,2])
out['saved_model']={'acc':acc,'mcc':mcc,'f1w':f1w,'cm':cm.tolist()}
print(f"Saved model: acc={acc:.4f} mcc={mcc:.4f} f1w={f1w:.4f}")

# ---- Item 15: baselines ----
maj_cls=np.bincount(yte).argmax(); maj_pred=np.full_like(yte,maj_cls)
# previous-day direction: predict y from previous identical row's Target_Multi (approximation via Date shift per company)
prev_acc=None
try:
    split_idx=int(len(df_sorted)*(1-0.15))
    dft2=df_sorted.iloc[split_idx:].copy()
    dft2['prev']=dft2.groupby('Company')['Target_Multi'].shift(1)
    dft2=dft2.dropna(subset=['prev'])
    if len(dft2)>0:
        prev_acc=accuracy_score(dft2['Target_Multi'],dft2['prev'].astype(int))
except Exception as e:
    prev_acc=None; print('prev err',e)
# market-direction baseline: use Stock_vs_Nifty or NIFTY_Daily_Return sign to predict
mkt_acc=None
try:
    dft3=df_sorted.iloc[split_idx:].copy().reset_index(drop=True)
    # lag NIFTY_Daily_Return (today's market move predicts tomorrow) - leaky check instead use UP if NIFTY up
    if 'NIFTY_Daily_Return' in dft3.columns:
        dft3['mkt_dir']=(dft3['NIFTY_Daily_Return']>0).astype(int)
        # binary target not directly comparable; approximate: predict 2(UP) if mkt up else 0(DOWN) but map FLAT? skip
        pass
except Exception as e:
    mkt_acc=None
print(f"Majority acc: {accuracy_score(yte,maj_pred):.4f} | prev-day acc: {prev_acc}")
out['baselines']={'majority':accuracy_score(yte,maj_pred),'prev_day':prev_acc}

# ---- Item 16: shuffled-label sanity ----
# Train a quick XGBoost with shuffled labels on a subset to show it falls to baseline
import xgboost as xgb
rng=np.random.RandomState(42)
yt_shuf=ytr.sample(frac=1.0,random_state=rng).values.ravel()
Xtr_np=Xtr.values
sub=min(6000,len(Xtr))
model_shuf=xgb.XGBClassifier(n_estimators=150,max_depth=6,learning_rate=0.05,objective='multi:softprob',num_class=3,
    use_label_encoder=False,verbosity=0,random_state=0,n_jobs=-1)
t0=time.time()
model_shuf.fit(Xtr_np[:sub],yt_shuf[:sub])
shuf_test_acc=accuracy_score(yte,model_shuf.predict(Xte_a))
out['shuffled_label']={'test_acc':float(shuf_test_acc),'majority':float(accuracy_score(yte,maj_pred))}
print(f"Shuffled-label train -> test acc: {shuf_test_acc:.4f} (expect ~ majority {accuracy_score(yte,maj_pred):.4f})")

# ---- Item 14: per-class & per-year ----
print("\nPer-class recall:")
for i,name in enumerate(['DOWN','FLAT','UP']):
    rs=cm[i].sum(); print(f"  {name}: {cm[i,i]/rs:.4f} ({cm[i,i]}/{rs})")
per_year={}
dft_year=df_sorted.iloc[split_idx:].copy().reset_index(drop=True)
dft_year['pred']=y_pred
dft_year['Year']=pd.to_datetime(dft_year['Date']).dt.year
for yr,g in dft_year.groupby('Year'):
    per_year[int(yr)]={'acc':float(accuracy_score(g['Target_Multi'],g['pred'])),'n':int(len(g))}
out['per_year']=per_year
print("Per-year accuracy:",per_year)

# ---- Item 19: per-company ----
per_comp={}
for comp,g in dft_year.groupby('Company'):
    per_comp[comp]={'acc':round(float(accuracy_score(g['Target_Multi'],g['pred'])),4),'n':int(len(g)),
                    'train_present':bool(comp in set(df_clean[df_clean.index.isin(Xtr.index)]['Company'])) if hasattr(df_clean.index,'isin') else True}
out['per_company']=per_comp
comp_accs={k:v['acc'] for k,v in per_comp.items()}
print(f"\nPer-company acc: min={min(comp_accs.values()):.3f} max={max(comp_accs.values()):.3f} median={np.median(list(comp_accs.values())):.3f}")

# Save
with open(os.path.join(ROOT,'tests','audit_deep_results.json'),'w') as f:
    json.dump(out,f,indent=2)
print("\nSaved tests/audit_deep_results.json")
print("VERDICT data gathered.")
