from __future__ import annotations
import importlib.util,json
from pathlib import Path
import numpy as np,torch

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("sae_select",ROOT/"scripts/trained_copy_sae_basis_selection_v1.py");assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)

def test_four_splits_are_pairwise_fresh():
 c=M.cfg();p=M.panel_set(c);rows=[r for v in p.values() for r in v]
 assert set(p)=={"fit","selector_fit","development","confirmation"}
 assert len({r['row_id'] for r in rows})==len(rows)
 assert len({r['row_seed'] for r in rows})==len(rows)
 assert len({M.canon((r['clean_values'],r['corrupt_values'],r['sham_values'])) for r in rows})==len(rows)

def test_pca_coverage_greedy_prefers_target_direction():
 d=torch.tensor([[0.,1.],[1.,0.],[1.,1.]])
 assert M.pca_coverage_order(d,np.array([[1.,0.]]))[0]==1

def test_vectorized_reconstruction_selector_matches_scalar_reference():
 g=torch.Generator().manual_seed(9);cc=torch.randn(7,5,generator=g);rc=torch.randn(7,5,generator=g);dec=torch.randn(5,3,generator=g);truth=torch.randn(7,3,generator=g)
 got=M.greedy_reconstruction_order(cc,rc,dec,truth);con=(cc-rc)[:,:,None]*dec[None];res=truth.clone();remain=set(range(5));ref=[]
 for _ in range(5):
  best=min(remain,key=lambda j:(float(torch.sum((res-con[:,j])**2)),j));ref.append(best);res-=con[:,best];remain.remove(best)
 assert got==ref

def test_omp_recovers_single_contribution_and_zero_columns():
 cc=torch.tensor([[2.,0.,0.],[1.,0.,0.]]);rc=torch.zeros_like(cc);decoder=torch.tensor([[1.,0.],[0.,1.],[1.,1.]])
 truth=cc[:,[0]]@decoder[[0]]
 order,coeff=M.omp_order_and_coefficients(cc,rc,decoder,truth)
 assert order==[0,1,2]
 assert np.isclose(coeff['1'][0],1.0)

def test_omp_direct_svd_matches_lstsq_for_ill_conditioned_design():
 # Two nearly collinear contributions expose the normal-equation bug this
 # successor is specifically required to avoid.
 cc=torch.tensor([[1.,1.],[2.,2.+1e-10],[3.,3.-1e-10]],dtype=torch.float64)
 rc=torch.zeros_like(cc);decoder=torch.tensor([[1.,0.],[1.,1e-10]],dtype=torch.float64)
 truth=torch.tensor([[2.,1e-10],[4.+1e-10,(2.+1e-10)*1e-10],[6.-1e-10,(3.-1e-10)*1e-10]],dtype=torch.float64)
 order,paths=M.omp_order_and_coefficients(cc,rc,decoder,truth)
 dz=(cc-rc).numpy();d=decoder.numpy();a=(dz[:,:,None]*d[None,:,:]).transpose(0,2,1).reshape(-1,2)
 ref=np.linalg.lstsq(a[:,order],truth.numpy().reshape(-1),rcond=None)[0]
 assert np.allclose(np.array(paths['2'])[order],ref,rtol=1e-7,atol=1e-9)

def test_omp_prefix_order_matches_exact_lstsq_reference():
 rg=np.random.default_rng(223);cc=rg.normal(size=(6,5));rc=rg.normal(size=(6,5));decoder=rg.normal(size=(5,3));decoder[4]=decoder[0]+1e-11*decoder[4];truth=rg.normal(size=(6,3))
 got,_=M.omp_order_and_coefficients(torch.tensor(cc),torch.tensor(rc),torch.tensor(decoder),torch.tensor(truth))
 dz=cc-rc;a=(dz[:,:,None]*decoder[None]).transpose(0,2,1).reshape(-1,5);yv=truth.reshape(-1);norm=np.linalg.norm(a,axis=0);remain=set(range(5));order=[];res=yv.copy()
 for _ in range(5):
  best=min(remain,key=lambda j:(-abs(float((a[:,j]@res)/norm[j])),j));order.append(best);remain.remove(best);beta=np.linalg.lstsq(a[:,order],yv,rcond=None)[0];res=yv-a[:,order]@beta
 assert got==order

def test_method_inventory_is_complete_and_deduplicates_unweighted_full_budget():
 c=M.cfg();names=M.expected_method_names(c)
 assert len(names)==M.expected_method_count(c)
 assert 'full_code_sae_topk16_seed10601' in names
 assert 'sae_topk16_variance_budget256_seed10601' not in names
 assert 'fit_supervised_omp_beta_topk16_budget256_seed10601' in names
 assert 'decoder_full_span_oracle_topk16_seed10601' in names
 assert 'selected_span_oracle_topk16_variance_budget256_seed10601' not in names

def test_family_conjoins_topk_and_seed_axes():
 assert M.method_family('sae_topk16_variance_budget128_seed1')==M.method_family('sae_topk128_variance_budget128_seed2')
 assert M.method_family('full_code_sae_topk16_seed1')==M.method_family('full_code_sae_topk128_seed2')

def test_cached_active_ids_mark_structural_zeros_missing():
 code=torch.tensor([[2.,0.,0.],[0.,0.,0.]])
 ids=M.active_feature_ids(code,2)
 assert ids[0,0].item()==0 and ids[0,1].item()==-1
 assert torch.all(ids[1]==-1)

def test_confirmation_authorization_ignores_estimated_outcomes():
 assert M.confirmation_authorization(True,True,{'all_fail':True})
 assert not M.confirmation_authorization(False,True,{'all_pass':True})

def test_failure_terminal_is_one_shot_and_forensic(tmp_path,monkeypatch):
 monkeypatch.setattr(M,'ROOT',tmp_path)
 c={'runtime':{'provenance_root':'prov'}}
 M.write_failure_terminal(c,TimeoutError('deadline'))
 rec=json.loads((tmp_path/'prov/TERMINAL.json').read_text())
 assert rec['status']=='TECHNICAL_FAILURE' and rec['no_retry_authorized']
 M.write_failure_terminal(c,RuntimeError('later'))
 assert json.loads((tmp_path/'prov/TERMINAL.json').read_text())['error']=='deadline'

def test_tree_inventory_detects_cache_or_checkpoint_mutation(tmp_path):
 root=tmp_path/'sealed';root.mkdir();p=root/'x.bin';p.write_bytes(b'one');before=M.tree_inventory(root);p.write_bytes(b'two')
 assert M.tree_inventory(root)!=before

def test_native_and_norm_matched_views_are_not_aliased():
 p=np.array([[3.,4.],[1.,0.]],dtype=np.float32);truth=np.array([[6.,8.],[4.,0.]],dtype=np.float32)
 matched,ok=M.base.r5.norm_match(p,truth)
 assert ok.all() and not np.array_equal(p,matched)
 assert np.allclose(np.linalg.norm(matched,axis=1),np.linalg.norm(truth,axis=1))
