function CARE_MVGC_4ROI_Run(taskTag)
% CARE_MVGC_4ROI_Run(taskTag)
% ------------------------------------------------------------
% Whole-task MVGC for CARE hyperscanning (STRICT 4 ROI for BOTH roles).
% Single unified pipeline for:
%   - REAL dyads MVGC
%   - PSEUDO-DYAD null MVGC (STATIC; between-dyad parent-child recombination)
%   - (optional) WITHIN-DYAD BLOCK null (STATIC asym only; for later dynamic work)
%
% Key design goals:
%   1) REAL and NULL both run the SAME MVGC engine -> identical edge table format.
%   2) Null pairs are generated ONCE and saved (reproducible).
%   3) Null statistics compare the same-level statistic:
%        REAL statistic = mean across real dyads
%        NULL statistic = bootstrap distribution of mean across nReal pseudo-dyads
%   4) Permutation outputs include GC values (edge-level), not only summary p-values.
%   5) Adds PRIMARY global dyad-specificity test:
%        Is global interbrain GC in REAL dyads > pseudo-dyad null?
%
% USAGE:
%   CARE_MVGC_4ROI_Run('ST');
%   CARE_MVGC_4ROI_Run('FT');
clc;
%% -------------------------
% 0) Input + CONFIG
% -------------------------
if nargin < 1 || isempty(taskTag)
    taskTag = 'ST';
end
assert(ischar(taskTag) || isstring(taskTag), 'taskTag must be ST or FT');
taskTag = upper(string(taskTag));
assert(taskTag=="ST" || taskTag=="FT", 'taskTag must be ST or FT');
CFG = struct();
CFG.BASEDIR = '/Users/janet/Desktop/Preprocessing/Preprocessing_fNIRS_StepA/Mara/Mara_TaskReady';
CFG.QC_DIR  = '/Users/janet/Desktop/Preprocessing/Preprocessing_fNIRS_StepA/Mara/QC_MATH';
CFG.DATA_DIR = CFG.BASEDIR;
CFG.MARA_DIR  = fullfile(CFG.BASEDIR,'MARA');
CFG.CACHE_DIR = fullfile(CFG.MARA_DIR,'CACHE');
CFG.PERM_DIR  = fullfile(CFG.MARA_DIR,'PERMUTATION');
CFG.OUTDIR    = fullfile(CFG.MARA_DIR, char(taskTag));
ensure_dir(CFG.MARA_DIR);
ensure_dir(CFG.CACHE_DIR);
ensure_dir(CFG.PERM_DIR);
ensure_dir(CFG.OUTDIR);
CFG.TASK = char(taskTag);
CFG.HB   = 'hbo';
% ROI definitions (fixed mapping)
CFG.ROI(1).name = 'LDLPFC'; CFG.ROI(1).chs = [1 8 16 9];
CFG.ROI(2).name = 'RDLPFC'; CFG.ROI(2).chs = [5 12 20 13];
CFG.ROI(3).name = 'LTPJ';   CFG.ROI(3).chs = [3 10 18 11];
CFG.ROI(4).name = 'RTPJ';   CFG.ROI(4).chs = [7 14 22 15];
CFG.min_good_ch  = 2;
CFG.require_all4 = true;
% MVGC settings
CFG.ESTIMATOR = 'LWR';
CFG.MAX_ORDER = 30;
CFG.DETREND   = true;
CFG.ZSCORE    = true;
% REAL p-values inside MVGC (within dyad) for descriptive purposes
CFG.ALPHA_FDR_WITHIN_DYAD = 0.05;
% -------------------------
% PERMUTATION switches
% -------------------------
CFG.DO_PSEUDO = true;
CFG.DO_BLOCK  = false;
CFG.PERM_SEED = 777;
CFG.PSEUDO_UNIQUE_PAIRS = true;
CFG.PSEUDO_USE_FULL_ORDERED_POOL = true; % if true, use all nReal*(nReal-1) non-self ordered pairs
CFG.PERM_N    = 1000;                    % used only if PSEUDO_USE_FULL_ORDERED_POOL=false
CFG.NULL_MO_MODE      = 'DYAD_MEAN'; % DYAD_MEAN | DYAD_MIN | BIC_CAPPED
CFG.NULL_MORDER_CAP   = 30;
CFG.NULL_FALLBACK_MO  = 10;
CFG.RIDGE_EPS = 1e-8;
CFG.NULL_BOOT_B    = 5000;
CFG.NULL_BOOT_SEED = 777;
CFG.BLK_LEN_SEC = 5;
CFG.BLK_MIN_N   = 8;
CFG.EXPORT_NULL_EDGE_TABLE = true;
%% -------------------------
% 1) Toolbox checks
% -------------------------
mustExist = {'tsdata_to_infocrit','tsdata_to_var','var_to_pwcgc','mvgc_pval','isbad'};
for i = 1:numel(mustExist)
    assert(exist(mustExist{i},'file')==2, 'Missing MVGC function: %s', mustExist{i});
end
qcfiles = dir(fullfile(CFG.QC_DIR,'*_TaskReady_QC.mat'));
assert(~isempty(qcfiles), 'No QC mats found in %s', CFG.QC_DIR);
fprintf('=== CARE MVGC %s (STRICT 4ROI) ===\n', CFG.TASK);
fprintf('OUTDIR: %s\n', CFG.OUTDIR);
fprintf('PSEUDO: %d | BLOCK: %d | PERM_N: %d\n\n', CFG.DO_PSEUDO, CFG.DO_BLOCK, CFG.PERM_N);
%% -------------------------
% 2) Headers / indexing
% -------------------------
EDGE_HDR = {'Dyad','Task','fs','nObs','morder_BIC', ...
            'Src','Dst','SrcRole','DstRole','Direction', ...
            'SrcROI','DstROI','SrcNet','DstNet','SrcHem','DstHem', ...
            'Route','RouteFamily','IsInterbrain','IsCrossHem', ...
            'GC','pval','sig_FDR'};
EDGEVARS = fixed_varnames_8();
[edgePairs_i, edgePairs_j, ~, ~, edgeMeta] = fixed_interbrain_edge_index_and_meta(EDGEVARS);
nInterEdges = numel(edgePairs_i);
roiList = {'LDLPFC','RDLPFC','LTPJ','RTPJ'};
nROI = 4;
nRoutes = nROI*nROI;
%% -------------------------
% 3) Build ELIG (REAL dyads)
% -------------------------
ELIG_CACHE = fullfile(CFG.CACHE_DIR, sprintf('ELIG_%s.mat', CFG.TASK));
USE_CACHE = false;
if exist(ELIG_CACHE,'file') == 2
    USE_CACHE = true;
end
ELIG = struct('dyad',{},'fs',{},'Tobs',{},'morder',{},'X',{});
edges_real = {};
realInterEdgeMat = [];   % [nReal x 32]
realRouteDEL = [];       % [nReal x 16]
realAsym = [];           % [nReal x 1]
realGlobalInter = [];    % [nReal x 1]
if USE_CACHE
    fprintf('[CACHE] Loading ELIG from %s\n', ELIG_CACHE);
    S = load(ELIG_CACHE);
    ELIG = S.ELIG;
else
    fprintf('[REAL] Building ELIG from QC_MATH + TaskReady...\n');
    for f = 1:numel(qcfiles)
        qcfile = qcfiles(f).name;
        dyad = infer_dyad_from_qcname(qcfile);
        qcpath = fullfile(CFG.QC_DIR, qcfile);
        trpath = fullfile(CFG.DATA_DIR, sprintf('%s_TaskReady.mat', dyad));
        if exist(trpath,'file') ~= 2
            fprintf('[%s] SKIP missing TaskReady\n', dyad);
            continue;
        end
        Sq = load(qcpath);
        outQC = pick_first_struct(Sq, {'outQC','QC','qc','out','OUT'});
        if isempty(outQC)
            fprintf('[%s] SKIP outQC\n', dyad);
            continue;
        end
        St = load(trpath);
        outTask = pick_first_struct(St, {'outTask','TaskReady','taskready','TR','out','data'});
        if isempty(outTask) || ~isfield(outTask, CFG.TASK)
            fprintf('[%s] SKIP outTask.%s\n', dyad, CFG.TASK);
            continue;
        end
        [Xp, Xc, fs, ok, msg] = get_task_mats_from_outTask(outTask, CFG.TASK, CFG.HB);
        if ~ok
            fprintf('[%s] SKIP %s\n', dyad, msg);
            continue;
        end
        [keepP, keepC] = get_keep_masks_from_outQC(outQC, CFG.TASK, size(Xp,2));
        [Xp_roi, Xc_roi, roi_names, ~, ~] = build_roi_timeseries_clean( ...
            Xp, Xc, keepP, keepC, CFG.ROI, CFG.min_good_ch);
        if CFG.require_all4 && numel(roi_names) ~= 4
            fprintf('[%s] SKIP ROI<4 (got %d)\n', dyad, numel(roi_names));
            continue;
        end
        X = preprocess_safe([Xp_roi; Xc_roi], CFG.DETREND, CFG.ZSCORE);
        Tobs = size(X,2);
        X3 = reshape(X, 8, Tobs, 1);
        morder = choose_morder_BIC_safe(X3, CFG.MAX_ORDER, CFG.ESTIMATOR, CFG.NULL_FALLBACK_MO);
        morder = max(2, morder);
        if Tobs <= max((morder+1)*8, 10*morder)
            fprintf('[%s] SKIP too short for VAR: T=%d m=%d\n', dyad, Tobs, morder);
            continue;
        end
        ELIG(end+1) = struct('dyad',dyad,'fs',fs,'Tobs',Tobs,'morder',morder,'X',X); %#ok<AGROW>
        fprintf('[%s] ELIG OK: T=%d mBIC=%d\n', dyad, Tobs, morder);
    end
    save(ELIG_CACHE,'ELIG','-v7.3');
    fprintf('[CACHE] Saved ELIG to %s\n', ELIG_CACHE);
end
nReal = numel(ELIG);
fprintf('\nEligible %s dyads: %d\n', CFG.TASK, nReal);
if nReal < 2
    warning('Not enough eligible dyads for pseudo-dyad permutations.');
end
if CFG.DO_PSEUDO && nReal >= 2 && CFG.PSEUDO_USE_FULL_ORDERED_POOL
    CFG.PERM_N = nReal * (nReal - 1);
    fprintf('[PSEUDO] Using full ordered non-self pseudo-dyad pool: %d*%d = %d pairs\n', ...
        nReal, nReal-1, CFG.PERM_N);
end
manifestHdr = {'Task','N_real','PseudoPairRule','N_pseudo_requested_or_used','NullModelOrderMode', ...
               'PrimaryTail','Estimator','MaxOrder','Detrend','Zscore','RidgeEps'};
manifestRows = {CFG.TASK, nReal, tern(CFG.PSEUDO_USE_FULL_ORDERED_POOL, ...
                'full_ordered_nonself_nReal_x_nRealMinus1', 'configured_perm_n'), ...
                CFG.PERM_N, CFG.NULL_MO_MODE, 'upper_real_gt_null', CFG.ESTIMATOR, ...
                CFG.MAX_ORDER, logical(CFG.DETREND), logical(CFG.ZSCORE), CFG.RIDGE_EPS};
out_manifest = fullfile(CFG.OUTDIR, sprintf('GC_pipeline_manifest_%s.csv', CFG.TASK));
write_cell_csv(out_manifest, manifestHdr, manifestRows);
fprintf('[MANIFEST] Saved: %s\n', out_manifest);
%% -------------------------
% 4) Run REAL MVGC (edge table)
% -------------------------
fprintf('\n[REAL] Running MVGC for %d dyads...\n', nReal);
for d = 1:nReal
    D = ELIG(d);
    [rows, Fmat, ~, ~] = run_mvgc_engine_edgeRows(D.X, D.fs, D.Tobs, D.morder, CFG, EDGEVARS, EDGE_HDR);
    rows = relabel_edgeRows_dyad(rows, D.dyad);
    edges_real = [edges_real; rows]; %#ok<AGROW>
    evec = nan(1, nInterEdges);
    for k = 1:nInterEdges
        evec(k) = Fmat(edgePairs_i(k), edgePairs_j(k));
    end
    realInterEdgeMat = [realInterEdgeMat; evec]; %#ok<AGROW>
    realGlobalInter(end+1,1) = mean(evec, 'omitnan'); %#ok<AGROW>
    rd = nan(1, nRoutes);
    for s = 1:nROI
        for dd = 1:nROI
            idxR = (s-1)*nROI + dd;
            p2c = Fmat(nROI+dd, s);
            c2p = Fmat(dd, nROI+s);
            rd(idxR) = p2c - c2p;
        end
    end
    realRouteDEL = [realRouteDEL; rd]; %#ok<AGROW>
    [~,~,asym] = compute_mean_asym(Fmat, nROI);
    realAsym(end+1,1) = asym; %#ok<AGROW>
end
out_real_edges = fullfile(CFG.OUTDIR, sprintf('GC_real_edges_%s.csv', CFG.TASK));
write_cell_csv(out_real_edges, EDGE_HDR, edges_real);
fprintf('[REAL] Saved: %s\n', out_real_edges);
fprintf('\nREAL dyads computed: %d\n', size(realInterEdgeMat,1));
fprintf('realGlobalInter length: %d\n', numel(realGlobalInter));
if isempty(realGlobalInter)
    error('realGlobalInter is empty — REAL loop did not populate global GC.');
end
%% -------------------------
% 5) PSEUDO-DYAD NULL: generate / load pairList
% -------------------------
pairsFile = fullfile(CFG.PERM_DIR, sprintf('pseudo_pairs_%s_N%d_seed%d.mat', CFG.TASK, CFG.PERM_N, CFG.PERM_SEED));
rng(CFG.PERM_SEED);
pairList = [];
if CFG.DO_PSEUDO && nReal >= 2
    if exist(pairsFile,'file') == 2
        S = load(pairsFile);
        pairList = S.pairList;
        fprintf('\n[PSEUDO] Loaded pairList: %s\n', pairsFile);
    else
        rng(CFG.PERM_SEED);
        allPairs = [];
        for i = 1:nReal
            for j = 1:nReal
                if i == j
                    continue;
                end
                allPairs(end+1,:) = [i j]; %#ok<AGROW>
            end
        end
        nPairs = size(allPairs,1);
        if CFG.PSEUDO_USE_FULL_ORDERED_POOL
            pairList = allPairs(randperm(nPairs),:);
            fprintf('\n[PSEUDO] FULL ordered non-self pairs: using all %d pairs\n', nPairs);
        elseif CFG.PSEUDO_UNIQUE_PAIRS
            ord = randperm(nPairs);
            allPairs = allPairs(ord,:);
            if CFG.PERM_N <= nPairs
                pairList = allPairs(1:CFG.PERM_N,:);
                fprintf('\n[PSEUDO] UNIQUE ordered pairs: using %d/%d\n', CFG.PERM_N, nPairs);
            else
                nExtra = CFG.PERM_N - nPairs;
                extraIdx = randi(nPairs, [nExtra 1]);
                pairList = [allPairs; allPairs(extraIdx,:)];
                fprintf('\n[PSEUDO] UNIQUE ordered pairs exhausted (%d); topped up with %d resampled pairs -> total %d\n', ...
                    nPairs, nExtra, size(pairList,1));
            end
        else
            pairList = nan(CFG.PERM_N,2);
            for p = 1:CFG.PERM_N
                ij = randperm(nReal,2);
                pairList(p,:) = ij;
            end
            fprintf('\n[PSEUDO] WITH replacement pairs: N=%d\n', CFG.PERM_N);
        end
        save(pairsFile,'pairList','-v7.3');
        fprintf('[PSEUDO] Saved pairList: %s\n', pairsFile);
    end
else
    fprintf('\n[INFO] Pseudo-dyad null skipped.\n');
end
%% -------------------------
% 6) Run NULL MVGC for each pseudo dyad (edge table)
% -------------------------
edges_null = {};
nullInterEdgeMat = [];
nullRouteDEL = [];
nullAsym = [];
nullGlobalInter = [];
nullPermIDs = [];
pseudoRows = {};
pseudoHdr = {'perm_id','dyad_parent','dyad_child','morder_used','asym_null','Tobs','status','note'};
if CFG.DO_PSEUDO && ~isempty(pairList)
    fprintf('\n[PSEUDO] Running MVGC for %d pseudo dyads...\n', size(pairList,1));
    for p = 1:size(pairList,1)
        iA = pairList(p,1);
        iB = pairList(p,2);
        if ~isfinite(iA) || ~isfinite(iB) || iA < 1 || iB < 1 || iA > numel(ELIG) || iB > numel(ELIG)
            pseudoRows(end+1,:) = {p,'','',NaN,NaN,NaN,'FAIL','Invalid pairList indices'}; %#ok<AGROW>
            continue;
        end
        Arec = ELIG(iA);
        Brec = ELIG(iB);
        dyadA = Arec.dyad;
        dyadB = Brec.dyad;
        if isfinite(Arec.fs) && isfinite(Brec.fs) && abs(Arec.fs - Brec.fs) > 1e-9
            pseudoRows(end+1,:) = {p,dyadA,dyadB,NaN,NaN,NaN,'FAIL','Sampling-rate mismatch'}; %#ok<AGROW>
            continue;
        end
        T = min(Arec.Tobs, Brec.Tobs);
        Xnull = [Arec.X(1:4,1:T); Brec.X(5:8,1:T)];
        mUsed = choose_null_morder(Arec.morder, Brec.morder, Xnull, CFG);
        if T <= (mUsed+1)*8
            pseudoRows(end+1,:) = {p,dyadA,dyadB,mUsed,NaN,T,'FAIL','Too short for chosen morder'}; %#ok<AGROW>
            continue;
        end
        ok = false;
        note = '';
        asym0 = NaN;
        try
            [rows, F0, ~, ~] = run_mvgc_engine_edgeRows(Xnull, Arec.fs, T, mUsed, CFG, EDGEVARS, EDGE_HDR);
            ok = true;
            pseudoID = sprintf('PS%04d', p);
            rows = relabel_edgeRows_dyad(rows, pseudoID);
            if CFG.EXPORT_NULL_EDGE_TABLE
                edges_null = [edges_null; rows]; %#ok<AGROW>
            end
            evec0 = nan(1, nInterEdges);
            for k = 1:nInterEdges
                evec0(k) = F0(edgePairs_i(k), edgePairs_j(k));
            end
            nullInterEdgeMat = [nullInterEdgeMat; evec0]; %#ok<AGROW>
            nullGlobalInter(end+1,1) = mean(evec0, 'omitnan'); %#ok<AGROW>
            rd0 = nan(1,nRoutes);
            for s = 1:nROI
                for dd = 1:nROI
                    idxR = (s-1)*nROI + dd;
                    p2c0 = F0(nROI+dd, s);
                    c2p0 = F0(dd, nROI+s);
                    rd0(idxR) = p2c0 - c2p0;
                end
            end
            nullRouteDEL = [nullRouteDEL; rd0]; %#ok<AGROW>
            [~,~,asym0] = compute_mean_asym(F0, nROI);
            nullAsym(end+1,1) = asym0; %#ok<AGROW>
            nullPermIDs(end+1,1) = p; %#ok<AGROW>
        catch ME
            note = ME.message;
            if numel(note) > 180
                note = note(1:180);
            end
        end
        pseudoRows(end+1,:) = {p,dyadA,dyadB,mUsed,asym0,T,tern(ok,'OK','FAIL'),note}; %#ok<AGROW>
        if mod(p,200)==0
            fprintf('  ... %d/%d\n', p, size(pairList,1));
        end
    end
    out_pseudo_log = fullfile(CFG.OUTDIR, sprintf('GC_null_pseudodyad_%s.csv', CFG.TASK));
    write_cell_csv(out_pseudo_log, pseudoHdr, pseudoRows);
    fprintf('[PSEUDO] Saved log: %s\n', out_pseudo_log);
    if CFG.EXPORT_NULL_EDGE_TABLE
        out_null_edges = fullfile(CFG.OUTDIR, sprintf('GC_null_edges_%s.csv', CFG.TASK));
        write_cell_csv(out_null_edges, EDGE_HDR, edges_null);
        fprintf('[PSEUDO] Saved NULL edge table: %s\n', out_null_edges);
    end
end
%% -------------------------
% 7A) GLOBAL dyad-specificity test
% Primary confirmatory tail follows prior hyperscanning expectation:
% real dyads > pseudo-dyad null.
% -------------------------
globalHdr = {'Task','N_real','real_mean_globalInterbrain', ...
             'N_null_OK','null_meanMean_globalInterbrain','null_sdMean_globalInterbrain', ...
             'delta_realMinusNull','p_emp_upper_real_gt_null_PRIMARY','p_emp_twoSided_descriptive'};
globalRows = {};
realGlobalMean = mean(realGlobalInter, 'omitnan');
nNullOK_global = numel(nullGlobalInter);
nullGlobalMu = NaN;
nullGlobalSd = NaN;
pGlobalOne = NaN;
pGlobalTwo = NaN;
if CFG.DO_PSEUDO && nNullOK_global > 0 && nReal > 0
    rng(CFG.NULL_BOOT_SEED);
    B = CFG.NULL_BOOT_B;
    bootGlobal = nan(B,1);
    for b = 1:B
        idx = randi(nNullOK_global, [nReal 1]);
        bootGlobal(b) = mean(nullGlobalInter(idx), 'omitnan');
    end
    nullGlobalMu = mean(bootGlobal, 'omitnan');
    nullGlobalSd = std(bootGlobal, 0, 'omitnan');
    pGlobalOne = (sum(bootGlobal >= realGlobalMean) + 1) / (B + 1);
    pGlobalTwo = (sum(abs(bootGlobal - nullGlobalMu) >= abs(realGlobalMean - nullGlobalMu)) + 1) / (B + 1);
end
globalRows(1,:) = {CFG.TASK, nReal, realGlobalMean, ...
                   nNullOK_global, nullGlobalMu, nullGlobalSd, ...
                   realGlobalMean - nullGlobalMu, pGlobalOne, pGlobalTwo};
out_globalSummary = fullfile(CFG.OUTDIR, sprintf('GC_null_globalSummary_%s.csv', CFG.TASK));
write_cell_csv(out_globalSummary, globalHdr, globalRows);
fprintf('\n[GLOBAL] Saved dyad-specificity summary: %s\n', out_globalSummary);
%% -------------------------
% 7B) Edge existence test
% -------------------------
edgeSumHdr = {'Edge','Direction','Src','Dst','SrcROI','DstROI','SrcNet','DstNet','SrcHem','DstHem', ...
              'N_real','real_mean', ...
              'N_null_OK','null_meanMean','null_sdMean', ...
              'p_emp_upper_realMean_gt_nullMean_PRIMARY', ...
              'p_fdr_BH','sig_fdr_BH'};
edgeSumRows = {};
pEmp = nan(1,nInterEdges);
realMean = mean(realInterEdgeMat, 1, 'omitnan');
nNullOK_edge = size(nullInterEdgeMat,1);
nullMu = nan(1,nInterEdges);
nullSd = nan(1,nInterEdges);
if CFG.DO_PSEUDO && nNullOK_edge > 0 && nReal > 0
    rng(CFG.NULL_BOOT_SEED);
    B = CFG.NULL_BOOT_B;
    bootMeans = nan(B, nInterEdges);
    for b = 1:B
        idx = randi(nNullOK_edge, [nReal 1]);
        bootMeans(b,:) = mean(nullInterEdgeMat(idx,:), 1, 'omitnan');
    end
    nullMu = mean(bootMeans, 1, 'omitnan');
    nullSd = std(bootMeans, 0, 1, 'omitnan');
    for k = 1:nInterEdges
        pEmp(k) = (sum(bootMeans(:,k) >= realMean(k)) + 1) / (B + 1);
    end
end
pFDR = bh_fdr_vec(pEmp);
sigFDR = pFDR < 0.05;
for k = 1:nInterEdges
    m = edgeMeta(k);
    edgeLabel = [m.Src '->' m.Dst];
    edgeSumRows(end+1,:) = {edgeLabel, m.Direction, m.Src, m.Dst, m.SrcROI, m.DstROI, ...
                            m.SrcNet, m.DstNet, m.SrcHem, m.DstHem, ...
                            nReal, realMean(k), ...
                            nNullOK_edge, nullMu(k), nullSd(k), ...
                            pEmp(k), pFDR(k), logical(sigFDR(k))}; %#ok<AGROW>
end
out_edgeSummary = fullfile(CFG.OUTDIR, sprintf('GC_null_edgeSummary_%s.csv', CFG.TASK));
write_cell_csv(out_edgeSummary, edgeSumHdr, edgeSumRows);
fprintf('\n[STEP1] Saved edge existence summary: %s\n', out_edgeSummary);
%% -------------------------
% 8) Route delta summary
% -------------------------
routeHdr = {'Route','SrcROI','DstROI','route_key', ...
            'N_real','real_mean_DELTA', ...
            'N_null_OK','null_meanMean_DELTA','null_sdMean_DELTA', ...
            'p_emp_upper_DELTA_PRIMARY','p_fdr_BH_DELTA','sig_fdr_BH_DELTA'};
routeRows2 = {};
pEmpR = nan(1,nRoutes);
realRouteMean = mean(realRouteDEL, 1, 'omitnan');
nNullOK_route = size(nullRouteDEL,1);
nullRouteMu = nan(1,nRoutes);
nullRouteSd = nan(1,nRoutes);
if CFG.DO_PSEUDO && nNullOK_route > 0 && nReal > 0
    rng(CFG.NULL_BOOT_SEED);
    B = CFG.NULL_BOOT_B;
    bootRoute = nan(B, nRoutes);
    for b = 1:B
        idx = randi(nNullOK_route, [nReal 1]);
        bootRoute(b,:) = mean(nullRouteDEL(idx,:), 1, 'omitnan');
    end
    nullRouteMu = mean(bootRoute, 1, 'omitnan');
    nullRouteSd = std(bootRoute, 0, 1, 'omitnan');
    for r = 1:nRoutes
        pEmpR(r) = (sum(bootRoute(:,r) >= realRouteMean(r)) + 1) / (B + 1);
    end
end
pFDR_R = bh_fdr_vec(pEmpR);
sigFDR_R = pFDR_R < 0.05;
for s = 1:nROI
    for dd = 1:nROI
        idxR = (s-1)*nROI + dd;
        routeLabel = sprintf('%s->%s', roiList{s}, roiList{dd});
        routeKey   = sprintf('DEL_%s_to_%s', roiList{s}, roiList{dd});
        routeRows2(end+1,:) = {routeLabel, roiList{s}, roiList{dd}, routeKey, ...
                               nReal, realRouteMean(idxR), ...
                               nNullOK_route, nullRouteMu(idxR), nullRouteSd(idxR), ...
                               pEmpR(idxR), pFDR_R(idxR), logical(sigFDR_R(idxR))}; %#ok<AGROW>
    end
end
out_routeSummary = fullfile(CFG.OUTDIR, sprintf('GC_null_routeDeltaSummary_%s.csv', CFG.TASK));
write_cell_csv(out_routeSummary, routeHdr, routeRows2);
fprintf('[ROUTE] Saved route delta summary: %s\n', out_routeSummary);
%% -------------------------
% 9) Block null (optional)
% -------------------------
if CFG.DO_BLOCK
    fprintf('\n[BLOCK] Running within-dyad block null (ASYM only) ...\n');
    blkHdr = {'perm_id','dyad','blk_len','morder_used','asym_null','Tobs','status','note'};
    blkRows = {};
    rng(CFG.PERM_SEED);
    for i = 1:nReal
        D = ELIG(i);
        fs = D.fs;
        T  = D.Tobs;
        blk_len = max(5, round(CFG.BLK_LEN_SEC * fs));
        nBlk = floor(T/blk_len);
        if nBlk < CFG.BLK_MIN_N
            blkRows(end+1,:) = {NaN, D.dyad, blk_len, NaN, NaN, T, 'SKIP', sprintf('nBlk=%d too small', nBlk)}; %#ok<AGROW>
            continue;
        end
        Tuse = nBlk*blk_len;
        Xp = D.X(1:4,1:Tuse);
        Xc = D.X(5:8,1:Tuse);
        Xc_blk = reshape(Xc, 4, blk_len, nBlk);
        mFixed = D.morder;
        for p = 1:CFG.PERM_N
            ord = randperm(nBlk);
            Xc_null = reshape(Xc_blk(:,:,ord), 4, Tuse);
            Xnull = [Xp; Xc_null];
            [ok, asym0, note] = run_null_asym_only(Xnull, mFixed, CFG);
            blkRows(end+1,:) = {p, D.dyad, blk_len, mFixed, asym0, Tuse, tern(ok,'OK','FAIL'), note}; %#ok<AGROW>
        end
    end
    out_block = fullfile(CFG.OUTDIR, sprintf('GC_null_blockChild_%s.csv', CFG.TASK));
    write_cell_csv(out_block, blkHdr, blkRows);
    fprintf('[BLOCK] Saved: %s\n', out_block);
end
fprintf('\n✅ DONE: CARE_MVGC_4ROI_Run(%s)\n', CFG.TASK);
end
%% =========================
% Helpers
% =========================
function ensure_dir(p)
if ~exist(p,'dir')
    mkdir(p);
end
end
function vars = fixed_varnames_8()
vars = {'P_LDLPFC','P_RDLPFC','P_LTPJ','P_RTPJ','C_LDLPFC','C_RDLPFC','C_LTPJ','C_RTPJ'};
end
function [iis,jjs,srcs,dsts,meta] = fixed_interbrain_edge_index_and_meta(vars)
iis = [];
jjs = [];
srcs = {};
dsts = {};
meta = struct('Src',{},'Dst',{},'SrcROI',{},'DstROI',{},'SrcNet',{},'DstNet',{},'SrcHem',{},'DstHem',{},'Direction',{});
k = 0;
for dst = 1:8
    for src = 1:8
        if dst == src
            continue;
        end
        [srcRole, srcROI, srcNet, srcHem] = parse_varname(vars{src});
        [dstRole, dstROI, dstNet, dstHem] = parse_varname(vars{dst});
        direction = classify_direction(srcRole, dstRole);
        if strcmp(direction,'within_role_or_other')
            continue;
        end
        k = k + 1;
        iis(k) = dst; %#ok<AGROW>
        jjs(k) = src; %#ok<AGROW>
        srcs{k} = vars{src}; %#ok<AGROW>
        dsts{k} = vars{dst}; %#ok<AGROW>
        meta(k).Src = vars{src};
        meta(k).Dst = vars{dst};
        meta(k).SrcROI = srcROI;
        meta(k).DstROI = dstROI;
        meta(k).SrcNet = srcNet;
        meta(k).DstNet = dstNet;
        meta(k).SrcHem = srcHem;
        meta(k).DstHem = dstHem;
        meta(k).Direction = direction;
    end
end
end
function dyad = infer_dyad_from_qcname(qcfile)
tok = regexp(qcfile, '^([0-9]{2}[A-Za-z])_TaskReady_QC\.mat$', 'tokens', 'once');
if ~isempty(tok)
    dyad = upper(tok{1});
else
    dyad = upper(qcfile(1:min(3,numel(qcfile))));
end
end
function S = pick_first_struct(L, candidates)
S = [];
for i = 1:numel(candidates)
    c = candidates{i};
    if isfield(L,c) && isstruct(L.(c))
        S = L.(c);
        return;
    end
end
fn = fieldnames(L);
for i = 1:numel(fn)
    if isstruct(L.(fn{i}))
        S = L.(fn{i});
        return;
    end
end
end
function [Xp, Xc, fs, ok, msg] = get_task_mats_from_outTask(outTask, task, hb)
ok = false;
msg = '';
fs = NaN;
Xp = [];
Xc = [];
if ~isfield(outTask, task)
    msg = sprintf('Missing outTask.%s',task);
    return;
end
T = outTask.(task);
pf = ['p_' hb];
cf = ['c_' hb];
if ~isfield(T,pf) || ~isfield(T,cf)
    msg = sprintf('Missing %s/%s',pf,cf);
    return;
end
Xp = T.(pf);
Xc = T.(cf);
if isempty(Xp) || isempty(Xc)
    msg = 'Empty mats';
    return;
end
nT = min(size(Xp,1), size(Xc,1));
Xp = Xp(1:nT,:);
Xc = Xc(1:nT,:);
if isfield(T,'fs')
    fs = double(T.fs);
end
ok = true;
end
function [keepP, keepC] = get_keep_masks_from_outQC(outQC, task, nCh)
keepP = true(1,nCh);
keepC = true(1,nCh);
try
    if isfield(outQC,'tasks') && isfield(outQC.tasks,task)
        TT = outQC.tasks.(task);
        if isfield(TT,'segments') && ~isempty(TT.segments)
            seg1 = TT.segments(1);
            if isfield(seg1,'role')
                if isfield(seg1.role,'Parent') && isfield(seg1.role.Parent,'keepMask')
                    km = seg1.role.Parent.keepMask;
                    if numel(km)==nCh, keepP = logical(km(:))'; end
                end
                if isfield(seg1.role,'Child') && isfield(seg1.role.Child,'keepMask')
                    km = seg1.role.Child.keepMask;
                    if numel(km)==nCh, keepC = logical(km(:))'; end
                end
            end
        end
        if isfield(TT,'role')
            if isfield(TT.role,'Parent') && isfield(TT.role.Parent,'keepMask')
                km = TT.role.Parent.keepMask;
                if numel(km)==nCh, keepP = logical(km(:))'; end
            end
            if isfield(TT.role,'Child') && isfield(TT.role.Child,'keepMask')
                km = TT.role.Child.keepMask;
                if numel(km)==nCh, keepC = logical(km(:))'; end
            end
        end
        if isfield(TT,'keepMaskParent')
            km = TT.keepMaskParent;
            if numel(km)==nCh, keepP = logical(km(:))'; end
        end
        if isfield(TT,'keepMaskChild')
            km = TT.keepMaskChild;
            if numel(km)==nCh, keepC = logical(km(:))'; end
        end
    end
    if isfield(outQC,'keepMaskParent')
        km = outQC.keepMaskParent;
        if numel(km)==nCh, keepP = logical(km(:))'; end
    end
    if isfield(outQC,'keepMaskChild')
        km = outQC.keepMaskChild;
        if numel(km)==nCh, keepC = logical(km(:))'; end
    end
catch
    % keep defaults
end
end
function [Xp_roi, Xc_roi, roi_names, nGoodP, nGoodC] = build_roi_timeseries_clean(Xp,Xc,keepP,keepC,ROI,min_good_ch)
T = size(Xp,1);
Xp_roi = nan(4,T);
Xc_roi = nan(4,T);
roi_names = cell(1,0);
nGoodP = nan(1,0);
nGoodC = nan(1,0);
k = 0;
for r = 1:4
    chs = ROI(r).chs;
    chs = chs(chs>=1 & chs<=size(Xp,2));
    gP = chs(keepP(chs));
    gC = chs(keepC(chs));
    if numel(gP)>=min_good_ch && numel(gC)>=min_good_ch
        P = mean(Xp(:,gP),2,'omitnan');
        C = mean(Xc(:,gC),2,'omitnan');
        if ~all(isfinite(P)) || ~all(isfinite(C))
            continue;
        end
        k = k + 1;
        Xp_roi(k,:) = P(:)';
        Xc_roi(k,:) = C(:)';
        roi_names{k} = upper(ROI(r).name); %#ok<AGROW>
        nGoodP(k) = numel(gP); %#ok<AGROW>
        nGoodC(k) = numel(gC); %#ok<AGROW>
    end
end
Xp_roi = Xp_roi(1:k,:);
Xc_roi = Xc_roi(1:k,:);
end
function Xout = preprocess_safe(X, doDetrend, doZ)
Xout = X;
for v = 1:size(Xout,1)
    x = Xout(v,:)';
    x = x - mean(x,'omitnan');
    if doDetrend
        x = detrend(x,'linear');
    end
    if doZ
        sd = std(x,0,'omitnan');
        if sd > 1e-10
            x = (x - mean(x,'omitnan')) ./ sd;
        else
            x = x - mean(x,'omitnan');
        end
    end
    Xout(v,:) = x(:)';
end
if any(~isfinite(Xout(:)))
    error('Non-finite after preprocessing. Check ROI building / keep masks / flat signals.');
end
end
function morder = choose_morder_BIC_safe(X3, maxOrder, estimator, fallbackOrder)
morder = fallbackOrder;
try
    [~,~,~,moBIC] = tsdata_to_infocrit(X3, maxOrder, estimator);
    if ~isempty(moBIC) && isnumeric(moBIC) && isfinite(moBIC) && moBIC >= 1
        morder = moBIC;
    end
catch
end
end
function mUsed = choose_null_morder(mA, mB, Xnull, CFG)
mode = upper(string(CFG.NULL_MO_MODE));
switch mode
    case "DYAD_MEAN"
        mUsed = round((mA + mB)/2);
    case "DYAD_MIN"
        mUsed = min(mA, mB);
    case "BIC_CAPPED"
        T = size(Xnull,2);
        X3 = reshape(Xnull, 8, T, 1);
        mUsed = choose_morder_BIC_safe(X3, min(CFG.MAX_ORDER, CFG.NULL_MORDER_CAP), CFG.ESTIMATOR, CFG.NULL_FALLBACK_MO);
    otherwise
        mUsed = round((mA + mB)/2);
end
mUsed = max(2, mUsed);
mUsed = min(mUsed, CFG.NULL_MORDER_CAP);
if ~isfinite(mUsed) || mUsed < 2
    mUsed = CFG.NULL_FALLBACK_MO;
end
end
function [rows, Fmat, pval, sigFDR] = run_mvgc_engine_edgeRows(X, fs, Tobs, morder, CFG, var_names, ~)
nVars = size(X,1);
X3 = reshape(X, nVars, Tobs, 1);
[A,SIG] = tsdata_to_var(X3, morder, CFG.ESTIMATOR);
if isbad(A)
    error('VAR isbad');
end
SIG = SIG + CFG.RIDGE_EPS*eye(nVars);
[Fmat,~] = var_to_pwcgc(A, SIG, X3, CFG.ESTIMATOR, 'F');
if isbad(Fmat,false)
    error('GC isbad');
end
pval = mvgc_pval(Fmat, morder, Tobs, 1, 1, 1, 'F');
sigFDR = bh_fdr_offdiag(pval, CFG.ALPHA_FDR_WITHIN_DYAD);
rows = {};
for ii = 1:nVars
    for jj = 1:nVars
        if ii == jj
            continue;
        end
        src = var_names{jj};
        dst = var_names{ii};
        [srcRole, srcROI, srcNet, srcHem] = parse_varname(src);
        [dstRole, dstROI, dstNet, dstHem] = parse_varname(dst);
        direction = classify_direction(srcRole, dstRole);
        isInterbrain = ~strcmp(direction,'within_role_or_other');
        isCrossHem = ~isempty(srcHem) && ~isempty(dstHem) && ~strcmp(srcHem, dstHem);
        route = [src '->' dst];
        routeFamily = [srcNet '->' dstNet];
        rows(end+1,:) = { ...
            "REAL", CFG.TASK, fs, Tobs, morder, ...
            src, dst, srcRole, dstRole, direction, ...
            srcROI, dstROI, srcNet, dstNet, srcHem, dstHem, ...
            route, routeFamily, logical(isInterbrain), logical(isCrossHem), ...
            Fmat(ii,jj), pval(ii,jj), logical(sigFDR(ii,jj)) ...
            }; %#ok<AGROW>
    end
end
end
function rows = relabel_edgeRows_dyad(rows, dyadID)
for r = 1:size(rows,1)
    rows{r,1} = dyadID;
end
end
function sigFDR = bh_fdr_offdiag(pval, alpha)
n = size(pval,1);
mask = ~eye(n);
pvec = pval(mask);
p = pvec(:);
[ps,idx] = sort(p,'ascend');
m = numel(ps);
th = (1:m)'/m*alpha;
k = find(ps<=th,1,'last');
sig = false(m,1);
if ~isempty(k)
    sig(idx(1:k)) = true;
end
sigFDR = false(n);
sigFDR(mask) = sig;
end
function q = bh_fdr_vec(p)
q = nan(size(p));
idxValid = find(isfinite(p));
if isempty(idxValid)
    return;
end
pv = p(idxValid);
[mv,ord] = sort(pv(:),'ascend');
m = numel(mv);
qv = mv .* (m ./ (1:m))';
for i = m-1:-1:1
    qv(i) = min(qv(i), qv(i+1));
end
q(idxValid(ord)) = qv;
end
function [meanPC, meanCP, asym] = compute_mean_asym(F, nROI)
P = 1:nROI;
C = nROI + (1:nROI);
PC = [];
CP = [];
for d = C
    for s = P
        PC(end+1) = F(d,s); %#ok<AGROW>
    end
end
for d = P
    for s = C
        CP(end+1) = F(d,s); %#ok<AGROW>
    end
end
meanPC = mean(PC);
meanCP = mean(CP);
asym = meanPC - meanCP;
end
function [role, roi, net, hem] = parse_varname(vn)
role = '';
roi = '';
net = '';
hem = '';
if numel(vn) < 3
    return;
end
if startsWith(vn,'P_')
    role = 'P';
elseif startsWith(vn,'C_')
    role = 'C';
end
roi = regexprep(vn,'^[PC]_','');
if startsWith(roi,'L')
    hem = 'L';
elseif startsWith(roi,'R')
    hem = 'R';
end
if contains(roi,'DLPFC')
    net = 'DLPFC';
elseif contains(roi,'TPJ')
    net = 'TPJ';
else
    net = 'OTHER';
end
end
function direction = classify_direction(srcRole, dstRole)
if strcmp(srcRole,'P') && strcmp(dstRole,'C')
    direction = 'P_to_C';
elseif strcmp(srcRole,'C') && strcmp(dstRole,'P')
    direction = 'C_to_P';
else
    direction = 'within_role_or_other';
end
end
function [ok, asym0, note] = run_null_asym_only(Xnull, mFixed, CFG)
ok = false;
asym0 = NaN;
note = '';
nVars = size(Xnull,1);
T = size(Xnull,2);
X3 = reshape(Xnull,nVars,T,1);
try
    [A,SIG] = tsdata_to_var(X3, mFixed, CFG.ESTIMATOR);
    if isbad(A)
        note = 'VAR isbad';
        return;
    end
    SIG = SIG + CFG.RIDGE_EPS*eye(nVars);
    [F,~] = var_to_pwcgc(A,SIG,X3,CFG.ESTIMATOR,'F');
    if isbad(F,false)
        note = 'GC isbad';
        return;
    end
    [~,~,asym0] = compute_mean_asym(F,4);
    ok = true;
catch ME
    note = ME.message;
    if numel(note) > 140
        note = note(1:140);
    end
end
end
function y = tern(cond, a, b)
if cond
    y = a;
else
    y = b;
end
end
function write_cell_csv(outpath, header, rows)
fid = fopen(outpath,'w');
assert(fid~=-1,'Cannot open %s', outpath);
fprintf(fid,'%s', esc(header{1}));
for j = 2:numel(header)
    fprintf(fid,',%s', esc(header{j}));
end
fprintf(fid,'\n');
if isempty(rows)
    fclose(fid);
    return;
end
for i = 1:size(rows,1)
    for j = 1:numel(header)
        if j > 1
            fprintf(fid,',');
        end
        fprintf(fid,'%s', esc(rows{i,j}));
    end
    fprintf(fid,'\n');
end
fclose(fid);
end
function s = esc(v)
if isempty(v)
    s = '';
    return;
end
if islogical(v)
    s = sprintf('%d',v);
elseif isnumeric(v)
    if numel(v)==1
        if isnan(v)
            s = '';
        else
            s = sprintf('%.10g',v);
        end
    else
        s = mat2str(v);
    end
else
    s = char(string(v));
end
s = strrep(s,'"','""');
if ~isempty(regexp(s, '[,"\r\n]', 'once'))
    s = ['"' s '"'];
end
end
