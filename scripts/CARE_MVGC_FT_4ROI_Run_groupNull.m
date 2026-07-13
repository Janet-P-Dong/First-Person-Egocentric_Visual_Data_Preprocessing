function CARE_MVGC_FT_4ROI_Run_groupNull()
% CARE_MVGC_FT_4ROI_Run_groupNull
% ------------------------------------------------------------
% FT-only, whole-task MVGC for CARE hyperscanning.
%
% Inclusion (STRICT 4 ROI, BOTH roles):
%   Run a dyad only if ALL 4 ROIs are available for BOTH Parent & Child,
%   where ROI is available if BOTH roles have >= CFG.min_good_ch GOOD channels
%   inside that ROI based on QC keepMask.
%
% Signals:
%   <DYAD>_TaskReady.mat  containing outTask.FT with p_hbo/c_hbo and fs
% QC:
%   QC_MATH/<DYAD>_TaskReady_QC.mat containing outQC with keepMask (robust parsing)
%
% Standardization (required):
%   ROI series built as mean of good channels; then z-score each ROI series
%   (per dyad, per role, per ROI), before MVGC.
%
% MVGC pipeline (friend's flow):
%   tsdata_to_infocrit (BIC) -> tsdata_to_var -> var_to_pwcgc -> mvgc_pval -> local BH-FDR
%
% Permutations:
%   1) Pseudo-dyad group permutation (N=CFG.PERM_N):
%      permute child donors across dyads, avoiding same-dyad pairs when possible.
%      Each permutation produces one group-level null mean.
%   2) Within-dyad BLOCK permutation (N=CFG.PERM_N):
%      permute CHILD blocks within every dyad, preserving local child structure.
%      Each permutation produces one group-level null mean across dyads.
%
% Outputs (CFG.OUTDIR):
%   - GC_real_edges_FT.csv
%   - GC_real_roi_summary_FT.csv
%   - GC_real_dyad_summary_FT.csv
%   - DYAD_FT_ROI_channelCounts.csv
%   - GC_null_pseudodyad_FT.csv
%   - GC_null_blockChild_FT.csv
%   - GC_null_groupStats_FT.csv
%   - GC_null_summary_FT.csv
%
% Requires MVGC toolbox functions:
%   tsdata_to_infocrit, tsdata_to_var, var_to_pwcgc, mvgc_pval, isbad
% ------------------------------------------------------------
clc;
%% =============================
% CONFIG (EDIT HERE ONLY)
%% =============================
CFG = struct();
CFG.BASEDIR = pwd;
CFG.QC_DIR   = fullfile(CFG.BASEDIR,'QC_MATH');   % QC mats live here
CFG.DATA_DIR = CFG.BASEDIR;                       % TaskReady mats live here
CFG.OUTDIR   = fullfile(CFG.BASEDIR,'MVGC_OUT_FT4ROI_groupNull');
if ~exist(CFG.OUTDIR,'dir'); mkdir(CFG.OUTDIR); end
CFG.TASK = 'FT';
CFG.HB   = 'hbo';
% ROI map (4 ROIs) - KEEP THIS ORDER
CFG.ROI(1).name = 'LDLPFC'; CFG.ROI(1).chs = [1 8 16 9];
CFG.ROI(2).name = 'RDLPFC'; CFG.ROI(2).chs = [5 12 20 13];
CFG.ROI(3).name = 'LTPJ';   CFG.ROI(3).chs = [3 10 18 11];
CFG.ROI(4).name = 'RTPJ';   CFG.ROI(4).chs = [7 14 22 15];
CFG.min_good_ch  = 2;       % per ROI per role
CFG.require_all4 = true;    % MUST have all 4
% MVGC settings
CFG.ESTIMATOR = 'LWR';
CFG.MAX_ORDER = 30;         % BIC search cap
CFG.ALPHA_FDR = 0.05;
% Standardization
CFG.DETREND = true;
CFG.ZSCORE  = true;
% Permutations
CFG.PERM_N    = 500;        % 
CFG.PERM_SEED = 123;
CFG.PSEUDO_AVOID_SELF = true;
% ----- Block permutation params (child only) -----
CFG.BLK_LEN_SEC = 5;        % 5 s blocks default
CFG.BLK_MIN_N   = 8;        % need at least 8 blocks to permute
CFG.RIDGE_EPS = 1e-8;       % ridge for SIG stabilization
%% =============================
% Check MVGC toolbox functions exist
%% =============================
mustExist = {'tsdata_to_infocrit','tsdata_to_var','var_to_pwcgc','mvgc_pval','isbad'};
missing = {};
for i=1:numel(mustExist)
    if exist(mustExist{i},'file')~=2
        missing{end+1} = mustExist{i}; %#ok<AGROW>
    end
end
assert(isempty(missing), 'Missing MVGC functions: %s', strjoin(missing,', '));
%% =============================
% Find QC files
%% =============================
qcfiles = dir(fullfile(CFG.QC_DIR,'*_TaskReady_QC.mat'));
assert(~isempty(qcfiles),'No QC mats found in: %s', CFG.QC_DIR);
fprintf('=== CARE MVGC FT (STRICT 4ROI) ===\n');
fprintf('QC_DIR   : %s\n', CFG.QC_DIR);
fprintf('DATA_DIR : %s\n', CFG.DATA_DIR);
fprintf('OUTDIR   : %s\n', CFG.OUTDIR);
fprintf('Task     : %s\n', CFG.TASK);
fprintf('Zscore   : %d\n', CFG.ZSCORE);
fprintf('Perm N   : %d\n\n', CFG.PERM_N);
%% =============================
% Output containers (headers written at export)
%% =============================
EDGE_HDR = {'Dyad','Task','fs','nObs','morder_BIC','Src','Dst','GC','pval','sig_FDR'};
ROI_HDR  = {'Dyad','Task','fs','nObs','morder_BIC','ROIset',...
            'mean_P_to_C','mean_C_to_P','asym_PminusC',...
            'TPJ_asym','DLPFC_asym'};
DYAD_HDR = {'Dyad','Task','fs','nObs','morder_BIC','asym_PminusC','mean_P_to_C','mean_C_to_P'};
CHC_HDR  = {'Dyad','Task','ROI','nGood_P','nGood_C'};
edges   = {};
roiSum  = {};
dyadSum = {};
chCount = {};
%% =============================
% ELIG struct template (CRITICAL: avoid dissimilar struct assignment)
%% =============================
ELIG = struct('dyad',{},'fs',{},'Tobs',{},'morder',{},'X',{},'Xp_roi',{},'Xc_roi',{});
ELIG_TEMPLATE = struct('dyad',[],'fs',[],'Tobs',[],'morder',[], ...
                       'X',[],'Xp_roi',[],'Xc_roi',[]);
realAsym = [];
%% =============================
% MAIN LOOP: FT whole task
%% =============================
for f=1:numel(qcfiles)
    qcfile = qcfiles(f).name;
    dyad   = infer_dyad_from_qcname(qcfile);
    qcpath = fullfile(CFG.QC_DIR, qcfile);
    trpath = fullfile(CFG.DATA_DIR, sprintf('%s_TaskReady.mat', dyad));
    if ~exist(trpath,'file')
        fprintf('[%s] SKIP: missing TaskReady: %s\n', dyad, trpath);
        continue;
    end
    % load QC
    Sq = load(qcpath);
    outQC = pick_first_struct(Sq, {'outQC','QC','qc','out','OUT'});
    if isempty(outQC)
        fprintf('[%s] SKIP: cannot read outQC from %s\n', dyad, qcfile);
        continue;
    end
    % load TaskReady
    Ft = load(trpath);
    outTask = pick_first_struct(Ft, {'outTask','TaskReady','taskready','outTR','TR','out','data'});
    if isempty(outTask) || ~isfield(outTask, CFG.TASK)
        fprintf('[%s] SKIP: cannot read outTask.%s\n', dyad, CFG.TASK);
        continue;
    end
    % signals
    [Xp, Xc, fs, ok, msg] = get_task_mats_from_outTask(outTask, CFG.TASK, CFG.HB);
    if ~ok
        fprintf('[%s] SKIP: %s\n', dyad, msg);
        continue;
    end
    % keep masks
    [keepP, keepC] = get_keep_masks_from_outQC(outQC, CFG.TASK, size(Xp,2));
    % build ROI series (fixed ROI order)
    [Xp_roi, Xc_roi, roi_names, nGoodP, nGoodC] = build_roi_timeseries_fixed4( ...
        Xp, Xc, keepP, keepC, CFG.ROI, CFG.min_good_ch);
    if CFG.require_all4 && numel(roi_names) ~= 4
        fprintf('[%s] SKIP: not all 4 ROIs available (got %d)\n', dyad, numel(roi_names));
        continue;
    end
    % channel counts
    for r=1:4
        chCount(end+1,:) = {dyad, CFG.TASK, roi_names{r}, nGoodP(r), nGoodC(r)}; %#ok<AGROW>
    end
    % assemble X (8 x T): P then C
    X = [Xp_roi; Xc_roi];
    X = preprocess_for_mvgc(X, CFG.DETREND, CFG.ZSCORE);
    nVars = size(X,1);
    Tobs  = size(X,2);
    X3 = reshape(X, nVars, Tobs, 1);
    % model order via BIC (robust wrapper)
    morder = choose_morder_BIC_safe(X3, CFG.MAX_ORDER, CFG.ESTIMATOR, 10);
    % VAR
    [A,SIG] = tsdata_to_var(X3, morder, CFG.ESTIMATOR);
    if isbad(A)
        fprintf('[%s] SKIP: VAR failed\n', dyad);
        continue;
    end
    SIG = SIG + CFG.RIDGE_EPS*eye(nVars);
    % GC
    [F,~] = var_to_pwcgc(A, SIG, X3, CFG.ESTIMATOR, 'F');
    if isbad(F,false)
        fprintf('[%s] SKIP: GC failed\n', dyad);
        continue;
    end
    % stats p-values
    ntrials = 1;
    pval = mvgc_pval(F, morder, Tobs, ntrials, 1, 1, 'F');
    % local BH-FDR on off-diagonal
    maskOff = ~eye(nVars);
    sigvec = fdr_bh_simple(pval(maskOff), CFG.ALPHA_FDR);
    sigFDR = false(nVars);
    sigFDR(maskOff) = sigvec;
    % variable names
    var_names = cell(1,8);
    for r=1:4, var_names{r}   = ['P_' roi_names{r}]; end
    for r=1:4, var_names{4+r} = ['C_' roi_names{r}]; end
    % edges
    for iVar=1:nVars
        for jVar=1:nVars
            if iVar==jVar, continue; end
            edges(end+1,:) = {dyad, CFG.TASK, fs, Tobs, morder, ...
                var_names{jVar}, var_names{iVar}, F(iVar,jVar), pval(iVar,jVar), logical(sigFDR(iVar,jVar))}; %#ok<AGROW>
        end
    end
    % summary metrics
    [meanPC, meanCP, asym] = compute_mean_asym(F, 4);
    TPJ_asym   = compute_sub_asym(F, 4, [3 4]);
    DLPFC_asym = compute_sub_asym(F, 4, [1 2]);
    roiSetStr = strjoin(roi_names,'|');
    roiSum(end+1,:)  = {dyad, CFG.TASK, fs, Tobs, morder, roiSetStr, meanPC, meanCP, asym, TPJ_asym, DLPFC_asym}; %#ok<AGROW>
    dyadSum(end+1,:) = {dyad, CFG.TASK, fs, Tobs, morder, asym, meanPC, meanCP}; %#ok<AGROW>
    % ---- store eligible (TEMPLATE!) ----
    e = ELIG_TEMPLATE;
    e.dyad   = dyad;
    e.fs     = fs;
    e.Tobs   = Tobs;
    e.morder = morder;
    e.Xp_roi = X(1:4,:);          % standardized
    e.Xc_roi = X(5:8,:);          % standardized
    e.X      = X;                 % 8 x T standardized
    ELIG(end+1) = e; %#ok<AGROW>
    realAsym(end+1) = asym; %#ok<AGROW>
    fprintf('[%s] PASS: T=%d, mBIC=%d, asym=%.4f\n', dyad, Tobs, morder, asym);
end
fprintf('\nEligible dyads (FT strict 4ROI): %d\n', numel(ELIG));
%% =============================
% PSEUDO-DYAD group permutation (Parent sample + permuted Child sample)
% Null: parent-child pairing is exchangeable across dyads.
% Each perm_id yields one group mean, aligned with mean(realAsym).
%% =============================
rng(CFG.PERM_SEED);
pseudoHdr = {'perm_id','parent_dyad','child_dyad','morder_used','asym_null','Tobs','status','note'};
pseudoRows = {};
pseudoStats = nan(CFG.PERM_N, 1);
if numel(ELIG) >= 2
    fprintf('\nRunning pseudo-dyad group permutation, N=%d...\n', CFG.PERM_N);
    for p=1:CFG.PERM_N
        childOrd = permuted_child_order(numel(ELIG), CFG.PSEUDO_AVOID_SELF);
        asymThisPerm = nan(numel(ELIG), 1);
        for i=1:numel(ELIG)
            A = ELIG(i);           % parent donor
            B = ELIG(childOrd(i)); % child donor
            if isfinite(A.fs) && isfinite(B.fs) && abs(A.fs - B.fs) > 1e-9
                pseudoRows(end+1,:) = {p, A.dyad, B.dyad, NaN, NaN, NaN, 'SKIP', 'sampling-rate mismatch'}; %#ok<AGROW>
                continue;
            end
            Tuse = min(A.Tobs, B.Tobs);
            Xp = A.X(1:4,1:Tuse);
            Xc = B.X(5:8,1:Tuse);
            Xnull = [Xp; Xc];
            nVars = size(Xnull,1);
            X3 = reshape(Xnull, nVars, Tuse, 1);
            morder_used = choose_morder_BIC_safe(X3, CFG.MAX_ORDER, CFG.ESTIMATOR, 6);
            morder_used = max(2, morder_used);
            try
                [AA,SIG] = tsdata_to_var(X3, morder_used, CFG.ESTIMATOR);
                if isbad(AA)
                    pseudoRows(end+1,:) = {p, A.dyad, B.dyad, morder_used, NaN, Tuse, 'FAIL', 'VAR isbad'}; %#ok<AGROW>
                    continue;
                end
                SIG = SIG + CFG.RIDGE_EPS*eye(nVars);
                [F,~] = var_to_pwcgc(AA, SIG, X3, CFG.ESTIMATOR, 'F');
                if isbad(F,false)
                    pseudoRows(end+1,:) = {p, A.dyad, B.dyad, morder_used, NaN, Tuse, 'FAIL', 'GC isbad'}; %#ok<AGROW>
                    continue;
                end
                [~,~,asym_null] = compute_mean_asym(F, 4);
                asymThisPerm(i) = asym_null;
                pseudoRows(end+1,:) = {p, A.dyad, B.dyad, morder_used, asym_null, Tuse, 'OK', ''}; %#ok<AGROW>
            catch ME
                note = ME.message; if numel(note)>140, note=note(1:140); end
                pseudoRows(end+1,:) = {p, A.dyad, B.dyad, morder_used, NaN, Tuse, 'FAIL', note}; %#ok<AGROW>
            end
        end
        pseudoStats(p) = mean_omitnan(asymThisPerm);
    end
else
    fprintf('\nNot enough eligible dyads for pseudo-dyad permutation.\n');
end
%% =============================
% WITHIN-DYAD BLOCK permutation null (Child only)
% Null: directionality requires true P-C temporal alignment,
% while preserving Child local temporal structure.
% Each perm_id yields one group mean across dyads.
%% =============================
blkHdr  = {'perm_id','dyad','blk_len','morder_used','asym_null','Tobs','status','note'};
blkRows = {};
blockAsymMat = nan(numel(ELIG), CFG.PERM_N);
if ~isempty(ELIG)
    fprintf('\nRunning within-dyad BLOCK permutation (Child only), N=%d group permutations...\n', CFG.PERM_N);
    for i=1:numel(ELIG)
        D = ELIG(i);
        % standardized real series (always present in this script)
        Xreal = D.X;              % 8 x T
        T = size(Xreal,2);
        if T < 50
            blkRows(end+1,:) = {NaN, D.dyad, NaN, NaN, NaN, T, 'SKIP', 'T too short'}; %#ok<AGROW>
            continue;
        end
        % Use the same dyad-level BIC order as the real model.
        morder_used = max(2, D.morder);
        fs = D.fs;
        blk_len = max(5, round(CFG.BLK_LEN_SEC * fs));
        nBlk = floor(T / blk_len);
        if blk_len <= 2*morder_used
            note = sprintf('Block too short for model order: blk_len=%d, morder=%d', blk_len, morder_used);
            blkRows(end+1,:) = {NaN, D.dyad, blk_len, morder_used, NaN, T, 'SKIP', note}; %#ok<AGROW>
            continue;
        end
        if nBlk < CFG.BLK_MIN_N
            note = sprintf('Too few blocks: nBlk=%d (need >=%d). Consider lower BLK_LEN_SEC.', nBlk, CFG.BLK_MIN_N);
            blkRows(end+1,:) = {NaN, D.dyad, blk_len, morder_used, NaN, T, 'SKIP', note}; %#ok<AGROW>
            continue;
        end
        % trim to full blocks only
        Tuse = nBlk * blk_len;
        Xp = Xreal(1:4,1:Tuse);
        Xc = Xreal(5:8,1:Tuse);
        % reshape child into blocks: [4 x blk_len x nBlk]
        Xc_blk = reshape(Xc, 4, blk_len, nBlk);
        for p=1:CFG.PERM_N
            ord = randperm(nBlk);
            while isequal(ord, 1:nBlk)
                ord = randperm(nBlk);
            end
            Xc_perm = Xc_blk(:,:,ord);
            Xc_null = reshape(Xc_perm, 4, Tuse);
            Xnull = [Xp; Xc_null];
            nVars = size(Xnull,1);
            X3 = reshape(Xnull, nVars, Tuse, 1);
            try
                [AA,SIG] = tsdata_to_var(X3, morder_used, CFG.ESTIMATOR);
                if isbad(AA)
                    blkRows(end+1,:) = {p, D.dyad, blk_len, morder_used, NaN, Tuse, 'FAIL', 'VAR isbad'}; %#ok<AGROW>
                    continue;
                end
                SIG = SIG + CFG.RIDGE_EPS*eye(nVars);
                [F,~] = var_to_pwcgc(AA, SIG, X3, CFG.ESTIMATOR, 'F');
                if isbad(F,false)
                    blkRows(end+1,:) = {p, D.dyad, blk_len, morder_used, NaN, Tuse, 'FAIL', 'GC isbad'}; %#ok<AGROW>
                    continue;
                end
                [~,~,asym_null] = compute_mean_asym(F, 4);
                blockAsymMat(i,p) = asym_null;
                blkRows(end+1,:) = {p, D.dyad, blk_len, morder_used, asym_null, Tuse, 'OK', ''}; %#ok<AGROW>
            catch ME
                note = ME.message; if numel(note)>140, note=note(1:140); end
                blkRows(end+1,:) = {p, D.dyad, blk_len, morder_used, NaN, Tuse, 'FAIL', note}; %#ok<AGROW>
            end
        end
    end
end
blockStats = col_mean_omitnan(blockAsymMat)';
%% =============================
% Export CSVs
%% =============================
write_cell_csv(fullfile(CFG.OUTDIR,'GC_real_edges_FT.csv'), EDGE_HDR, edges);
write_cell_csv(fullfile(CFG.OUTDIR,'GC_real_roi_summary_FT.csv'), ROI_HDR, roiSum);
write_cell_csv(fullfile(CFG.OUTDIR,'GC_real_dyad_summary_FT.csv'), DYAD_HDR, dyadSum);
write_cell_csv(fullfile(CFG.OUTDIR,'DYAD_FT_ROI_channelCounts.csv'), CHC_HDR, chCount);
write_cell_csv(fullfile(CFG.OUTDIR,'GC_null_pseudodyad_FT.csv'), pseudoHdr, pseudoRows);
write_cell_csv(fullfile(CFG.OUTDIR,'GC_null_blockChild_FT.csv'), blkHdr, blkRows);
% group-level null statistics and empirical tails
real_stat = mean_omitnan(realAsym);
groupHdr = {'perm_id','pseudo_group_mean','block_group_mean'};
groupRows = cell(CFG.PERM_N, numel(groupHdr));
for p=1:CFG.PERM_N
    groupRows(p,:) = {p, pseudoStats(p), blockStats(p)};
end
write_cell_csv(fullfile(CFG.OUTDIR,'GC_null_groupStats_FT.csv'), groupHdr, groupRows);
summaryHdr = {'N_real','real_mean','real_sd', ...
              'N_pseudo_group_OK','pseudo_group_mean','pseudo_group_sd', ...
              'p_pseudo_upper_realGreater','p_pseudo_lower_realLower','p_pseudo_twoSided', ...
              'N_block_group_OK','block_group_mean','block_group_sd', ...
              'p_block_upper_realGreater','p_block_lower_realLower','p_block_twoSided'};
summaryRow = {numel(realAsym), real_stat, std_omitnan(realAsym)};
% pseudo
pseudoOK = pseudoStats(isfinite(pseudoStats));
if ~isempty(pseudoOK)
    [p_upper, p_lower, p_two] = empirical_tails(real_stat, pseudoOK);
    summaryRow = [summaryRow, {numel(pseudoOK), mean_omitnan(pseudoOK), std_omitnan(pseudoOK), p_upper, p_lower, p_two}];
else
    summaryRow = [summaryRow, {0, NaN, NaN, NaN, NaN, NaN}];
end
% block
blockOK = blockStats(isfinite(blockStats));
if ~isempty(blockOK)
    [p_upper, p_lower, p_two] = empirical_tails(real_stat, blockOK);
    summaryRow = [summaryRow, {numel(blockOK), mean_omitnan(blockOK), std_omitnan(blockOK), p_upper, p_lower, p_two}];
else
    summaryRow = [summaryRow, {0, NaN, NaN, NaN, NaN, NaN}];
end
write_cell_csv(fullfile(CFG.OUTDIR,'GC_null_summary_FT.csv'), summaryHdr, summaryRow);
fprintf('\n✅ DONE. Outputs saved to:\n%s\n', CFG.OUTDIR);
end
%% ============================================================
% Helpers
%% ============================================================
function dyad = infer_dyad_from_qcname(qcfile)
tok = regexp(qcfile, '^([0-9]{2}[A-Za-z])_TaskReady_QC\.mat$', 'tokens', 'once');
if ~isempty(tok)
    dyad = upper(tok{1});
else
    dyad = upper(qcfile(1:min(3,numel(qcfile))));
end
end
function ord = permuted_child_order(n, avoidSelf)
ord = randperm(n);
if avoidSelf && n > 1
    maxTry = 1000;
    k = 0;
    while any(ord == 1:n) && k < maxTry
        ord = randperm(n);
        k = k + 1;
    end
    % For small or unlucky samples, a simple rotation guarantees no self-pair.
    if any(ord == 1:n)
        ord = [2:n 1];
    end
end
end
function [p_upper, p_lower, p_two] = empirical_tails(real_stat, null_stats)
null_stats = null_stats(isfinite(null_stats));
if isempty(null_stats) || ~isfinite(real_stat)
    p_upper = NaN;
    p_lower = NaN;
    p_two = NaN;
    return;
end
% Add-one correction avoids exact-zero p-values from finite permutations.
n = numel(null_stats);
p_upper = (sum(null_stats >= real_stat) + 1) / (n + 1);
p_lower = (sum(null_stats <= real_stat) + 1) / (n + 1);
p_two = min(1, 2 * min(p_upper, p_lower));
end
function m = mean_omitnan(x)
x = x(isfinite(x));
if isempty(x)
    m = NaN;
else
    m = mean(x);
end
end
function s = std_omitnan(x)
x = x(isfinite(x));
if numel(x) < 2
    s = NaN;
else
    s = std(x);
end
end
function m = col_mean_omitnan(X)
m = nan(1, size(X,2));
for j=1:size(X,2)
    m(j) = mean_omitnan(X(:,j));
end
end
function S = pick_first_struct(L, candidates)
S = [];
for i=1:numel(candidates)
    c = candidates{i};
    if isfield(L,c) && isstruct(L.(c))
        S = L.(c); return;
    end
end
fn = fieldnames(L);
for i=1:numel(fn)
    v = L.(fn{i});
    if isstruct(v)
        S = v; return;
    end
end
end
function [Xp, Xc, fs, ok, msg] = get_task_mats_from_outTask(outTask, task, hb)
ok = false; msg = '';
Xp=[]; Xc=[]; fs=NaN;
if ~isfield(outTask, task)
    msg = sprintf('Missing outTask.%s', task); return;
end
T = outTask.(task);
pfield = ['p_' hb];
cfield = ['c_' hb];
if ~isfield(T,pfield) || ~isfield(T,cfield)
    msg = sprintf('Missing fields: %s/%s', pfield, cfield); return;
end
Xp = T.(pfield);
Xc = T.(cfield);
if isempty(Xp) || isempty(Xc)
    msg = 'Empty matrices'; return;
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
            km = TT.keepMaskParent; if numel(km)==nCh, keepP = logical(km(:))'; end
        end
        if isfield(TT,'keepMaskChild')
            km = TT.keepMaskChild; if numel(km)==nCh, keepC = logical(km(:))'; end
        end
    end
    if isfield(outQC,'keepMaskParent')
        km = outQC.keepMaskParent; if numel(km)==nCh, keepP = logical(km(:))'; end
    end
    if isfield(outQC,'keepMaskChild')
        km = outQC.keepMaskChild; if numel(km)==nCh, keepC = logical(km(:))'; end
    end
catch
end
end
function [Xp_roi, Xc_roi, roi_names, nGoodP, nGoodC] = build_roi_timeseries_fixed4(Xp, Xc, keepP, keepC, ROI, min_good_ch)
T = size(Xp,1);
Xp_roi = nan(numel(ROI), T);
Xc_roi = nan(numel(ROI), T);
roi_names = {};
nGoodP = [];
nGoodC = [];
k = 0;
for r=1:numel(ROI)
    chs = ROI(r).chs;
    chs = chs(chs>=1 & chs<=size(Xp,2));
    goodP = chs(keepP(chs));
    goodC = chs(keepC(chs));
    if numel(goodP) >= min_good_ch && numel(goodC) >= min_good_ch
        Pseries = mean(Xp(:,goodP),2,'omitnan');
        Cseries = mean(Xc(:,goodC),2,'omitnan');
        if any(isnan(Pseries)) || any(isnan(Cseries))
            continue;
        end
        k = k + 1;
        Xp_roi(k,:) = Pseries(:)';
        Xc_roi(k,:) = Cseries(:)';
        roi_names{k} = upper(ROI(r).name); %#ok<AGROW>
        nGoodP(k) = numel(goodP); %#ok<AGROW>
        nGoodC(k) = numel(goodC); %#ok<AGROW>
    end
end
Xp_roi = Xp_roi(1:k,:);
Xc_roi = Xc_roi(1:k,:);
end
function Xout = preprocess_for_mvgc(X, doDetrend, doZ)
Xout = X;
for v=1:size(X,1)
    x = Xout(v,:)';
    x = x - mean(x,'omitnan');
    if doDetrend
        x = detrend(x,'linear');
    end
    if doZ
        sd = std(x,0,'omitnan');
        if sd>0
            x = (x - mean(x,'omitnan')) ./ sd;
        else
            x = x - mean(x,'omitnan');
        end
    end
    Xout(v,:) = x(:)';
end
if any(isnan(Xout(:)))
    error('NaNs after preprocessing. Check ROI building / keep masks.');
end
end
function sig = fdr_bh_simple(pvals, alpha)
p = pvals(:);
[ps, idx] = sort(p,'ascend');
m = numel(ps);
th = (1:m)'/m * alpha;
k = find(ps <= th, 1, 'last');
sig = false(size(p));
if ~isempty(k)
    sig(idx(1:k)) = true;
end
sig = reshape(sig, size(pvals));
end
function [meanPC, meanCP, asym] = compute_mean_asym(F, nROIpairs)
Pidx = 1:nROIpairs;
Cidx = (nROIpairs+1):(2*nROIpairs);
PC = [];
CP = [];
for d=Cidx
    for s=Pidx
        PC(end+1)=F(d,s); %#ok<AGROW>
    end
end
for d=Pidx
    for s=Cidx
        CP(end+1)=F(d,s); %#ok<AGROW>
    end
end
meanPC = mean(PC);
meanCP = mean(CP);
asym   = meanPC - meanCP;
end
function sub_asym = compute_sub_asym(F, nROIpairs, subIdx)
if isempty(subIdx), sub_asym = NaN; return; end
Pidx = subIdx;
Cidx = nROIpairs + subIdx;
PC=[]; CP=[];
for d=Cidx
    for s=Pidx
        PC(end+1)=F(d,s); %#ok<AGROW>
    end
end
for d=Pidx
    for s=Cidx
        CP(end+1)=F(d,s); %#ok<AGROW>
    end
end
sub_asym = mean(PC) - mean(CP);
end
function morder = choose_morder_BIC_safe(X3, maxOrder, estimator, fallbackOrder)
% Robust BIC chooser: if tsdata_to_infocrit errors (SPD issues), return fallbackOrder.
morder = fallbackOrder;
try
    [~,~,~,moBIC] = tsdata_to_infocrit(X3, maxOrder, estimator);
    if ~isempty(moBIC) && isnumeric(moBIC) && isfinite(moBIC) && moBIC>=1
        morder = moBIC;
    end
catch
    % keep fallback
end
end
function write_cell_csv(outpath, header, rows)
fid = fopen(outpath,'w');
assert(fid~=-1, 'Cannot open %s', outpath);
fprintf(fid, '%s', csv_escape(header{1}));
for j=2:numel(header)
    fprintf(fid, ',%s', csv_escape(header{j}));
end
fprintf(fid, '\n');
if isempty(rows)
    fclose(fid);
    return;
end
for i=1:size(rows,1)
    for j=1:numel(header)
        if j>1, fprintf(fid, ','); end
        fprintf(fid, '%s', csv_escape(rows{i,j}));
    end
    fprintf(fid, '\n');
end
fclose(fid);
end
function s = csv_escape(v)
if isempty(v)
    s = '';
    return;
end
if islogical(v)
    s = sprintf('%d', v);
elseif isnumeric(v)
    if numel(v)==1
        if isnan(v), s = ''; else, s = sprintf('%.10g', v); end
    else
        s = mat2str(v);
    end
elseif isstring(v) || ischar(v)
    s = char(v);
else
    try
        s = char(string(v));
    catch
        s = '<obj>';
    end
end
s = strrep(s, '"', '""');
needQuote = false;
if ~isempty(strfind(s, ',')),  needQuote = true; end %#ok<STREMP>
if ~isempty(strfind(s, '"')),  needQuote = true; end %#ok<STREMP>
if ~isempty(strfind(s, sprintf('\n'))), needQuote = true; end %#ok<STREMP>
if ~isempty(strfind(s, sprintf('\r'))), needQuote = true; end %#ok<STREMP>
if needQuote
    s = ['"', s, '"'];
end
end
