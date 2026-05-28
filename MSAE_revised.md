# MSAE.md — Morphological Sparse Autoencoders for Mechanistic Interpretability

## TL;DR
- **Current SAEs are quantitatively broken on the criteria that matter:** Paulo & Belrose (2025) show only ~30% feature overlap between TopK SAEs trained on Llama-3-8B with different seeds; Kantamneni et al. (ICML 2025) show SAE probes underperform plain logistic regression across 113 binary-classification probing tasks in all four difficult regimes; Engels, Riggs & Tegmark (2024) show ~half of the SAE error vector and >90% of its squared norm are linearly predictable "dark matter"; Chanin et al. (2024) document feature absorption as a structural pathology of any single-dictionary L1/TopK SAE on hierarchical features.
- **MSAE = activations decomposed into K parallel components, each sparse in a *different* mutually-incoherent dictionary**, lifting the Donoho–Huo / Donoho–Elad / Elad–Bruckstein / McCoy–Tropp theory of Morphological Component Analysis from images into language-model activations. This converts the "one dictionary tries to do everything" failure mode into a *demixing* problem with provable identifiability so long as the dictionaries' mutual coherence µ(D_i, D_j) is held small.
- **The experimental program is structured as three papers with linear dependencies and clear early-exit decision gates.** Paper 1 establishes the methodological foundation by validating K=2 position-vs-content demixing on Pythia-160M with probe-based ground truth. Paper 2 generalizes to K=3 with a dark-matter-absorbing dense branch and evaluates against the full SAEBench suite on Gemma-2-2B layer 12 (the SAEBench reference site). Paper 3 introduces structured atomic primitives (subspace-valued atoms, multi-resolution branches) to address documented failure modes that linear-component decomposition alone cannot fix. Each paper has a single declarative claim, internal baselines and ablations that close the obvious counterarguments, and pre-declared success thresholds that gate publication and progression to subsequent papers.

---

# Part I: Shared Foundations

This section consolidates the diagnosis, theory, baselines, evaluation protocol, model details, adjacent prior work, and implementation tools that all three papers rest on. None of the content in Part I is specific to one paper; each paper draws on whichever subset it needs and references this part rather than duplicating it.

## 1. The diagnosis: why a *single* sparse dictionary cannot be the right tool

SAEs assume an activation x ∈ ℝᵈ admits a representation x ≈ Dα with α ∈ ℝᵐ sparse in a *single* learned overcomplete D. The 2024–2025 literature has falsified each pillar of that assumption:

**Feature absorption (Chanin, Wilken-Smith, Dulka, Bhatnagar, Bloom 2024, arXiv:2409.14507).** Whenever the underlying features form a hierarchy (e.g. "starts-with-S" ⊃ "short"), L1/TopK SAEs merge the parent direction into a child latent, producing "gerrymandered" latents that fire on ~95% of instances and silently fail on the rest. The first-letter spelling task is operationalised as: for each letter, fit a one-vs-rest logistic-regression probe on residual-stream activations; identify k-sparse "main feature-split latents" by adding latents whose inclusion improves k-sparse probe F1 by ≥ τ_fs = 0.03; on tokens the LR probe gets right but all main latents miss, run integrated-gradients ablation on SAE latents; declare absorption when the top-ablation-magnitude latent has cosine similarity ≥ 0.025 with the LR probe direction AND its ablation magnitude exceeds the second-place latent by ≥ 1.0. Across all Gemma-Scope 16k and 65k residual SAEs, absorption rises with width and falls in L0 (sparser SAEs absorb more).

**Seed instability (Paulo & Belrose 2025, arXiv:2501.16615).** Train TopK SAEs on identical data, identical batch order, only varying the init seed. Match latents across seeds by greedy Hungarian assignment with the criterion that a latent is "shared" iff cosine similarity ≥ 0.7 on *both* encoder and decoder weights. Headline numbers: **131K-latent TopK SAE on a Llama-3-8B feedforward block — only 30% of latents shared across seeds**; TopK is *more* seed-dependent than L1-ReLU at matched sparsity. The companion EleutherAI blog (Paulo & Belrose, Dec 12 2024) reports that **a 32,768-latent TopK SAE trained on the MLP at layer 6 of Pythia-160M has exactly 53% of latents shared across two independently trained seeds**. Auto-interp scores of the "orphan" (unshared) latents average 0.72, i.e. they are real and interpretable; the SAE is just sampling from a degenerate family of solutions.

**Non-canonical / non-atomic features (Leask, Bussmann, Pearce, Bloom, Tigges, Al Moubayed, Sharkey, Nanda, ICLR 2025; arXiv:2502.04878).** Meta-SAEs trained on the *decoder rows* of a primary SAE recover sub-latents that compose to form the original directions ("Einstein → scientist + Germany + famous + starts-with-E"). Across width sweeps, larger SAEs do not converge to a unique atomic dictionary; one SAE's "atoms" decompose into another's, and SAE stitching exposes that smaller SAEs are simply incomplete.

**Multi-dimensional features (Engels, Liao, Michaud, Gurnee, Tegmark, ICLR 2025; arXiv:2405.14860).** Days-of-the-week, months, and years-of-the-20th-century are *circular*, irreducible 2-D representations in GPT-2-small layer 7, Mistral-7B and Llama-3-8B. The discovery pipeline clusters SAE decoder vectors by mixed cosine + Jaccard similarity, then evaluates irreducibility via a Separability Index and an ε-Mixture Index; causal interventions on the recovered circles drive modular-arithmetic behaviour on day/month tasks. By construction a one-direction-per-feature SAE cannot represent these without splitting them into shards.

**SAE probes lose to logistic regression (Kantamneni, Engels, Rajamanoharan, Tegmark, Nanda, ICML 2025; arXiv:2502.16681).** 113 binary classification datasets (front-page-vs-inside NYT headlines, MNLI entailment, NYC borough identification, AI-vs-human text, athlete-sport categorisation, Twitter emotion …; prompts 5–1024 tokens). SAE probes built as: encode last-token activation X^l_{−1} through Gemma-Scope JumpReLU SAE for Gemma-2-9B (layer 20) or Llama-Scope TopK SAE for Llama-3.1-8B, pick top-k latents by mean absolute difference between classes (k ∈ {16, 128}), train L1-regularised LR on those latents. Across all four hard regimes — data scarcity, class imbalance, label noise, covariate shift — **mean test AUC of SAE probes is below that of plain logistic regression on raw activations**. The "Quiver of Arrows" robustness test (add SAE probes to a baseline toolkit and pick best by validation AUC) does not raise the toolkit's test AUC. This was a primary motivator for DeepMind's blog "Negative Results for Sparse Autoencoders On Downstream Tasks and Deprioritising SAE Research (Mechanistic Interpretability Team Progress Update)" (Smith, Rajamanoharan, Conmy, McDougall, Kramár, Lieberum, Shah, Nanda, deepmindsafetyresearch.medium.com, 26 Mar 2025), whose TL;DR reads verbatim: "we do not think that SAEs will be a game-changer for interpretability, and speculate that the field is over-invested in them."

**Dark matter (Engels, Riggs/Smith, Tegmark, 2024; arXiv:2410.14670).** About half of the SAE error vector and **>90% of its squared norm** can be *linearly* predicted from the input activation itself — i.e. the residual is not "yet-to-be-learned features in superposition" but a structurally different component. Gradient-pursuit at inference time barely dents it; only adding linear transformations of earlier-layer SAE outputs reduces it. This is empirical evidence that activations live in a *direct sum* of qualitatively different geometric components, exactly the setting MCA was invented for.

Taken together these results are not five unrelated bugs. They are the signature of trying to capture a sum of geometrically heterogeneous components — sparse-in-one-basis features, manifold-valued features, multi-dimensional features, and a dense bias drift — with a single learned overcomplete dictionary and a single sparsity penalty. The DeepMind safety-team pivot away from SAEs (26 Mar 2025) reads naturally as the field hitting that ceiling.

## 2. The proposal: Morphological SAEs

MCA (Starck, Moudden, Bobin, Elad, Donoho, SPIE 2005; Bobin, Starck, Fadili, Moudden, Donoho, IEEE TIP 2007) decomposes a signal y = Σ_k Φ_k α_k where each Φ_k is a *different* dictionary in which one morphological component is sparse and the others are not. We propose the strict analogue for a transformer activation x ∈ ℝᵈ at a chosen hook:

  x ≈ Σ_{k=1..K} D_k σ_k(W_k x + b_k) + r

where the K branches have *separate, mutually-incoherent* dictionaries D_k ∈ ℝ^{d × m_k} and possibly *different* activation/sparsity regimes σ_k (some TopK with small k, some JumpReLU, possibly one low-rank/dense branch for the linearly-predictable "dark matter"). The training loss combines a reconstruction term, per-branch sparsity, and an explicit *mutual-coherence regulariser* between dictionaries.

The full K=3 instantiation, which becomes the centerpiece of Paper 2, comprises:
- **D_1: TopK k ≈ 32 over m_1 = 65k atoms** — captures sparse, monosemantic "linear-representation-hypothesis" features.
- **D_2: JumpReLU with thresholds θ initialised at 0.001 and bandwidth ε = 0.001 over m_2 = 16k atoms** — captures rarer, higher-magnitude features.
- **D_3: low-rank dense branch (rank r ≤ 64)** — captures the Engels-Riggs-Tegmark "linear dark matter" component explicitly, instead of letting it pollute the L0 budget of D_1 and D_2.

Paper 3 introduces additional structured branches:
- **D_subspace**: subspace-valued atoms (each atom is a low-rank matrix rather than a vector) to absorb Engels-style multi-dimensional features such as circular days-of-the-week.
- **D_multiscale**: nested-sparsity branches following the Matryoshka template but inside the MSAE framework, with different m_k operating at different abstraction scales.

Paper 1 begins at the simpler end of this design space with K=2 and a single declarative split (position vs. content), validated against probe ground truth.

## 3. Identifiability: the theory we are leveraging

This is what makes MSAE different from "just train two SAEs in parallel." The classical compressed-sensing / MCA chain gives precise inequalities under which the demixing is unique and ℓ1-recoverable. The theorems below are referenced across all three papers; each paper draws on the subset most relevant to its claim.

**Mutual coherence (Donoho–Huo 2001, IEEE TIT 47).** For dictionaries D_1, D_2 with unit-norm columns define µ = µ(D_1, D_2) := max_{i, j} |⟨d_{1,i}, d_{2,j}⟩|. The original 2-orthobasis result: if x = D_1 α_1 + D_2 α_2 with ‖α_1‖_0 + ‖α_2‖_0 < (√2 − ½)/µ then ℓ1 minimisation recovers (α_1, α_2) uniquely. **This is the foundational bound for Paper 1**, where the cleanest empirical instantiation is position-vs-content because position via RoPE is encoded in a Fourier-like basis and content in a spike-like token-aligned basis — the canonical Donoho-Huo setup with µ ≈ 1/√n.

**Elad–Bruckstein 2002 (IEEE TIT 48).** Sharpens the 2-orthobasis bound; recovery thresholds in terms of concentration of 1-norm / 2-norm (Riegler & Bölcskei survey, arXiv:1811.03996).

**Donoho–Elad 2003 (PNAS 100(5):2197).** Extends to general redundant dictionaries D = [D_1 | D_2 | … | D_K]: any signal with sparse representation satisfying ‖α‖_0 < ½(1 + 1/µ(D)) is the *unique* sparsest representation and is recovered by basis pursuit. **This is the bound Paper 2 instantiates for K-component MSAE.**

**Babel function (Tropp 2004).** µ_1(p) = max_Λ Σ_{j ∈ Λ, |Λ| = p} max_{i ≠ j} |⟨d_i, d_j⟩| — a tighter average-case coherence we monitor at training time; recovery requires µ_1(p − 1) + µ_1(p) < 1.

**McCoy–Tropp convex demixing (FoCM 2014; Amelunxen-Lotz-McCoy-Tropp, Information & Inference 3(3):224–294, 2014, arXiv:1303.6672).** The phase transition for demixing z = x_0 + Uy_0 (e.g. sparse + rotated sparse, or low-rank + sparse) under random rotation U is *sharp* and located by the **statistical dimension** δ(C) of the descent cones C_f(x_0), C_g(y_0): demixing succeeds whp ⇔ δ(C_f) + δ(C_g) < d. We compute δ_f, δ_g empirically for the per-branch atomic norms and use them as a *design constraint* on per-branch sparsity targets (so total statistical dimension stays comfortably below d). **Used in Paper 1 for theoretical phase-diagram overlay and in Paper 2 for K=3 sizing.**

**Atomic-norm framework (Chandrasekaran-Recht-Parrilo-Willsky 2012).** Each branch's regulariser is naturally written as the gauge of a chosen atomic set 𝒜_k; combining branches by sum of gauges is the canonical convex relaxation of "multi-structure" recovery. **This is the theoretical foundation for Paper 3's structured branches** (nuclear-norm gauges for subspace atoms, group-LASSO gauges for nested sparsity).

**Spielman-Wang-Wright 2012 (COLT, arXiv:1206.5882): ER-SpUD.** For square dictionaries with Bernoulli-Gaussian sparse coefficients, O(n log n) samples suffice for unique recovery, and a polynomial-time ℓ1-based alternating algorithm provably recovers the dictionary up to permutation/sign — the first provable dictionary-learning algorithm. **Arora-Ge-Moitra 2014** ("New Algorithms for Learning Incoherent and Overcomplete Dictionaries", arXiv:1308.6273) extends this to overcomplete µ-incoherent dictionaries supporting k ≤ c · min(√n / (µ log n), m^{1/2 − η}) sparsity. These are the theorems that license calling MSAE training a *dictionary-recovery* algorithm rather than a heuristic.

**Sun-Qu-Wright 2015** treats complete dictionary recovery as nonconvex optimisation over the sphere and shows benign landscape with O(n³) sample complexity.

Translating to a concrete regulariser, the design implication used in **every paper** is:

  L_inc = Σ_{j<k} λ_inc · ‖D_j^⊤ D_k‖_F² / (m_j m_k)   (Frobenius decorrelation)

or equivalently a soft penalty on µ̂(D_j, D_k) = ‖D_j^⊤ D_k‖_∞, with stochastic estimation by sampling random columns. We also periodically compute µ̂ and the empirical statistical dimension of each branch's descent cone (using the polyhedral cone Monte-Carlo estimator from Amelunxen-Lotz-McCoy-Tropp §6) and adaptively raise λ_inc whenever µ̂ × max_k k_k exceeds the Donoho-Elad uniqueness threshold (1 + 1/µ̂)/2.

## 4. The state-of-the-art baselines all three papers must beat

A single, fully-specified SOTA recipe (Gemma Scope, Lieberum et al. 2024, arXiv:2408.05147) for direct comparison:

| Component | Value |
|---|---|
| Architecture | JumpReLU SAE; W_dec columns unit-norm; W_enc initialised as W_dec^⊤ |
| LR | η = 7 × 10⁻⁵ |
| LR warmup | cosine from 0.1η → η over 1000 steps |
| Optimizer | Adam, (β_1, β_2) = (0, 0.999), ε = 10⁻⁸ |
| Batch size | 4096 |
| Sparsity coefficient λ warmup | linear 0 → λ over 10000 steps |
| JumpReLU bandwidth | ε = 0.001 (with unit-MS-norm activations) |
| Threshold init | θ = (0.001)^M |
| Activation norm | unit mean-squared-norm; subtract b_dec pre-encoder during training, fold post-hoc |
| Widths | {2¹⁴, 2¹⁵, 2¹⁶, 2¹⁷, 2¹⁸, 2¹⁹, 2²⁰} |
| Tokens | 4B for 16K-width; 8B default; 16B for 1M-width |
| Sites | residual, MLP-out, attn-out (pre-W_O concat) on every layer of Gemma-2 2B/9B; layers 10/22/34 of 27B |
| Precision | fp32 training |

For the OpenAI TopK recipe (Gao et al. 2024, arXiv:2406.04093) as a second baseline:

| Component | Value |
|---|---|
| Activation | TopK (k ∈ {32, 64, 128, 256, 512}, default k = 32); also Multi-TopK with L_total = L(k) + L(4k)/8 |
| Optimizer | Adam, β_1 = 0.9, β_2 = 0.999, ε = 6.25 × 10⁻¹⁰; constant LR (∝ 1/√n) |
| EMA | weight EMA coefficient 0.999, bias-corrected |
| b_pre init | geometric median of a sample of data points |
| Encoder init | parallel to (transpose of) decoder; for TopK, encoder magnitude scaled to match input magnitude |
| Decoder columns | renormalised to unit norm after every step; gradient parallel to decoder column projected out before Adam |
| Dead-latent threshold | no activation for 10M tokens |
| AuxK auxiliary loss | top-k_aux dead latents (typically 512); coefficient α = 1/32; zero on NaN |
| Batch size | 131072 tokens |
| Tokens | GPT-2 small ReLU baselines: 8 epochs × 6.4B tokens; flagship: 16M-latent SAE on GPT-4, 40B tokens |
| Context length | 64 tokens |
| Pre-processing | subtract mean over d_model dim, normalize to unit norm |
| Layer | layer 8 of GPT-2 small (post-MLP residual, ¾ through); ⅚ through for GPT-4-class |
| Dead-latent fraction at 16M | 7% with AuxK + tied init |

Joint scaling law (TopK, GPT-4 fit) — useful as an upper-bound prediction for what additional capacity buys:

  L(n, k) = exp(α + β_k log k + β_n log n + γ log k log n) + exp(ζ + η log k)
  with (α, β_k, β_n, γ, ζ, η) = (−0.50, 0.26, −0.017, −0.042, −1.32, −0.085).

## 5. SAEBench: the evaluation Paper 2 must run end-to-end

SAEBench (Karvonen, Rager, Lin, Tigges, Bloom, Chanin, Lau, Farrell, McDougall, Ayonrinde, Till, Wearden, Conmy, Marks, Nanda 2025, ICML; arXiv:2503.09532) consolidates eight metric families. Numbers below are from the paper.

Reference model and site for headline results: **Gemma-2-2B, layer 12 residual stream**; secondary: Pythia-160M layer 8. In-house SAE widths in the benchmark suite: 4K, 16K, 65K. Per-SAE L0 targets swept: {20, 40, 80, 160, 320, 640}. Per-evaluation compute on RTX-3090: ≈ 107 min one-time setup + ≈ 65 min per SAE for the full suite.

In-house SAE training hyperparameters used to produce the comparison suite (Karvonen et al. 2025, Table 3): The Pile, context 1024, batch 2048, LR 3 × 10⁻⁴ with 1000-step LR warmup, 5000-step sparsity-penalty warmup, last-20% LR decay to 0, **500M tokens**, decoder init = transpose of encoder, unit-MS-norm activation pre-processing.

The 8 metric families:

1. **Core reconstruction and sparsity metrics**: Loss Recovered (CE-delta) = (H* − H_0) / (H_orig − H_0), with H* the CE when SAE-reconstructed activations are spliced back and H_0 the CE under zero-ablation; reported alongside L0 (mean number of active latents per token), KL, and FVU.
2. **Feature Absorption**: Chanin first-letter task extended to all layers; introduces partial-absorption and multi-latent absorption variants. Headline finding (Karvonen et al., 2025): **"Matryoshka Batch TopK SAEs perform best on concept detection and feature disentanglement tasks, especially in the typical L0 range of 40–200 (5 of 8 metrics)."**
3. **SCR — Spurious Correlation Removal** (automated SHIFT, after Marks et al.): train biased linear probe (gender + profession from Bias-in-Bios, etc.); pick top-K SAE latents by absolute attribution; zero-ablate; score S_SHIFT = (A_ablated − A_baseline) / (A_oracle − A_baseline). Class pairs (Bias-in-Bios): Professor/Nurse, Architect/Journalist, Surgeon/Psychologist, Attorney/Teacher. (Amazon reviews): Books / CDs-and-Vinyl, Software / Electronics, Pet-Supplies / Office-Products, Industrial-and-Scientific / Toys-and-Games. Main report at K = 20; sweep K ∈ {5, 10, 20, 50, 100, 500}.
4. **TPP — Targeted Probe Perturbation**: generalises SCR to multi-class; classes = {Accountant, Architect, Attorney, Dentist, Filmmaker} (Bias-in-Bios) and {Toys-and-Games, Cell-Phones-and-Accessories, Industrial-and-Scientific, Musical-Instruments, Electronics} (Amazon). Score = mean_{i = j}(A_{i, j} − A_j) − mean_{i ≠ j}(A_{i, j} − A_j).
5. **Sparse Probing**: top-k latents (k ∈ {1, 2, 5}; headline at k = 1) chosen by maximum mean-difference; LR probe; 4000 train / 1000 test per task; 128-token left-truncation; mean pooling. 35 binary tasks over 5 datasets: bias_in_bios (profession), Amazon Reviews (category + sentiment), Europarl (language ID), GitHub (programming language), AG News (topic).
6. **RAVEL** (attribute–value disentanglement, Huang et al. 2024): cities (Country / Continent / Language) and Nobel laureates (Country-of-birth / Field / Gender); learn an MDBM mask over SAE latents (7000 training examples, 50/50 cause-vs-isolation split, 2 epochs, LR 10⁻³, 3000 eval); score = mean(Cause, Isolation). Jointly-trained MDAS + MDBM skyline = 0.87.
7. **Automated Interpretability**: gpt-4o-mini judge, detection-score style (Paulo et al. 2024); 1000 non-dead latents per SAE; test per latent = 10 random + 2 max-activating + 2 importance-weighted sequences.
8. **Unlearning** (Farrell et al.): WMDP-bio forget set, WikiText retain set; clamp selected SAE features to large negative values when active; sweep retain_threshold ∈ [0.001, 0.01], n_features ∈ {10, 20}, negative multiplier ∈ {25, 50, 100, 200}. Filter for MMLU subsets (High-School-US-History, College-CS, High-School-Geography, Human-Aging) where MMLU ≥ 0.99, then minimise WMDP-bio accuracy. 1024 sequences × 1024 tokens per split.

This is the bar Paper 2 has to clear, especially Matryoshka's lead at L0 ≈ 40–200.

## 6. Models and activations

- **GPT-2 small** (124M, 12 layers, d_model = 768): residual-stream layer 8 post-MLP is the OpenAI default site.
- **Pythia-70M / 160M / 410M / 2.8B**: trained on the Pile; sparsify-library / EleutherAI SAEs use Pile residual-stream activations as in Paulo & Belrose. **Pythia-160M layer 3 is the Paper 1 reference site for K=2 position-vs-content, with layer 4 as fallback** (early/mid depth where position information is still strongly represented before deeper mixing). SAEBench secondary site is Pythia-160M layer 8.
- **TinyStories** models (Eldan & Li): useful for fast iteration on identifiability ablations because the underlying lexical/syntactic feature set is small.
- **Gemma-2-2B / 9B / 27B**: Gemma-Scope provides JumpReLU SAEs at every layer/site; **layer 12 residual on 2B is the SAEBench reference and the Paper 2 main empirical site**. Lieberum et al.: SAEs at widths 16K, 32K, 65K, 131K, 262K, 524K, 1M.
- **Llama-3-8B / 3.1-8B**: Llama-Scope (He et al. 2024) provides TopK SAEs used by Kantamneni et al.; layer 20 is the canonical probing site.

Standard pre-training corpora: The Pile (EleutherAI), OpenWebText, RedPajama, FineWeb (HuggingFace; used by recent HierarchicalTopK / Bussmann work on Gemma-2-2B with 1B-token sub-samples).

## 7. Adjacent architectures all papers must benchmark against

- **Matryoshka SAEs** (Bussmann, Nabeshima, Karvonen, Nanda 2025, arXiv:2503.17547). Architecture: simultaneously train K nested sub-dictionaries of sizes m_1 < m_2 < … < m_K (each later sub-SAE has access to its own latents *plus* all earlier ones). Each sub-SAE is required to independently reconstruct x. With BatchTopK activation. Loss = Σ_k w_k ‖x − x̂_k‖² over the nested reconstructions. Headline: dramatically lower absorption and lower decoder-cosine-similarity (less feature composition) at modest reconstruction cost. **Currently the SAEBench winner at L0 ≈ 40–200**, but with a measurable tradeoff: per Bussmann et al. Figure 1, Matryoshka has "higher variance unexplained" at L0 = 40 vs. standard BatchTopK; SAEBench states Matryoshka "perform[s] worse than TopK and BatchTopK on the sparsity-fidelity frontier" (no single percentage gap reported). **This is the primary baseline for Paper 2 (matched-L0 head-to-head) and the comparison architecture for Paper 3 (absorption metric on hierarchical features).**
- **Switch SAEs** (Mudide, Engels, Michaud, Tegmark, Schroeder de Witt 2024, arXiv:2410.08201). 8-expert mixture-of-SAE routing; encoder features t-SNE-cluster by expert.
- **End-to-end SAEs** (Braun et al. 2024). Train to minimise downstream CE-loss change rather than reconstruction MSE — different objective; recent results (arXiv:2503.17272) show short e2e finetuning improves SAEBench mixed.
- **Meta-SAEs** (Bussmann, Pearce, Leask, Bloom, Sharkey, Nanda Aug 2024). SAE-on-the-decoder-of-an-SAE; the canonical demonstration of non-atomic latents.
- **BatchTopK** (Bussmann 2024, arXiv:2412.06410). TopK across the *batch* rather than per-token; gives adaptive per-token compute. Used inside Matryoshka.
- **HierarchicalTopK** ("Train One Sparse Autoencoder Across Multiple Sparsity Budgets to Preserve Interpretability and Accuracy", May 2025, arXiv:2505.24473). Single SAE that matches or surpasses separately trained BatchTopK / TopK SAEs **when interpolating ℓ0 ≤ 128** (Figure 3 of that paper); trained on Gemma-2-2B layer 12 with d_dict = 65,536 on a 1B-token FineWeb sub-sample.
- **Anthropic Circuit Tracing / Cross-Layer Transcoders** (Ameisen, Lindsey, Pearce, Gurnee, Turner, Chen, Citro et al., Mar 2025; transformer-circuits.pub/2025/attribution-graphs/methods.html and biology.html). CLTs replace MLPs with sparse cross-layer transcoders, then trace attribution graphs through them. Open-source re-implementations (decoderesearch/circuit-tracer, EleutherAI Attribute, Goodfire) now support Gemma-2-2B, Llama-3.1-1B, Qwen3-4B. **The downstream consumer of better features; Paper 3 integrates MSAE features into this pipeline for its mechanistic case studies.**

## 8. Multi-dictionary sparse coding prior art (image processing → ML adaptation)

- **MCA / MMCA** (Starck-Moudden-Bobin-Elad-Donoho 2005; Bobin-Starck-Fadili-Moudden-Donoho 2007). Iterative thresholding with a *decreasing* threshold (a precursor to JumpReLU): at iteration t, for each component k, residual = y − Σ_{j ≠ k} Φ_j α_j; α_k ← S_{λ_t}(Φ_k^⊤ residual). Threshold linearly decays to zero — analogous to a sparsity-coefficient warm-down. Convergence shown to be drastically faster when dictionaries are mutually incoherent.
- **Curvelet + wavelet + DCT triples** as canonical MCA dictionaries — the spiritual ancestor of our "one branch per feature geometry" design.
- **K-SVD** (Aharon-Elad-Bruckstein 2006), online dictionary learning (Mairal-Bach-Ponce-Sapiro 2010), MOD — all natural baselines for an MSAE-style branch.
- **Sparse Subspace Clustering / Low-Rank Representation** (Elhamifar-Vidal 2013; Liu-Lin-Yu 2010) — relevant if some branches should be union-of-subspaces rather than sparse-in-dictionary; **directly motivates Paper 3's D_subspace branch design**.
- **RPCA** (Candès-Li-Ma-Wright 2011, JACM) and **Tensor RPCA** — the prototype "low-rank + sparse" demixing that the McCoy-Tropp phase-transition theory was designed to analyse. **Direct theoretical justification for Paper 2's D_3 dense low-rank branch.**
- **Convolutional sparse coding** with multiple kernels (Heide-Heidrich-Wetzstein 2015) — relevant if any branch operates on token-window patches rather than single tokens.

## 9. Implementation frameworks (shared across all papers)

- **SAELens** (Bloom & Chanin) — the canonical training pipeline; supports JumpReLU, TopK, BatchTopK, Gated, Matryoshka; integrates HookedTransformer activation streaming, decoder-norm unit-projection, AuxK dead-latent revival, activation buffering, neuronpedia upload.
- **TransformerLens** (Nanda et al.) — primary tool for residual-stream / MLP-out / attn-out hook collection.
- **nnsight** (NDIF, Marks et al.) — intervention infrastructure used for sparse-feature-circuit experiments and SHIFT/SCR.
- **dictionary_learning** (Marks et al.) — the original SAE training library; still used for sparse-feature-circuits and SHIFT replication.
- **sparsify** (EleutherAI / Belrose) — the library used in Paulo & Belrose; reproduce seed-stability experiments here.
- **sae_spelling** (Chanin et al., github.com/lasr-spelling) — feature-absorption metric reference implementation.
- **SAEBench** (github.com/adamkarvonen/SAEBench) — the eight-metric evaluation harness.

---

# Part II: The Three-Paper Experimental Program

The program comprises three papers with linear dependencies. Paper 2 does not begin until Paper 1's headline thresholds are met. Paper 3 does not begin until Paper 2's headline thresholds are met. Each paper has its own claim, internal experiments, and pre-declared publication criteria.

## Paper 1: "Morphological Sparse Autoencoders — Provable Demixing of Position and Content in Transformer Activations"

### 1.1 Single declarative claim

A multi-dictionary sparse autoencoder with enforced mutual incoherence can recover a planted morphological decomposition of transformer activations. We demonstrate this on the position-vs-content split, where ground truth is verifiable via independent probes, and show that the recovery (a) is consistent with the Donoho-Huo / McCoy-Tropp identifiability theory, (b) is more stable across random seeds than single-dictionary SAEs, and (c) is not reducible to either branch heterogeneity or post-hoc clustering of standard SAE latents.

### 1.2 Why position-vs-content is the right starting split

Position vs content has three properties that no other candidate split (syntax-vs-semantics, attention-vs-MLP, high-vs-low frequency) has all at once:
- **Known generating mechanism.** Position is injected by RoPE (or sinusoidal / learned embeddings) at a known site and propagates through the residual stream in a partially-traceable way.
- **Verifiable ground truth.** Linear probes for token position and token identity are standard and high-fidelity at early layers.
- **Canonical theoretical fit.** RoPE encodes position via Fourier-like rotations and content via approximately spike-aligned token embeddings. The mutual coherence of Fourier and spike bases is exactly 1/√n — the canonical Donoho-Huo example. The classical theorem applies to its native problem, not by analogy.

Syntax-vs-semantics is famously slippery at the activation level (Tenney et al.'s "BERT Rediscovers the Classical NLP Pipeline" shows layered but co-varying syntax/semantics) and would produce ambiguous results that confound the methodological claim.

### 1.3 Architecture

Two parallel branches operating on Pythia-160M layer 3 residual-stream activations (d_model = 768), with layer 4 kept as fallback:

- **D_position**: m_pos = 8k atoms; activation = TopK with k_pos = 8 (position should be low-dimensional in a transformer that uses RoPE — the rotation lives in a small number of frequency channels). Decoder columns unit-norm; encoder initialised as the transpose of the decoder.
- **D_content**: m_content = 32k atoms; activation = TopK with k_content = 24. Same unit-norm decoder convention.

Initial b_pre is the geometric median of a sample of activations. Activations are pre-processed to unit MS-norm.

### 1.4 Training recipe

Inheriting the Gemma-Scope convention (Section 4) adapted to Pythia-160M scale: Adam (β_1, β_2) = (0, 0.999), ε = 10⁻⁸, LR = 7 × 10⁻⁵ with cosine warmup 0.1η → η over 1000 steps, batch size 4096, decoder columns renormalised after every step with gradient-parallel-to-decoder projected out.

Loss:

  L_total = ‖x − D_pos σ_pos(α_pos) − D_content σ_content(α_content)‖² + λ_inc ‖D_pos^⊤ D_content‖_F² / (m_pos · m_content) + α_AuxK L_AuxK

where λ_inc is warmed linearly from 0 to its target value over 10,000 steps. Dead-latent revival: 10M-token threshold; revive via AuxK with top-512 dead latents and coefficient α_AuxK = 1/32.

Tokens: 8B from The Pile (matching Gemma-Scope default at width 65k; Pythia's d_model is smaller but the 8B target is conservative).

### 1.5 The synthetic identifiability sandbox

Before any neural-network confound enters, demonstrate that the convex demixing theory works on data where ground truth is known by construction. Generate y = D_1^* α_1^* + D_2^* α_2^* with:
- Two random orthogonal D_k^* ∈ ℝ^{n × n} at ambient dimensions n ∈ {64, 256, 1024}.
- Bernoulli-Gaussian sparse coefficients with sparsities k_1, k_2 spanning the Donoho-Elad regime and beyond.

Run alternating ℓ1 minimisation with the same incoherence regularizer. Recover phase-diagram of recovery success vs (k_1 + k_2, µ̂(D_1, D_2), n), overlaid on the McCoy-Tropp theoretical phase curve computed via the Amelunxen-Lotz-McCoy-Tropp statistical-dimension formulas for the ℓ1 descent cone. Add an "low-rank + sparse" planted-structure variant (D_2 replaced by a planted low-rank component) to establish that the framework extends to mixed atomic norms — a stepping stone to Paper 2's K=3 design and Paper 3's structured branches.

This is two figures and answers "does the theory work at all before we touch a neural net."

### 1.5B Raw-activation separability pilot (no SAE, de-risking prerequisite)

Before any MSAE training, test whether Pythia-160M layer-4 residual activations already admit an approximate *linear* separation between position-predictive and content-predictive structure. This addresses the core theory-to-practice risk directly.

Protocol:
- Train linear probes on raw activations only: `P_pos: x -> position bucket` and `P_tok: x -> top-1024 token bucket`.
- Build probe-derived subspaces from probe weight matrices: `S_pos` from the top singular vectors of `P_pos`, `S_tok` from the top singular vectors of `P_tok`; sweep subspace rank `r in {8, 16, 32}`.
- Evaluate probe transfer under projection: `Proj_{S_pos}(x)`, `Proj_{S_pos^\perp}(x)`, `Proj_{S_tok}(x)`, `Proj_{S_tok^\perp}(x)`.
- Quantify geometric overlap via principal angles between `S_pos` and `S_tok`, and cross-projection energy (`||Proj_{S_pos} Proj_{S_tok}||_F`).

Minimum pass thresholds (required before committing the full 8B-token Paper 1 run):
1. Position AUC on `Proj_{S_pos}(x)` is high (`>= 0.90`) while position AUC on `Proj_{S_pos^\perp}(x)` is substantially lower (`<= 0.70`).
2. Token top-1 on `Proj_{S_tok}(x)` retains most raw performance (`>= 0.75 * raw`) while token top-1 on `Proj_{S_tok^\perp}(x)` is substantially lower (`<= 0.60 * raw`).
3. Cross-talk reduction: projecting to `S_pos` reduces token-identity accuracy by `>= 25%` relative to raw; projecting to `S_tok` reduces position AUC by `>= 25%` relative to raw.
4. At least one `(r_pos, r_tok)` setting yields median principal angle `>= 45` degrees between `S_pos` and `S_tok`.

If this pilot fails, Paper 1 does not proceed unchanged: we either move to an earlier layer (e.g., layer 2) or narrow the claim to "weak/partial separability" before running any large-scale MSAE training.

### 1.6 The K=2 position-vs-content experiment

Train MSAE on Pythia-160M layer 3 residual stream (layer 4 fallback) with the architecture and recipe in §1.3–1.4, using the 8B-token The Pile training budget specified above. Separately collect a 100M-token OpenWebText holdout activation set (filtering BOS/EOS/padding, shuffled in 10⁶-element buckets) for probe training/evaluation and initialization diagnostics.

Initialization variants (three settings, head-to-head):
- Random Gaussian init for both branches (baseline).
- D_position initialised from sinusoidal/Fourier atoms matching RoPE's frequency channels; D_content random Gaussian.
- PCA-conditioned init: D_position from PCs of position-conditioned activations (activations of the same token across different positions), D_content from PCs of content-conditioned activations.

### 1.7 Four-probe validation (the empirical core)

After training, run four independent probes whose pass/fail is pre-declared and not adjustable post-hoc.

**Probe 1: Position prediction.** Train a multiclass linear classifier to predict token position (buckets of size 1 over positions 0–1023) from each of: raw activations (baseline), D_position activations, D_content activations, K=1 SAE activations. Held-out test set. Headline metric: classification AUC. Expected pattern: D_position AUC ≥ raw AUC ≥ K=1 SAE AUC > D_content AUC ≈ chance.

**Probe 2: Token identity.** Same protocol, predicting top-1024 token bucket. Expected pattern: D_content top-1 ≥ raw ≥ K=1 SAE > D_position ≈ chance.

**Probe 3: Position invariance.** Construct matched pairs (token T at position P_1, token T at position P_2) with |P_1 − P_2| ∈ {8, 32, 128}. Compute cosine similarity of D_position activations within each pair (expect: low) and of D_content activations within each pair (expect: high). Compare to the same statistic computed on raw activations and on K=1 SAE activations.

**Probe 4: Causal intervention.** Clamp D_position atoms to zero during forward pass and re-run on (a) token-level loss tasks (next-token prediction CE), (b) explicit position-dependent tasks (a synthetic relative-position task adapted from the IOI literature). Symmetric for D_content clamping. Expected pattern: D_position clamp preserves (a) but destroys (b); D_content clamp the reverse.

### 1.8 Internal baselines and ablations

The two critical baselines that need to be inside this paper (not deferred):

- **K=1 SAE with post-hoc position-vs-content split.** Train a standard JumpReLU SAE at matched total parameter count (m = 40k = m_pos + m_content). Identify each latent's "position score" and "content score" via the same probes used in §1.7. Compare the cleanliness of the post-hoc split to MSAE's enforced split. This rules out the obvious reviewer attack: "the K=1 SAE already finds this decomposition; you're just labelling it post-hoc."
- **K=2 MSAE with no incoherence regularizer (λ_inc = 0).** Train two parallel branches with no decorrelation penalty. If this baseline does as well as the full MSAE, the architectural prior alone is sufficient and the incoherence regularizer is doing no work. This rules out the second obvious reviewer attack: "you've just trained two SAEs in parallel."

Ablations:
- **Incoherence strength sweep**: λ_inc ∈ {0, 10⁻⁴, 10⁻³, 10⁻², 10⁻¹}. Plot µ̂(D_pos, D_content) and each probe metric vs λ_inc.
- **Regularizer warmdown (hysteresis test)**: train to convergence with target λ_inc, then continue finetuning for 1-2B tokens with λ_inc forced to 0. Track µ̂ drift, probe degradation, and branch swapping. This distinguishes stable learned geometry from "regularizer-held" separation.
- **Sparsity allocation**: (k_pos, k_content) ∈ {(4, 28), (8, 24), (16, 16), (24, 8)}. Tests sensitivity to the prior on which branch should be sparser.
- **Initialization**: as in §1.6.
- **Width allocation**: at fixed m_total = 40k, sweep (m_pos, m_content) ∈ {(2k, 38k), (4k, 36k), (8k, 32k), (16k, 24k), (20k, 20k)}.

### 1.9 Seed-stability analysis (addresses Paulo-Belrose)

Train 5 seeds at fixed hyperparameters. Apply the Paulo-Belrose Hungarian-matching protocol: a latent is "shared" iff cosine similarity ≥ 0.7 on *both* encoder and decoder weights. Report fraction of shared latents within each branch (D_pos cross-seed, D_content cross-seed) and across branches (D_pos seed-i vs D_content seed-j, expect: zero overlap). Compare to the Paulo-Belrose Pythia-160M baseline of 53% for K=1 TopK SAE at 32k latents.

The headline number for the seed-stability story: **MSAE per-branch cross-seed overlap should be ≥ 60% — meaningfully above the K=1 baseline.**

### 1.10 Theoretical contribution (in-paper)

A single concentrated theory section connecting Donoho-Huo's spike-Fourier uncertainty principle to the specific RoPE / content geometry of the experiment. The section includes:
- An explicit upper bound on µ(D_pos, D_content) for RoPE-derived position dictionaries and token-embedding-derived content dictionaries.
- Empirical estimates of µ̂ and statistical dimension throughout training, with overlay on the McCoy-Tropp phase curve.
- A discussion of why the deterministic Donoho-Elad bound is sufficient (not necessary) and how to interpret it as a design heuristic rather than a guarantee on the trained model.
- A short subsection adapting Spielman-Wang-Wright-style ER-SpUD guarantees to the two-branch setting under appropriate sparse-coding assumptions — not a full theorem but a stated open conjecture for future work.

### 1.11 One downstream mechanistic case study

To validate that the position-vs-content decomposition has interpretability utility (not just clean probes), reproduce a position-disentangled feature analysis on the indirect-object-identification (IOI) circuit in Pythia-160M's lower layers. Position is a known confound in IOI features; MSAE features should disentangle the positional and content-based contributions to the duplicate-token-head signal.

Pre-declared metrics for this case study (to prevent narrative-only interpretation):
1. **IOI logit-difference retention** under branch-specific clamping: with `D_pos` clamped, IOI logit-difference should drop by `>= 20%`; with `D_content` clamped, drop should be `>= 20%`; and each clamp should differentially affect distinct intervention sets.
2. **Branch-specific causal attribution concentration**: for duplicate-token-head-mediated IOI signal, at least `60%` of position-sensitive attribution mass should route through `D_pos` rather than `D_content`.
3. **Cross-branch leakage bound**: ablating top-k IOI-attributing `D_pos` latents should not reduce content-only control-task performance by more than `5%`, and symmetrically for `D_content` on position-only controls.

This remains a compact section (one figure + one table), but with explicit quantitative claims.

### 1.12 Pre-declared success thresholds for Paper 1 (publication criteria)

A criterion is "met" if all listed conditions hold simultaneously on the headline test split with 5-seed mean. The paper is published if ≥ 4 of the 5 criteria are met.

1. **Position probe AUC on D_position ≥ 0.95** AND **position probe AUC on D_content ≤ 0.55**.
2. **Token-identity top-1 accuracy on D_content ≥ that of raw activations − 1pp** AND **token-identity accuracy on D_position ≤ chance + 5pp**.
3. **Position-invariance cosine similarity gap (D_content − D_position) ≥ 0.4** on matched-token pairs.
4. **Causal intervention**: D_position clamp leaves token-level CE within +2% of baseline AND collapses relative-position task accuracy by ≥ 30pp; D_content clamp the reverse.
5. **Seed stability**: per-branch cross-seed Hungarian-matched overlap ≥ 60% (vs. ≤ 53% for the K=1 TopK baseline) AND mutual coherence µ̂(D_pos, D_content) ≤ 0.1.

Additional robustness criterion (reported separately, claim-strengthening): after the regularizer warmdown ablation in §1.8, µ̂ should not increase by more than `+0.05` absolute and each of the four probe metrics should degrade by no more than `2 pp`. If this criterion fails, the paper is reframed as "incoherence-regularized separation" rather than intrinsic morphological decomposition.

### 1.13 Decision gate: when to write Paper 2

Paper 2 begins as a serious project only if Paper 1 hits ≥ 4 of 5 thresholds. If Paper 1 hits ≤ 2 of 5, the project pivots: the most likely explanation is that activations are not morphologically decomposable in the way MCA assumes, and the next research question is "why not?" — a publishable negative result with theoretical implications. If Paper 1 hits exactly 3 of 5, attempt one round of design iteration on Paper 1 before proceeding.

---

## Paper 2: "Generalized Morphological Sparse Autoencoders — K-Component Decomposition for Mechanistic Interpretability"

### 2.1 Single declarative claim

The position-vs-content demixing result generalizes to K ≥ 3 components capturing structurally heterogeneous signals (sparse-sparse-dense, attention-routed vs MLP-computed), and on the SAEBench benchmark suite the resulting decomposition matches or beats single-dictionary SAEs (Gemma-Scope JumpReLU, BatchTopK, Matryoshka) at matched L0. We additionally narrow the SAE-probe-vs-logistic-regression gap on the Kantamneni 113-task benchmark in at least two of the four difficult regimes.

### 2.2 Architecture: K=3 full instantiation

The full K=3 architecture described in Part I §2:

- **D_1: TopK k = 32 over m_1 = 65k atoms** — captures sparse monosemantic features.
- **D_2: JumpReLU (bandwidth ε = 0.001, threshold init θ = 0.001) over m_2 = 16k atoms** — captures rarer, higher-magnitude features.
- **D_3: dense low-rank branch (rank r ≤ 64)** — captures the Engels-Riggs-Tegmark "linear dark matter" component. Parameterized as D_3 = U V^⊤ with U ∈ ℝ^{d × r}, V ∈ ℝ^{r × d}; the activation is the full rank-r reconstruction U V^⊤ x (no sparsity, no threshold).

All sparse-branch decoder columns are unit-norm constrained; encoders are initialised as the transposes of their decoders; b_pre at the geometric median of a sample of data points.

### 2.3 Training recipe at Gemma-2-2B scale

Gemma-2-2B layer 12 residual stream (the SAEBench reference site). Recipe matches Karvonen et al. 2025 Table 3 for fair comparison: The Pile, context 1024, batch 2048, LR 3 × 10⁻⁴, 1000-step LR warmup, 5000-step sparsity-penalty warmup, last-20% LR decay to 0, **500M tokens**, decoder init as encoder transpose, unit-MS-norm pre-processing.

Loss:

  L_total = ‖x − Σ_k x̂_k‖² + Σ_{k ∈ {1,2}} λ_k S_k(α_k) + λ_inc Σ_{j < k} ‖D_j^⊤ D_k‖_F² / (m_j m_k) + λ_aux L_AuxK

with S_1 the TopK indicator (no penalty), S_2 the L1 with JumpReLU STE gradient (Rajamanoharan et al. 2024 §3), and no sparsity penalty on D_3. The incoherence regularizer applies to all sparse-sparse pairs *and* to sparse-dense pairs (computing ‖D_j^⊤ U‖² so the sparse branches don't collapse into the dense branch's row space). L1 / TopK / JumpReLU coefficients warmed linearly from 0 over 10,000 steps in parallel with λ_inc.

### 2.4 Monitoring during training

- µ̂_{jk} = ‖D_j^⊤ D_k‖_∞ logged every 1,000 steps; target ≤ 0.3 once λ_inc warmup completes.
- Babel function µ_1(p) for the *concatenated* dictionary D = [D_1 | D_2] at p = max-active-per-token, logged every 5,000 steps.
- Per-branch FVU_k and total FVU.
- Empirical statistical dimension of each branch's descent cone, estimated by Amelunxen-Lotz-McCoy-Tropp Monte-Carlo (§6.3 of their paper).
- D_3 rank utilization (effective rank of U V^⊤ via singular-value spectrum) — declares whether the dense branch is actually used or collapses.

### 2.5 K=2 attention-vs-MLP supporting experiment

A second morphological split with different theoretical motivation (architectural rather than signal-theoretic). Train a K=2 MSAE where the two branches operate on attention-output activations vs MLP-output activations at Gemma-2-2B layer 12, using transcoders as the architectural anchor (Dunefsky-Chlenski-Nanda 2024). Validation uses dedicated probes: attention-pattern-prediction probes for D_attn, MLP-input-reconstruction probes for D_mlp. This serves as an internal robustness check that Paper 1's success was not specific to position-vs-content.

### 2.6 Unsupervised K=2 discovery experiment

Train MSAE with random init and only the incoherence regularizer — no specified split. Then ask: what split did the model discover? Run all the probes from Paper 1 (§1.7) on both branches; run additional probes for syntax (POS tagging, dependency parsing depth from Hewitt-Manning structural probes), high-vs-low frequency (mean activation magnitude on common vs rare tokens), and attention-vs-MLP (correlation with transcoder outputs). The branch whose probes peak most strongly defines the discovered split.

This experiment converts the supervised result into a methodological tool. **If the unsupervised split lands on position-vs-content**, we have shown the demixing structure is natural to the activation geometry, not an imposed prior. **If it lands on something else** (e.g., high-vs-low frequency, or attention-vs-MLP), we have learned what *is* morphologically distinct in transformer activations — itself a contribution.

### 2.7 Dark-matter validation for D_3

Direct test of the Engels-Riggs-Tegmark dark-matter hypothesis. Compute:
- FVU contribution attributable to D_3 alone (variance explained by U V^⊤ x).
- Linear predictability of the residual (x − Σ_k x̂_k) from x itself — Engels et al.'s headline diagnostic. **Target: linear predictability ≤ 30%** of squared norm (vs. ≥ 90% for standard JumpReLU SAEs).
- Whether removing D_3 (forcing K=2 sparse + sparse) restores the dark-matter pathology.
- **Matched-rank linear control:** compare D_3 against a rank-matched PCA residual branch (same rank `r`, same training/eval splits). If D_3 only matches PCA, claim is reframed as "low-rank residual correction" rather than a distinct morphological component.
- **Interpretability diagnostics of D_3 row space:** inspect top singular directions of `U V^⊤` and test alignment with known nuisance/global directions (layer-norm direction, mean residual drift, attention-sink-associated directions, high-frequency norm-shift directions). Require reproducible cross-seed alignment patterns to support non-trivial structure claims.

### 2.8 Full SAEBench evaluation

All 8 SAEBench metric families (Part I §5) on Gemma-2-2B layer 12 at matched L0 ∈ {20, 40, 80, 160, 320, 640}. Head-to-head against:
- Gemma-Scope JumpReLU (matching width).
- BatchTopK at matched k.
- Matryoshka BatchTopK (the current SAEBench leader at L0 ≈ 40–200).

Per-metric reporting: mean ± std over 5 seeds. Paired bootstrap (10,000 resamples) over SAEBench tasks for per-metric significance vs each baseline. BH-corrected p-values across the 8 metric families.

### 2.9 The Kantamneni 113-task probing benchmark

The strongest existing negative result for SAEs, applied to MSAE features. Reproduce Kantamneni et al. 2025 (ICML) protocol on Gemma-2-9B layer 20 (their site): 113 binary tasks across the four difficult regimes (data scarcity, class imbalance, label noise, covariate shift). SAE probes built as: encode last-token activation through MSAE, pick top-k latents by mean absolute difference between classes (k ∈ {16, 128}), train L1-regularised LR on those latents. Compare mean test AUC of MSAE probes against:
- Gemma-Scope JumpReLU probes (the Kantamneni-reported number).
- Plain logistic regression on raw activations (the baseline that wins in Kantamneni et al.).

Run the Kantamneni "Quiver of Arrows" robustness test: add MSAE probes to the baseline toolkit and pick best by validation AUC; check whether MSAE raises the toolkit's test AUC.

### 2.10 Internal ablations

- **K sweep**: K ∈ {1 (control = standard SAE), 2, 3, 4, 6}. Watch SAEBench scores and total parameter count. Tests "any K works" and "more is always better" simultaneously.
- **Incoherence sweep**: λ_inc ∈ {0, 10⁻⁴, 10⁻³, 10⁻², 10⁻¹}. Plot µ̂ vs each SAEBench metric.
- **Branch heterogeneity**: K=3 with (TopK k=32, TopK k=32, dense r=64) vs. (TopK k=32, JumpReLU, dense r=64) — tests whether activation-function heterogeneity matters or just architecture-count.
- **Dense-branch ablation**: turn off D_3; verify dark matter reappears in residual.
- **Dense-branch control ablation**: replace learned D_3 with frozen rank-matched PCA branch; compare residual predictability, Loss Recovered, and downstream metrics to the learned D_3 model.
- **Width allocation at fixed total m**: (m_1, m_2, r) ∈ {(99k, 1k, 0), (90k, 10k, 16), (65k, 16k, 64), (50k, 30k, 64), (40k, 40k, 16)}.
- **Decoder-tying**: tied vs untied encoders, with and without gradient-projection trick.

### 2.11 Pre-declared success thresholds for Paper 2

A criterion is "met" if all listed conditions hold simultaneously on the headline test split with 5-seed mean. The paper is published if ≥ 5 of the 7 criteria are met.

1. **Loss Recovered within 0.02 of Gemma-Scope JumpReLU baseline** at matched L0 ∈ {40, 80, 160} (the L0 range where Matryoshka leads SAEBench).
2. **≥ 30% reduction in feature absorption** vs Gemma-Scope JumpReLU at L0 = 80 on the Chanin first-letter task.
3. **TPP and SCR within 1 pp of, or above, Matryoshka** at L0 = 80; **RAVEL Cause+Isolation score above Gemma-Scope JumpReLU** at L0 = 80.
4. **Sparse probing accuracy at k=1 within 1 pp of Matryoshka or better.**
5. **Kantamneni 113-task mean AUC ≥ logistic-regression baseline in ≥ 2 of 4 regimes**.
6. **Dark-matter residual linear-predictability ≤ 30%** (vs. ≥ 90% for standard JumpReLU), confirming D_3 actually absorbs the dense component.
7. **Beyond-PCA value of D_3:** at matched rank, learned D_3 must outperform frozen PCA control by either `>= 5 pp` on residual linear-predictability reduction or `>= 0.01` on Loss Recovered, and should show reproducible (cross-seed) structured singular directions.

### 2.12 Decision gate: when to write Paper 3

Paper 3 begins as a serious project only if Paper 2 hits ≥ 5 of 7 thresholds. If Paper 2 fails on Loss Recovered while winning on the disentanglement metrics (TPP/SCR/RAVEL/Absorption), Paper 2 is still publishable as the new SAEBench leader on disentanglement and Paper 3 proceeds. If Paper 2 fails on disentanglement at competitive reconstruction, the project pivots to either (i) more aggressive incoherence regularisation or (ii) structured atomic primitives — i.e., Paper 3 becomes the rescue plan rather than the extension.

---

## Paper 3: "Beyond Linear Atoms — Structured Branches in Morphological Sparse Autoencoders"

### 3.1 Single declarative claim

Adding architecturally non-linear branches (subspace-valued atoms for multi-dimensional features, multi-resolution sparsity for hierarchical concepts) to the MSAE framework resolves specific documented SAE failure modes — feature absorption on hierarchical concepts, multi-dimensional feature shattering, and multi-resolution feature fragmentation — that K-linear-component decompositions in Paper 2 cannot fix on their own.

### 3.2 The unifying intuition

Some interpretability failures are not about *how many* dictionaries you use but about *what kind* of atomic primitives each dictionary contains. Engels' circular days-of-the-week features need 2-D subspace atoms; Chanin's absorption requires nested-scale atoms; multi-resolution token-window features need shift-equivariant atoms. The MSAE framework accommodates all of these as additional branches with different atomic-norm regularizers — the Chandrasekaran-Recht-Parrilo-Willsky atomic-norm framework (Part I §3) gives this its formal license.

### 3.3 Architecture variants

Two new branch types added to the Paper 2 K=3 backbone:

**D_subspace**: atoms parameterized as low-rank matrices rather than vectors. Each atom A_i ∈ ℝ^{d × r_i} with small r_i ∈ {2, 3, 4}; activations represented as (A_i v_i) with v_i ∈ ℝ^{r_i}; sparsity over "which atom" is on (group-LASSO over atom blocks), and within an active atom v_i is dense and unconstrained. Recovery regularizer: group-LASSO + nuclear norm on the per-atom blocks. Justified by Chandrasekaran-Recht-Parrilo-Willsky's atomic-norm framework for sets of low-rank atoms, and by Sparse Subspace Clustering (Elhamifar-Vidal 2013) as a direct algorithmic precedent.

**D_multiscale**: nested-sparsity branches following the Matryoshka template inside the MSAE framework. K_scale ≥ 3 nested sub-dictionaries D_multiscale^{(s)} for s ∈ {1, …, K_scale} of sizes m^{(1)} < m^{(2)} < … with BatchTopK activation; each sub-SAE required to independently reconstruct its assigned residual. Different from vanilla Matryoshka because (a) it operates inside the MSAE framework alongside D_1, D_2, D_3 with cross-branch incoherence, and (b) the sub-dictionaries are assigned per-resolution rather than just per-width.

### 3.4 Training recipe (Gemma-2-2B layer 12)

Extends Paper 2's recipe: same Gemma-2-2B layer 12 site, same 500M-token budget, same baselines. Additional loss terms for the structured branches:

  L_total = ... [Paper 2 losses] ... + λ_subspace · Σ_i ‖A_i‖_* + λ_multiscale · Σ_s w_s ‖x − Σ_{branches} x̂_branch − x̂_multiscale^{(s)}‖²

where ‖·‖_* is the nuclear norm and w_s the Matryoshka per-resolution weight.

### 3.4B Feasibility pilot and convergence gate (required before full 5-seed matrix)

Because D_subspace learnability is explicitly an open question, Paper 3 begins with a constrained feasibility pilot before committing to the full run matrix.

Pilot design:
- 50M-token run on Gemma-2-2B layer 12, 3 seeds, reduced-width variant of the full K=5 model.
- Same optimizer family and warmups as §3.4, with a narrowed hyperparameter grid for `(λ_subspace, λ_multiscale, λ_inc)`.
- Explicit stability instrumentation: NaN incidence, gradient-norm explosions, dead-block rates in D_subspace, effective-rank collapse, and branch-loss domination.

Pilot pass criteria (all required):
1. At least 2/3 seeds train stably to completion with no unrecoverable divergence.
2. D_subspace activates non-trivially (>= 10% of subspace atoms active at least once per 1M-token window) and does not collapse to zero or duplicate D_3.
3. Preliminary Engels metrics exceed a simple sparse-only baseline on at least one circular feature family (days or months).

If pilot fails, Paper 3 is reframed as an exploratory optimization paper and the full 5-seed ablation matrix is not launched.

### 3.5 Validation: Engels circular features

Direct test on the Engels-Liao-Michaud-Gurnee-Tegmark (ICLR 2025) discovery pipeline. Run the same activation-clustering protocol on MSAE D_subspace atoms instead of standard SAE 1-D features. Headline question: does D_subspace recover days-of-the-week, months, and years-of-the-20th-century as *single* 2-D atoms rather than the 7 / 12 / 100 shards that 1-D SAEs produce?

Metrics:
- **Engels' Separability Index** for each recovered atom.
- **ε-Mixture Index** for each recovered atom.
- **Reconstruction quality** of the embedded circles (how much of the within-circle variance is captured by the atom's 2-D subspace).
- **Causal intervention**: clamping a recovered 2-D atom should drive the modular-arithmetic / day-of-week prediction task as effectively as the Engels-baseline full-layer intervention.

### 3.6 Validation: Chanin absorption on hierarchical features

Direct head-to-head against Matryoshka on the Chanin first-letter task at L0 ∈ {40, 80, 160}. The first-letter task is the cleanest hierarchical-feature absorption benchmark: "starts-with-S" is a parent of "short", and SAEs without scale-aware structure absorb the former into the latter. Matryoshka was specifically designed to fix this; D_multiscale is the MSAE-framework version of the same idea, with the additional incoherence constraint across non-multiscale branches.

Metrics:
- **Absorption rate** at matched L0 (defined per Chanin: top-ablation-magnitude latent has cosine ≥ 0.025 with LR probe, exceeds second-place by ≥ 1.0).
- **Partial-absorption rate** and **multi-latent absorption rate** (Karvonen et al. 2025 extensions).
- **Targeted ablation effect**: removing all "short" latents while preserving "starts-with-S" latents should preserve "starts-with-S" probe accuracy.

### 3.7 Theoretical section on atomic norms

A focused theoretical contribution on atomic norms beyond ℓ1:
- Nuclear-norm gauges for D_subspace atoms.
- Group-LASSO gauges for D_multiscale nested sparsity.
- The Chandrasekaran-Recht-Parrilo-Willsky framework for choosing atomic sets appropriate to a target structure (e.g., when is the natural atomic set a sphere of low-rank matrices vs a finite set of subspaces vs a continuous orbit under a group action?).
- McCoy-Tropp statistical-dimension calculations for the combined K=5 architecture (D_1 sparse + D_2 sparse + D_3 dense + D_subspace + D_multiscale).

### 3.8 Two mechanistic case studies

These serve as the paper's downstream demonstrations.

**Case study 1: Modular-arithmetic / temporal-reasoning circuits.** Engels et al. identified circuits in Mistral 7B and Llama-3-8B that use circular day-of-week / month features for tasks like "what is 3 days after Monday." Re-trace these circuits using MSAE features instead of residual-stream activations, with attribution graphs computed via the Anthropic circuit-tracer library (decoderesearch/circuit-tracer or EleutherAI Attribute). Headline: does the attribution graph using D_subspace atoms produce a cleaner / smaller / more interpretable circuit than the standard SAE-feature attribution graph?

**Case study 2: SHIFT/SCR Bias-in-Bios debiasing intervention.** Reproduce Marks et al.'s SHIFT intervention with MSAE features. The SHIFT pipeline: train a biased classifier (predicts profession given gender-correlated features), identify SAE latents responsible for the bias via attribution, ablate them, measure debiased classifier accuracy on the bias-free oracle. Headline metric: how many MSAE latents (K_top) does one need to identify-and-ablate to reach a target SHIFT score, versus how many standard JumpReLU latents are needed for the same score?

### 3.9 Pre-declared success thresholds for Paper 3

A criterion is "met" if all listed conditions hold simultaneously on the headline test split with 5-seed mean. The paper is published if ≥ 3 of the 4 criteria are met.

1. **D_subspace recovers circular day-of-week feature as a single 2-D atom** with Separability Index ≥ Engels' reported baseline and within-circle variance captured ≥ 80%.
2. **D_multiscale absorption rate ≤ Matryoshka absorption rate** at matched L0 = 80 on the Chanin first-letter task.
3. **Modular-arithmetic attribution graph using D_subspace** is at least as compact (≤ same number of nodes/edges) as the standard SAE-feature graph while preserving the same intervention effects.
4. **SHIFT K_top required** is reduced by ≥ 30% versus standard JumpReLU SAE features at matched bias-removal target.

---

# Part III: Project-Level Concerns

## 10. Compute envelope (refined per paper)

**Paper 1 (Pythia-160M layer 3 primary, layer 4 fallback, K=2, m_total = 40k, 8B tokens):** Single 65k-width JumpReLU on Gemma-2-2B trains in 8B tokens at Gemma-Scope settings. Pythia-160M is ~13× smaller per token; the K=2 architecture is ~1.5× more expensive per token than K=1 (extra encoders are negligible; the dominant cost is activation streaming). Estimate: ~1/8th of one Gemma-2-2B JumpReLU SAE training, so ≈ 4-8 GPU-days on an RTX-4090-class GPU for the headline 5-seed run, plus ~3x that for ablations and the new raw-activation separability/warmdown pilots.

**Paper 2 (Gemma-2-2B layer 12, K=3, 500M tokens):** Matches the SAEBench reference configuration. K=3 is ~1.5-2× the cost of K=1 per token. Single MSAE training run: 500M tokens × ~2 minutes per million tokens at batch 2048 ≈ 17 GPU-hours on an H100. Full L0 sweep × 5 seeds × baselines + ablations: ~150 GPU-days. SAEBench evaluation: 107-minute setup + 65 minutes per SAE on RTX-3090.

**Baseline re-run overhead (explicitly budgeted):** matched-L0 in-house baseline reproduction for Matryoshka / BatchTopK / JumpReLU is expected to add ~80-140 GPU-days total (training + evaluation), because published figure-only frontiers are insufficient for precise numeric comparisons.

**Paper 3 (Gemma-2-2B layer 12, K=5, 500M tokens):** ~2× Paper 2 per training run due to the additional structured branches. Roughly 250 GPU-days total including feasibility pilots, ablations, and case studies.

**Total program**: ≈ 500-700 GPU-days including baseline reproduction overhead and new de-risking pilots.

## 11. Statistical-significance protocol (shared across all papers)

- All headline numbers reported as mean ± std over 5 seeds.
- Paired bootstrap (10,000 resamples) over evaluation tasks for per-metric significance vs each named baseline.
- BH-corrected p-values across the metric families within each paper.
- Pre-registration: before Stage 0 (synthetic identifiability) data collection, the lead author commits the success-threshold table for Paper 1 to a timestamped Git commit. Same for Papers 2 and 3 before their first training run. This protects against motivated-reasoning threshold revision after seeing data.

## 12. What is deliberately not in any of the three papers

A few directions from the original loose-bundling plan don't make it into Papers 1-3, and the rationale for each:

**Scaling to Gemma-2-9B and Llama-3-8B as a separate paper.** This would be a follow-up artifact release analogous to Gemma Scope, accompanied by a short technical report rather than a full research paper. The conceptual contribution at scale is small if the 2B results in Paper 2 are convincing. Defer until after Papers 1-3 are published; consider as part of a future Gemma-Scope-style public artifact release.

**A standalone identifiability theory paper.** Proving multi-dictionary recovery theorems for the MSAE setting under Spielman-Wang-Wright-style assumptions is appealing but probably belongs as the theoretical section inside Paper 1 (§1.10) rather than a separate publication. Pure-theory papers in mech interp do not have a clear venue, and the theorem statement is more useful as motivation in an applied paper than as the main contribution.

**A general K-sweep paper exploring K up to 8 or 16.** The K=2 / K=3 results in Papers 1 and 2 are the load-bearing structure; larger K is an ablation in §2.10, not a story.

**The atomic-norm circuit-discovery direction** (treating circuits as atoms rather than features as atoms) is speculative enough that it should be a follow-up conditional on Paper 1's success, not committed-to in advance.

**Cross-layer / cross-model MSAE.** The crosscoder / cross-layer-transcoder direction (Anthropic 2024-2025) is interesting and orthogonal to MSAE's per-layer demixing; combining the two is a future-work direction noted in Paper 2's discussion section, not its own paper here.

**Time-varying / position-conditioned dictionaries** and **convolutional / shift-equivariant atoms** belong as future-work bullets at the end of Paper 3.

**Inference-optimized deployment variants.** The core papers prioritize representation quality over runtime. Practical acceleration paths (branch pruning, distillation to single-branch surrogates, caching subspace projections, low-rank kernel fusion) are deliberately deferred, but we will report inference-time overhead transparently in Paper 2 and Paper 3.

## 13. Caveats

- **The Donoho-Elad bound is worst-case.** A µ̂ of 0.3 nominally allows only k_total < (1 + 1/0.3)/2 ≈ 2.17 — far below realistic SAE sparsities. The bound is *sufficient*, not necessary; average-case recovery (McCoy-Tropp statistical-dimension regime) is much more permissive, but it depends on randomness assumptions (random rotation of one dictionary, Bernoulli-Gaussian coefficients) that learned dictionaries do not strictly satisfy. We will therefore use these bounds as design *heuristics* (lower µ̂ is better, large total descent-cone-dimension is bad) rather than as theorems we can invoke on the trained SAE.
- **DeepMind's blog (March 26, 2025)** stated in its TL;DR: "we do not think that SAEs will be a game-changer for interpretability, and speculate that the field is over-invested in them." Even improved SAEs may not provide the downstream-task value the field originally expected. MSAE has to be evaluated on that strong form of the claim — does it actually help any *downstream* user (steering, debiasing, circuit discovery, unlearning) more than the baselines do? — not just on intrinsic metrics. Paper 2's Kantamneni-benchmark inclusion (§2.9) is the explicit hedge against this critique.
- **Multi-dimensional features (circles, manifolds)** are not strictly an MCA-style "sparse in a different basis" problem; they are a "sparse in an atomic-norm whose atoms are manifold pieces" problem. The Chandrasekaran-Recht-Parrilo-Willsky atomic-norm framework formally covers this, but the *learnability* of such an atomic set inside a transformer activation is an open theoretical question; the D_subspace branch in Paper 3 is a heuristic instantiation, not a guaranteed-recovery method.
- **Identifiability of the incoherence-regularised SAE** is not proved by any single theorem above; we are *composing* MCA's two-dictionary recovery results with the dictionary-learning guarantees of Spielman-Wang-Wright / Arora-Ge-Moitra. A clean theoretical result on the joint problem ("multi-dictionary learning under mutual incoherence") would be a valuable companion paper but is not a prerequisite for the empirical work.
- **Kantamneni et al. is a strong negative result** for SAE probing in general; MSAE has no a priori reason to overturn it. If MSAE features do close the LR-vs-SAE-probe gap that is itself interesting; if they do not, that is consistent with the "SAEs are not the right representation for downstream classification" hypothesis and does not invalidate the gains on absorption/SCR/TPP/RAVEL.
- **Source quality**: Anthropic's *Towards Monosemanticity* (Bricken et al. 2023) and *Scaling Monosemanticity* (Templeton et al. 2024) do not publish the kind of full hyperparameter tables Gemma-Scope and Gao et al. do; we should treat the Gemma-Scope and OpenAI TopK recipes as the *practical* SOTA baselines and note that any Anthropic-style comparison is necessarily approximate.
- **Matryoshka's frontier tradeoff** (the principal benchmark Paper 2 must clear) is reported by Bussmann et al. and SAEBench in figure form only — no single numerical Loss-Recovered gap is published; comparisons must therefore re-run the relevant baselines in-house at matched L0 rather than cite a headline number.
- **Position information might be 'everywhere' in deep layers.** Recent work suggests position is heavily mixed with content in deep layers. The Paper 1 split is cleaner at Pythia-160M layer 3/4 than at deeper layers, with layer 3 as primary target and layer 4 as fallback. If supervised K=2 fails at both layers 3 and 4 it is unlikely to succeed at layer 8 or 10; if it succeeds at layer 3/4, replication at later layers should be a §1.x ablation, not its own experiment.
- **Inference cost matters for adoption.** K-branch MSAE inference is more expensive than single-SAE inference. We therefore report throughput, memory footprint, and latency multipliers in Papers 2 and 3, and we interpret downstream gains relative to this compute tax.
- **Per-paper failure modes that should kill or redesign the project**: (i) µ̂(D_j, D_k) collapses to > 0.8 once λ_inc is removed (the dictionaries learn essentially the same atoms; the regularizer is doing all the work — papers downgrade to "incoherence regularizer for SAEs" instead of "multi-dictionary SAE"). (ii) D_3 absorbs > 40% of variance in Paper 2 (the sparse branches are not learning anything new beyond a PCA bias — Paper 2 should pivot to "sparse SAE + low-rank baseline" framing rather than full K=3 MSAE). (iii) Seed stability does not improve over standard JumpReLU at matched width and L0 in Paper 1 (multi-dictionary structure does not regularise the loss landscape — Paper 1 is downgraded to negative-result form). (iv) Any per-metric SAEBench number in Paper 2 is worse than Matryoshka by more than 5pp with no compensating improvement (Paper 2 cannot claim general SAEBench leadership; reframe around the metrics where it does win).
